"""
Tests for the GGLTCG game engine.

Tests game initialization, turn management, card playing, and tussles.
"""

import sys
from pathlib import Path

# Add the src directory to the path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from game_engine.game_engine import GameEngine
from game_engine.models.game_state import GameState, Phase
from game_engine.models.player import Player
from game_engine.models.card import Card, CardType, Zone
from game_engine.data.card_loader import CardLoader


def create_test_game() -> GameState:
    """Create a simple test game with two players."""
    # Load cards
    csv_path = Path(__file__).parent.parent / "data" / "cards.csv"
    loader = CardLoader(str(csv_path))
    all_cards = loader.load_cards()
    
    # Create players with simple decks
    player1_cards = [
        next(c for c in all_cards if c.name == "Ka"),
        next(c for c in all_cards if c.name == "Knight"),
        next(c for c in all_cards if c.name == "Beary"),
    ]
    
    player2_cards = [
        next(c for c in all_cards if c.name == "Wizard"),
        next(c for c in all_cards if c.name == "Demideca"),
        next(c for c in all_cards if c.name == "Archer"),
    ]
    
    # Set ownership
    for card in player1_cards:
        card.owner = "player1"
        card.controller = "player1"
    
    for card in player2_cards:
        card.owner = "player2"
        card.controller = "player2"
    
    player1 = Player(
        player_id="player1",
        name="Alice",
        hand=player1_cards.copy(),
    )
    
    player2 = Player(
        player_id="player2",
        name="Bob",
        hand=player2_cards.copy(),
    )
    
    game_state = GameState(
        game_id="test-game",
        players={"player1": player1, "player2": player2},
        active_player_id="player1",
        first_player_id="player1",
        turn_number=1,
        phase=Phase.START,
    )
    
    return game_state


def test_turn_management():
    """Test turn start and end mechanics."""
    print("Testing turn management...")
    
    game_state = create_test_game()
    engine = GameEngine(game_state)
    
    # Start turn 1
    engine.start_turn()
    
    player1 = game_state.players["player1"]
    
    # First player should get 2 CC on turn 1
    assert player1.cc == 2, f"Expected 2 CC on turn 1, got {player1.cc}"
    print("✓ First player gained 2 CC on turn 1")
    
    # Should be in main phase
    assert game_state.phase == Phase.MAIN, f"Expected Main phase, got {game_state.phase}"
    print("✓ Moved to Main phase")
    
    # End turn
    engine.end_turn()
    
    # Should switch to player 2
    assert game_state.active_player_id == "player2", "Turn didn't switch to player 2"
    print("✓ Turn switched to player 2")
    
    # Turn number should increment
    assert game_state.turn_number == 2, f"Expected turn 2, got {game_state.turn_number}"
    print("✓ Turn number incremented")
    
    player2 = game_state.players["player2"]
    
    # Player 2 should get 4 CC (not first turn)
    assert player2.cc == 4, f"Expected 4 CC on turn 2, got {player2.cc}"
    print("✓ Second player gained 4 CC")
    
    return True


def test_play_card():
    """Test playing cards."""
    print("\nTesting card playing...")
    
    game_state = create_test_game()
    engine = GameEngine(game_state)
    engine.start_turn()
    
    player1 = game_state.players["player1"]
    
    # Play Ka (cost 2 CC)
    ka = next(c for c in player1.hand if c.name == "Ka")
    
    success = engine.play_card(player1, ka)
    assert success, "Failed to play Ka"
    print("✓ Successfully played Ka")
    
    # Ka should be in play
    assert ka in player1.in_play, "Ka not in play area"
    assert ka not in player1.hand, "Ka still in hand"
    print("✓ Ka moved to play area")
    
    # Player should have 0 CC left (started with 2, spent 2)
    assert player1.cc == 0, f"Expected 0 CC, got {player1.cc}"
    print("✓ CC cost deducted correctly")
    
    return True


def test_continuous_effects():
    """Test continuous effects like Ka's +2 Strength."""
    print("\nTesting continuous effects...")
    
    game_state = create_test_game()
    engine = GameEngine(game_state)
    engine.start_turn()
    
    player1 = game_state.players["player1"]
    
    # Play Ka
    ka = next(c for c in player1.hand if c.name == "Ka")
    engine.play_card(player1, ka)
    
    # Ka's base strength is 9
    base_strength = ka.strength
    print(f"  Ka base strength: {base_strength}")
    
    # With Ka's effect, it should get +2 (its own effect applies to itself)
    modified_strength = engine.get_card_stat(ka, "strength")
    assert modified_strength == base_strength + 2, \
        f"Expected {base_strength + 2}, got {modified_strength}"
    print(f"✓ Ka has +2 Strength from its own effect ({modified_strength})")
    
    # Play Knight
    knight = next(c for c in player1.hand if c.name == "Knight")
    player1.gain_cc(10)  # Give enough CC
    engine.play_card(player1, knight)
    
    # Knight should also get +2 from Ka
    knight_base = knight.strength
    knight_modified = engine.get_card_stat(knight, "strength")
    assert knight_modified == knight_base + 2, \
        f"Expected {knight_base + 2}, got {knight_modified}"
    print(f"✓ Knight has +2 Strength from Ka ({knight_modified})")
    
    return True


