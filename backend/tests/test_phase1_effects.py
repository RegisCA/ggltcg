"""
Tests for Phase 1 data-driven action effects.

Verifies that Rush, Wake, Sun, and Clean work correctly with the new CSV-driven system.
"""

import sys
from pathlib import Path

# Add the src directory to the path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from game_engine.models.game_state import GameState, Phase
from game_engine.models.player import Player
from game_engine.models.card import Zone
from game_engine.data.card_loader import CardLoader
from game_engine.rules.effects.effect_registry import EffectRegistry


def test_rush_effect_parsing():
    """Test that Rush effect is parsed correctly from CSV."""
    print("Testing Rush effect parsing...")
    
    csv_path = Path(__file__).parent.parent / "data" / "cards.csv"
    loader = CardLoader(str(csv_path))
    all_cards = loader.load_cards()
    
    rush = next(c for c in all_cards if c.name == "Rush")
    print(f"  Rush effect_definitions: '{rush.effect_definitions}'")
    
    if rush.effect_definitions != "gain_cc:2:not_first_turn":
        print(f"✗ Rush should have effect_definitions='gain_cc:2:not_first_turn'")
        return False
    
    # Get the effect
    effects = EffectRegistry.get_effects(rush)
    print(f"  Rush has {len(effects)} effect(s): {[e.__class__.__name__ for e in effects]}")
    
    if len(effects) != 1:
        print(f"✗ Rush should have 1 effect")
        return False
    
    if effects[0].__class__.__name__ != "GainCCEffect":
        print(f"✗ Rush effect should be GainCCEffect")
        return False
    
    # Check parameters
    effect = effects[0]
    if effect.amount != 2:
        print(f"✗ Rush should gain 2 CC, got {effect.amount}")
        return False
    
    if not effect.not_first_turn:
        print(f"✗ Rush should have not_first_turn restriction")
        return False
    
    print(f"✓ Rush effect parsed correctly")
    return True


def test_wake_effect_parsing():
    """Test that Wake effect is parsed correctly from CSV."""
    print("\nTesting Wake effect parsing...")
    
    csv_path = Path(__file__).parent.parent / "data" / "cards.csv"
    loader = CardLoader(str(csv_path))
    all_cards = loader.load_cards()
    
    wake = next(c for c in all_cards if c.name == "Wake")
    print(f"  Wake effect_definitions: '{wake.effect_definitions}'")
    
    if wake.effect_definitions != "unsleep:1":
        print(f"✗ Wake should have effect_definitions='unsleep:1'")
        return False
    
    effects = EffectRegistry.get_effects(wake)
    print(f"  Wake has {len(effects)} effect(s): {[e.__class__.__name__ for e in effects]}")
    
    if len(effects) != 1 or effects[0].__class__.__name__ != "UnsleepEffect":
        print(f"✗ Wake should have 1 UnsleepEffect")
        return False
    
    if effects[0].count != 1:
        print(f"✗ Wake should unsleep 1 card")
        return False
    
    print(f"✓ Wake effect parsed correctly")
    return True


def test_sun_effect_parsing():
    """Test that Sun effect is parsed correctly from CSV."""
    print("\nTesting Sun effect parsing...")
    
    csv_path = Path(__file__).parent.parent / "data" / "cards.csv"
    loader = CardLoader(str(csv_path))
    all_cards = loader.load_cards()
    
    sun = next(c for c in all_cards if c.name == "Sun")
    print(f"  Sun effect_definitions: '{sun.effect_definitions}'")
    
    if sun.effect_definitions != "unsleep:2":
        print(f"✗ Sun should have effect_definitions='unsleep:2'")
        return False
    
    effects = EffectRegistry.get_effects(sun)
    print(f"  Sun has {len(effects)} effect(s): {[e.__class__.__name__ for e in effects]}")
    
    if len(effects) != 1 or effects[0].__class__.__name__ != "UnsleepEffect":
        print(f"✗ Sun should have 1 UnsleepEffect")
        return False
    
    if effects[0].count != 2:
        print(f"✗ Sun should unsleep 2 cards")
        return False
    
    print(f"✓ Sun effect parsed correctly")
    return True


def test_clean_effect_parsing():
    """Test that Clean effect is parsed correctly from CSV."""
    print("\nTesting Clean effect parsing...")
    
    csv_path = Path(__file__).parent.parent / "data" / "cards.csv"
    loader = CardLoader(str(csv_path))
    all_cards = loader.load_cards()
    
    clean = next(c for c in all_cards if c.name == "Clean")
    print(f"  Clean effect_definitions: '{clean.effect_definitions}'")
    
    if clean.effect_definitions != "sleep_all":
        print(f"✗ Clean should have effect_definitions='sleep_all'")
        return False
    
    effects = EffectRegistry.get_effects(clean)
    print(f"  Clean has {len(effects)} effect(s): {[e.__class__.__name__ for e in effects]}")
    
    if len(effects) != 1 or effects[0].__class__.__name__ != "SleepAllEffect":
        print(f"✗ Clean should have 1 SleepAllEffect")
        return False
    
    print(f"✓ Clean effect parsed correctly")
    return True


