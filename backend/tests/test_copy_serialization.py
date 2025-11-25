"""
Test that Copy card effects survive serialization/deserialization.
"""
import pytest
from pathlib import Path
import sys

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from game_engine.models.card import Card, CardType, Zone
from game_engine.models.player import Player
from game_engine.models.game_state import GameState, Phase
from game_engine.game_engine import GameEngine
from game_engine.data.card_loader import CardLoader
from api.serialization import serialize_game_state, deserialize_game_state
from game_engine.rules.effects import EffectRegistry


def test_copy_effects_survive_serialization():
    """Test that Copy card's _copied_effects survive serialize/deserialize cycle."""
    # Load cards from CSV
    cards_csv_path = Path(__file__).parent.parent / "data" / "cards.csv"
    loader = CardLoader(str(cards_csv_path))
    all_cards = loader.load_cards_dict()
    
    # Create a game with Ka and Copy
    player1_deck = [
        Card(
            name=all_cards['Ka'].name,
            card_type=all_cards['Ka'].card_type,
            cost=all_cards['Ka'].cost,
            effect_text=all_cards['Ka'].effect_text,
            effect_definitions=all_cards['Ka'].effect_definitions,
            speed=all_cards['Ka'].speed,
            strength=all_cards['Ka'].strength,
            stamina=all_cards['Ka'].stamina,
            primary_color=all_cards['Ka'].primary_color,
            accent_color=all_cards['Ka'].accent_color,
        )
        for _ in range(5)
    ]
    player1_deck.append(
        Card(
            name=all_cards['Copy'].name,
            card_type=all_cards['Copy'].card_type,
            cost=all_cards['Copy'].cost,
            effect_text=all_cards['Copy'].effect_text,
            effect_definitions=all_cards['Copy'].effect_definitions,
            primary_color=all_cards['Copy'].primary_color,
            accent_color=all_cards['Copy'].accent_color,
        )
    )
    
    player2_deck = [
        Card(
            name=all_cards['Demideca'].name,
            card_type=all_cards['Demideca'].card_type,
            cost=all_cards['Demideca'].cost,
            effect_text=all_cards['Demideca'].effect_text,
            effect_definitions=all_cards['Demideca'].effect_definitions,
            speed=all_cards['Demideca'].speed,
            strength=all_cards['Demideca'].strength,
            stamina=all_cards['Demideca'].stamina,
            primary_color=all_cards['Demideca'].primary_color,
            accent_color=all_cards['Demideca'].accent_color,
        )
        for _ in range(6)
    ]
    
    engine = GameEngine(
        player1_id="player1",
        player1_name="Player 1",
        player1_deck=player1_deck,
        player2_id="player2",
        player2_name="Player 2",
        player2_deck=player2_deck,
        first_player_id="player1",
    )
    
    # Start the game
    engine.start_game()
    
    # Play Ka (should buff itself to 11)
    player = engine.game_state.players["player1"]
    ka = next((c for c in player.hand if c.name == "Ka"), None)
    assert ka is not None
    
    # Force Ka into play
    ka.zone = Zone.IN_PLAY
    ka.controller = "player1"
    player.hand.remove(ka)
    player.in_play.append(ka)
    
    # Play Copy targeting Ka
    copy_card = next((c for c in player.hand if c.name == "Copy"), None)
    assert copy_card is not None
    
    # Simulate CopyEffect transformation
    copy_card.name = "Copy of Ka"
    copy_card.effect_text = ka.effect_text
    copy_card.effect_definitions = ka.effect_definitions
    copy_card.speed = ka.speed
    copy_card.strength = ka.strength
    copy_card.stamina = ka.stamina
    copy_card._is_transformed = True
    
    # Create _copied_effects
    from game_engine.rules.effects.effect_factory import EffectFactory
    copy_card._copied_effects = EffectFactory.parse_effects(
        copy_card.effect_definitions,
        copy_card
    )
    
    # Move Copy to in_play
    copy_card.zone = Zone.IN_PLAY
    copy_card.controller = "player1"
    player.hand.remove(copy_card)
    player.in_play.append(copy_card)
    
    # Verify effects before serialization
    assert hasattr(copy_card, '_copied_effects'), "Copy should have _copied_effects before serialization"
    assert len(copy_card._copied_effects) > 0, "Copy should have at least one copied effect"
    
    effects_before = EffectRegistry.get_effects(copy_card)
    assert len(effects_before) > 0, "EffectRegistry should return effects before serialization"
    
    # Check Ka's stats (should be 13: 9 base + 2 from Ka + 2 from Copy of Ka)
    ka_strength_before = engine.get_card_stat(ka, 'strength')
    print(f"Ka strength before serialization: {ka_strength_before}")
    assert ka_strength_before == 13, f"Expected 13, got {ka_strength_before}"
    
    # Serialize the game state
    serialized = serialize_game_state(engine.game_state)
    
    # Check that serialization includes transformation flag
    serialized_copy = None
    for player_data in serialized['players'].values():
        for card_data in player_data['in_play']:
            if card_data['name'] == 'Copy of Ka':
                serialized_copy = card_data
                break
    
    assert serialized_copy is not None, "Copy of Ka should be in serialized data"
    assert serialized_copy.get('modifications', {}).get('_is_transformed') is True, \
        "Serialized Copy should have _is_transformed flag in modifications"
    assert 'effect_definitions' in serialized_copy, "Serialized Copy should have effect_definitions"
    
    # Deserialize the game state
    deserialized_state = deserialize_game_state(serialized)
    
    # Find the Copy card in deserialized state
    deserialized_player = deserialized_state.players["player1"]
    deserialized_copy = next((c for c in deserialized_player.in_play if c.name == "Copy of Ka"), None)
    assert deserialized_copy is not None, "Copy of Ka should exist after deserialization"
    
    # Verify _copied_effects restored
    assert hasattr(deserialized_copy, '_copied_effects'), \
        "Deserialized Copy should have _copied_effects attribute"
    assert len(deserialized_copy._copied_effects) > 0, \
        "Deserialized Copy should have at least one copied effect"
    
    # Verify EffectRegistry returns effects
    effects_after = EffectRegistry.get_effects(deserialized_copy)
    assert len(effects_after) > 0, "EffectRegistry should return effects after deserialization"
    
    # Create a new engine with deserialized state to test stat calculation
    engine2 = GameEngine(
        player1_id="player1",
        player1_name="Player 1",
        player1_deck=[],
        player2_id="player2",
        player2_name="Player 2",
        player2_deck=[],
        first_player_id="player1",
    )
    engine2.game_state = deserialized_state
    
    # Find Ka in deserialized state
    deserialized_ka = next((c for c in deserialized_player.in_play if c.name == "Ka"), None)
    assert deserialized_ka is not None
    
    # Check Ka's stats after deserialization (should still be 13)
    ka_strength_after = engine2.get_card_stat(deserialized_ka, 'strength')
    print(f"Ka strength after serialization: {ka_strength_after}")
    assert ka_strength_after == 13, \
        f"Ka strength should be 13 after deserialization, got {ka_strength_after}"


if __name__ == '__main__':
    test_copy_effects_survive_serialization()
    print("\n✅ All tests passed!")
