"""
Integration test: Verify Copy effects work end-to-end through GameService
"""
import pytest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from api.game_service import GameService
from game_engine.rules.effects import EffectRegistry


def test_copy_effects_persist_through_reload():
    """Test that Copy card effects persist when game is reloaded from storage."""
    # Create game service with in-memory mode (no database)
    cards_csv_path = Path(__file__).parent.parent / "data" / "cards.csv"
    service = GameService(str(cards_csv_path), use_database=False)

    # Create a new game with specific decks
    game_id, engine = service.create_game(
        player1_id="test_player1",
        player1_name="Test Player 1",
        player1_deck=["Demideca", "Copy", "Ka", "Knight", "Sun", "Wake"],
        player2_id="test_player2",
        player2_name="Test Player 2",
        player2_deck=["Demideca", "Copy", "Ka", "Knight", "Sun", "Wake"],
    )

    # Get the game
    engine = service.get_game(game_id)
    player = engine.game_state.players["test_player1"]

    # Find Demideca and Copy in hand
    demideca = next((c for c in player.hand if c.name == "Demideca"), None)
    copy_card = next((c for c in player.hand if c.name == "Copy"), None)
    ka = next((c for c in player.hand if c.name == "Ka"), None)

    # Cards should be in hand since we specified the deck
    assert demideca is not None, "Demideca should be in hand"
    assert copy_card is not None, "Copy should be in hand"
    assert ka is not None, "Ka should be in hand"

    # Play Demideca
    engine.play_toy("test_player1", demideca.id, "test_player1")
    service.update_game(game_id, engine)

    # Reload game and verify Demideca's stats
    engine = service.get_game(game_id)
    player = engine.game_state.players["test_player1"]
    demideca_in_play = next((c for c in player.in_play if c.name == "Demideca"), None)
    
    assert demideca_in_play is not None
    demideca_str = engine.get_card_stat(demideca_in_play, 'strength')
    assert demideca_str == 3, f"Demideca should have 3 STR (2 base + 1 from self), got {demideca_str}"

    # Play Copy targeting Demideca
    copy_in_hand = next((c for c in player.hand if c.name == "Copy"), None)
    engine.play_action("test_player1", copy_in_hand.id, {"target_id": demideca_in_play.id})
    service.update_game(game_id, engine)

    # Reload game AFTER Copy played
    engine = service.get_game(game_id)
    player = engine.game_state.players["test_player1"]

    # Find cards in play
    demideca_in_play = next((c for c in player.in_play if c.name == "Demideca" and "Copy" not in c.name), None)
    copy_in_play = next((c for c in player.in_play if "Copy of Demideca" in c.name), None)

    assert copy_in_play is not None, "Copy of Demideca should be in play"
    
    # Verify effects are restored
    effects = EffectRegistry.get_effects(copy_in_play)
    assert len(effects) > 0, "Copy of Demideca should have effects after reload"

    # Check stats
    demideca_str = engine.get_card_stat(demideca_in_play, 'strength')
    copy_str = engine.get_card_stat(copy_in_play, 'strength')
    
    # Both should have 4 STR: 2 base + 1 from original Demideca + 1 from Copy's Demideca effect
    assert demideca_str == 4, f"Demideca should have 4 STR, got {demideca_str}"
    assert copy_str == 4, f"Copy of Demideca should have 4 STR, got {copy_str}"

    # Play Ka to test all effects together
    ka_in_hand = next((c for c in player.hand if c.name == "Ka"), None)
    engine.play_toy("test_player1", ka_in_hand.id, "test_player1")
    service.update_game(game_id, engine)
    
    # Reload one more time
    engine = service.get_game(game_id)
    player = engine.game_state.players["test_player1"]
    
    ka_in_play = next((c for c in player.in_play if c.name == "Ka"), None)
    ka_str = engine.get_card_stat(ka_in_play, 'strength')
    
    # Ka should have: 9 base + 2 Ka effect + 1 Demideca + 1 Copy's Demideca = 13
    assert ka_str == 13, f"Ka should have 13 STR, got {ka_str}"