def test_tussle_basic():
    """Test basic tussle mechanics."""
    print("\nTesting basic tussle...")
    
    game_state = create_test_game()
    engine = GameEngine(game_state)
    
    # Set up: Both players have cards in play
    player1 = game_state.players["player1"]
    player2 = game_state.players["player2"]
    
    # Give players CC and put cards in play
    player1.gain_cc(10)
    player2.gain_cc(10)
    
    ka = next(c for c in player1.hand if c.name == "Ka")
    ka.zone = Zone.IN_PLAY
    player1.hand.remove(ka)
    player1.in_play.append(ka)
    
    wizard = next(c for c in player2.hand if c.name == "Wizard")
    wizard.zone = Zone.IN_PLAY
    player2.hand.remove(wizard)
    player2.in_play.append(wizard)
    
    game_state.phase = Phase.MAIN
    game_state.active_player_id = "player1"
    
    # Calculate initial stats
    ka_str = engine.get_card_stat(ka, "strength")
    wizard_str = engine.get_card_stat(wizard, "strength")
    
    print(f"  Ka: {ka_str} STR, {ka.current_stamina} STA")
    print(f"  Wizard: {wizard_str} STR, {wizard.current_stamina} STA")
    
    # Ka tussles Wizard
    success = engine.initiate_tussle(ka, wizard, player1)
    assert success, "Tussle failed to initiate"
    print("✓ Tussle initiated successfully")
    
    # Check that damage was applied
    # Ka has higher speed (5) than Wizard (1), so Ka strikes first
    # Ka deals 11 damage (9 base + 2 from own effect)
    # Wizard has 3 stamina, so should be sleeped
    assert wizard in player2.sleep_zone, "Wizard should be sleeped"
    assert wizard not in player2.in_play, "Wizard should not be in play"
    print("✓ Wizard was sleeped (took fatal damage)")
    
    return True


def test_cost_modification():
    """Test cost modification effects."""
    print("\nTesting cost modification (Wizard)...")
    
    game_state = create_test_game()
    engine = GameEngine(game_state)
    
    player1 = game_state.players["player1"]
    player2 = game_state.players["player2"]
    player1.gain_cc(10)
    
    # Put Wizard (player2's card) in player1's control (via control change)
    wizard = next(c for c in player2.hand if c.name == "Wizard")
    wizard.zone = Zone.IN_PLAY
    wizard.controller = "player1"
    player2.hand.remove(wizard)
    player1.in_play.append(wizard)
    
    # Put Ka in play for tussle attacker
    ka = next(c for c in player1.hand if c.name == "Ka")
    ka.zone = Zone.IN_PLAY
    player1.hand.remove(ka)
    player1.in_play.append(ka)
    
    game_state.phase = Phase.MAIN
    
    # Tussle cost should be 1 (Wizard's effect)
    cost = engine.calculate_tussle_cost(ka, player1)
    assert cost == 1, f"Expected tussle cost 1 with Wizard, got {cost}"
    print("✓ Wizard reduces tussle cost to 1 CC")
    
    return True


def test_victory_condition():
    """Test victory condition check."""
    print("\nTesting victory condition...")
    
    game_state = create_test_game()
    engine = GameEngine(game_state)
    
    player1 = game_state.players["player1"]
    player2 = game_state.players["player2"]
    
    # Move all player2's cards to sleep zone
    for card in player2.hand[:]:
        player2.hand.remove(card)
        card.zone = Zone.SLEEP
        player2.sleep_zone.append(card)
    
    # Check victory
    winner = game_state.check_victory()
    assert winner == "player1", f"Expected player1 to win, got {winner}"
    print("✓ Player 1 wins when all opponent cards are sleeped")
    
    return True


def main():
    """Run all game engine tests."""
    print("=" * 60)
    print("GGLTCG Game Engine Tests")
    print("=" * 60)
    
    tests = [
        test_turn_management,
        test_play_card,
        test_continuous_effects,
        test_tussle_basic,
        test_cost_modification,
        test_victory_condition,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ Test {test.__name__} failed with exception: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed == 0:
        print("\n✅ All game engine tests passed!")
    else:
        print(f"\n❌ {failed} test(s) failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