def test_rush_cc_gain():
    """Test that Rush gains 2 CC when played."""
    print("\nTesting Rush CC gain...")
    
    csv_path = Path(__file__).parent.parent / "data" / "cards.csv"
    loader = CardLoader(str(csv_path))
    all_cards = loader.load_cards()
    
    rush = next(c for c in all_cards if c.name == "Rush")
    rush.owner = "p1"
    rush.controller = "p1"
    
    player1 = Player(
        player_id="p1",
        name="Player 1",
        hand=[rush],
        cc=5,
    )
    
    player2 = Player(
        player_id="p2",
        name="Player 2",
        hand=[],
    )
    
    game_state = GameState(
        game_id="test",
        players={"p1": player1, "p2": player2},
        active_player_id="p1",
        first_player_id="p1",
        turn_number=2,  # Not first turn
        phase=Phase.MAIN,
    )
    
    # Apply Rush effect
    effects = EffectRegistry.get_effects(rush)
    effect = effects[0]
    
    initial_cc = player1.cc
    effect.apply(game_state, player=player1)
    
    print(f"  CC before: {initial_cc}, after: {player1.cc}")
    
    if player1.cc != initial_cc + 2:
        print(f"✗ Rush should gain 2 CC")
        return False
    
    print(f"✓ Rush gains 2 CC correctly")
    return True


def test_rush_first_turn_restriction():
    """Test that Rush cannot be played on first turn."""
    print("\nTesting Rush first turn restriction...")
    
    csv_path = Path(__file__).parent.parent / "data" / "cards.csv"
    loader = CardLoader(str(csv_path))
    all_cards = loader.load_cards()
    
    rush = next(c for c in all_cards if c.name == "Rush")
    rush.owner = "p1"
    rush.controller = "p1"
    
    player1 = Player(
        player_id="p1",
        name="Player 1",
        hand=[rush],
    )
    
    player2 = Player(
        player_id="p2",
        name="Player 2",
        hand=[],
    )
    
    # Test Turn 1 for first player (should be blocked)
    game_state = GameState(
        game_id="test",
        players={"p1": player1, "p2": player2},
        active_player_id="p1",
        first_player_id="p1",
        turn_number=1,
        phase=Phase.MAIN,
    )
    
    effects = EffectRegistry.get_effects(rush)
    effect = effects[0]
    
    can_play_turn1 = effect.can_apply(game_state, player=player1)
    print(f"  Can play on Turn 1 (first player): {can_play_turn1}")
    
    if can_play_turn1:
        print(f"✗ Rush should not be playable on Turn 1 for first player")
        return False
    
    # Test Turn 2 for first player (should be allowed)
    game_state.turn_number = 2
    can_play_turn2 = effect.can_apply(game_state, player=player1)
    print(f"  Can play on Turn 2 (first player): {can_play_turn2}")
    
    if not can_play_turn2:
        print(f"✗ Rush should be playable on Turn 2 for first player")
        return False
    
    # Test Turn 2 for second player (should be blocked - their first turn)
    game_state.active_player_id = "p2"
    can_play_turn2_p2 = effect.can_apply(game_state, player=player2)
    print(f"  Can play on Turn 2 (second player): {can_play_turn2_p2}")
    
    if can_play_turn2_p2:
        print(f"✗ Rush should not be playable on Turn 2 for second player (their first turn)")
        return False
    
    print(f"✓ Rush first turn restriction works correctly")
    return True


def test_clean_sleeps_all_cards():
    """Test that Clean sleeps all cards in play."""
    print("\nTesting Clean sleeps all cards...")
    
    csv_path = Path(__file__).parent.parent / "data" / "cards.csv"
    loader = CardLoader(str(csv_path))
    all_cards = loader.load_cards()
    
    clean = next(c for c in all_cards if c.name == "Clean")
    ka = next(c for c in all_cards if c.name == "Ka")
    wizard = next(c for c in all_cards if c.name == "Wizard")
    demideca = next(c for c in all_cards if c.name == "Demideca")
    
    # Set up cards in play
    ka.owner = "p1"
    ka.controller = "p1"
    wizard.owner = "p1"
    wizard.controller = "p1"
    demideca.owner = "p2"
    demideca.controller = "p2"
    
    player1 = Player(
        player_id="p1",
        name="Player 1",
        hand=[],
        in_play=[ka, wizard],
    )
    
    player2 = Player(
        player_id="p2",
        name="Player 2",
        hand=[],
        in_play=[demideca],
    )
    
    game_state = GameState(
        game_id="test",
        players={"p1": player1, "p2": player2},
        active_player_id="p1",
        first_player_id="p1",
        turn_number=1,
        phase=Phase.MAIN,
    )
    
    print(f"  Before Clean: P1 has {len(player1.in_play)} in play, P2 has {len(player2.in_play)} in play")
    print(f"  Before Clean: P1 has {len(player1.sleep_zone)} sleeping, P2 has {len(player2.sleep_zone)} sleeping")
    
    # Apply Clean effect
    effects = EffectRegistry.get_effects(clean)
    effect = effects[0]
    effect.apply(game_state, player=player1)
    
    print(f"  After Clean: P1 has {len(player1.in_play)} in play, P2 has {len(player2.in_play)} in play")
    print(f"  After Clean: P1 has {len(player1.sleep_zone)} sleeping, P2 has {len(player2.sleep_zone)} sleeping")
    
    if len(player1.in_play) != 0 or len(player2.in_play) != 0:
        print(f"✗ Clean should sleep all cards in play")
        return False
    
    if len(player1.sleep_zone) != 2 or len(player2.sleep_zone) != 1:
        print(f"✗ Clean should move all cards to sleep zones")
        return False
    
    print(f"✓ Clean sleeps all cards correctly")
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("Phase 1 Data-Driven Action Effects Tests")
    print("=" * 60)
    
    tests = [
        test_rush_effect_parsing,
        test_wake_effect_parsing,
        test_sun_effect_parsing,
        test_clean_effect_parsing,
        test_rush_cc_gain,
        test_rush_first_turn_restriction,
        test_clean_sleeps_all_cards,
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
        print("\n✅ All Phase 1 effect tests passed!")
    else:
        print(f"\n❌ {failed} test(s) failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
