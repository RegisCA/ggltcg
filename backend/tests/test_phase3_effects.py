"""
Tests for Phase 3 of data-driven effect refactoring.

Phase 3: Triggered Effects and Self-Cost Modifications
- Umbruh: Triggered effect (gain CC when sleeped)
- Raggy: Self tussle cost 0 with turn 1 restriction

This phase introduces triggered effects that respond to game events
and self-referential cost modifications with temporal restrictions.
"""

import sys
from pathlib import Path

# Add the src directory to the path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from game_engine.models.game_state import GameState, Phase
from game_engine.models.player import Player
from game_engine.models.card import Card, CardType, Zone
from game_engine.data.card_loader import CardLoader
from game_engine.rules.effects.effect_registry import EffectRegistry, EffectFactory
from game_engine.rules.effects.base_effect import TriggerTiming
from game_engine.game_engine import GameEngine


def test_parse_gain_cc_when_sleeped_effect():
    """Test parsing gain_cc_when_sleeped effect."""
    print("Testing gain_cc_when_sleeped effect parsing...")
    
    csv_path = Path(__file__).parent.parent / "data" / "cards.csv"
    loader = CardLoader(str(csv_path))
    all_cards = loader.load_cards()
    
    umbruh = next(c for c in all_cards if c.name == "Umbruh")
    print(f"  Umbruh effect_definitions: '{umbruh.effect_definitions}'")
    
    if umbruh.effect_definitions != "gain_cc_when_sleeped:1":
        print(f"✗ Umbruh should have effect_definitions='gain_cc_when_sleeped:1'")
        return False
    
    effects = EffectRegistry.get_effects(umbruh)
    print(f"  Umbruh has {len(effects)} effect(s): {[e.__class__.__name__ for e in effects]}")
    
    if len(effects) != 1:
        print(f"✗ Umbruh should have 1 effect")
        return False
    
    if effects[0].__class__.__name__ != "GainCCWhenSleepedEffect":
        print(f"✗ Umbruh effect should be GainCCWhenSleepedEffect")
        return False
    
    effect = effects[0]
    if effect.amount != 1:
        print(f"✗ Umbruh should gain 1 CC, got {effect.amount}")
        return False
    
    if effect.trigger != TriggerTiming.WHEN_SLEEPED:
        print(f"✗ Umbruh should trigger when sleeped")
        return False
    
    print(f"✓ Umbruh effect parsed correctly")
    return True


def test_parse_set_self_tussle_cost_effect():
    """Test parsing set_self_tussle_cost effect with turn restriction."""
    print("\nTesting set_self_tussle_cost effect parsing...")
    
    csv_path = Path(__file__).parent.parent / "data" / "cards.csv"
    loader = CardLoader(str(csv_path))
    all_cards = loader.load_cards()
    
    raggy = next(c for c in all_cards if c.name == "Raggy")
    print(f"  Raggy effect_definitions: '{raggy.effect_definitions}'")
    
    if raggy.effect_definitions != "set_self_tussle_cost:0:not_turn_1":
        print(f"✗ Raggy should have effect_definitions='set_self_tussle_cost:0:not_turn_1'")
        return False
    
    effects = EffectRegistry.get_effects(raggy)
    print(f"  Raggy has {len(effects)} effect(s): {[e.__class__.__name__ for e in effects]}")
    
    if len(effects) != 1:
        print(f"✗ Raggy should have 1 effect")
        return False
    
    if effects[0].__class__.__name__ != "SetSelfTussleCostEffect":
        print(f"✗ Raggy effect should be SetSelfTussleCostEffect")
        return False
    
    effect = effects[0]
    if effect.cost != 0:
        print(f"✗ Raggy tussle cost should be 0, got {effect.cost}")
        return False
    
    if not effect.not_turn_1:
        print(f"✗ Raggy should have not_turn_1 restriction")
        return False
    
    print(f"✓ Raggy effect parsed correctly")
    return True


def test_umbruh_gains_cc_when_sleeped():
    """Test that Umbruh's controller gains CC when sleeped from play."""
    print("\nTesting Umbruh triggered effect...")
    
    # Setup game
    player1 = Player(player_id="player1", name="Player 1")
    player2 = Player(player_id="player2", name="Player 2")
    game_state = GameState(
        game_id="test_game",
        players={player1.player_id: player1, player2.player_id: player2},
        active_player_id=player1.player_id
    )
    game_state.phase = Phase.MAIN
    game_state.turn_number = 2
    game_state.first_player_id = player1.player_id
    
    # Create game engine
    game_engine = GameEngine(game_state)
    
    # Load Umbruh from CSV
    csv_path = Path(__file__).parent.parent / "data" / "cards.csv"
    loader = CardLoader(str(csv_path))
    all_cards = loader.load_cards()
    umbruh = next(c for c in all_cards if c.name == "Umbruh")
    
    # Put Umbruh in play for player1
    umbruh.zone = Zone.IN_PLAY
    umbruh.owner = player1.player_id
    umbruh.controller = player1.player_id
    player1.in_play.append(umbruh)
    
    # Player starts with 5 CC
    player1.cc = 5
    
    print(f"  Player CC before: {player1.cc}")
    
    # Sleep Umbruh from play using GameEngine (which triggers effects)
    game_engine._sleep_card(umbruh, player1, was_in_play=True)
    
    print(f"  Player CC after: {player1.cc}")
    
    if player1.cc != 6:
        print(f"✗ Player should have 6 CC (gained 1), but has {player1.cc}")
        return False
    
    if umbruh not in player1.sleep_zone:
        print(f"✗ Umbruh should be in sleep zone")
        return False
    
    print(f"✓ Umbruh triggered effect works correctly")
    return True


def test_raggy_tussle_cost_and_turn_restriction():
    """Test Raggy's tussle cost and turn 1 restriction."""
    print("\nTesting Raggy cost effect and turn restriction...")
    
    # Setup game
    player1 = Player(player_id="player1", name="Player 1")
    player2 = Player(player_id="player2", name="Player 2")
    game_state = GameState(
        game_id="test_game",
        players={player1.player_id: player1, player2.player_id: player2},
        active_player_id=player1.player_id
    )
    game_state.phase = Phase.MAIN
    game_state.first_player_id = player1.player_id
    
    # Load Raggy from CSV
    csv_path = Path(__file__).parent.parent / "data" / "cards.csv"
    loader = CardLoader(str(csv_path))
    all_cards = loader.load_cards()
    raggy = next(c for c in all_cards if c.name == "Raggy")
    
    # Get effect
    effects = EffectRegistry.get_effects(raggy)
    effect = effects[0]
    
    # Test turn 1 restriction
    game_state.turn_number = 1
    can_tussle_t1 = effect.can_tussle(game_state)
    print(f"  Can tussle on turn 1: {can_tussle_t1}")
    
    if can_tussle_t1:
        print(f"✗ Raggy should NOT be able to tussle on turn 1")
        return False
    
    # Test turn 2 (can tussle)
    game_state.turn_number = 2
    can_tussle_t2 = effect.can_tussle(game_state)
    print(f"  Can tussle on turn 2: {can_tussle_t2}")
    
    if not can_tussle_t2:
        print(f"✗ Raggy SHOULD be able to tussle on turn 2")
        return False
    
    # Test tussle cost is 0
    tussle_cost = effect.modify_tussle_cost(2, game_state, player1)
    print(f"  Tussle cost: {tussle_cost}")
    
    if tussle_cost != 0:
        print(f"✗ Raggy tussle cost should be 0, got {tussle_cost}")
        return False
    
    print(f"✓ Raggy cost effect and restriction work correctly")
    return True


def test_clean_sleeps_umbruh_and_triggers():
    """Test that Clean sleeping Umbruh triggers its effect."""
    print("\nTesting Clean + Umbruh interaction...")
    
    # Setup game
    player1 = Player(player_id="player1", name="Player 1")
    player2 = Player(player_id="player2", name="Player 2")
    game_state = GameState(
        game_id="test_game",
        players={player1.player_id: player1, player2.player_id: player2},
        active_player_id=player1.player_id
    )
    game_state.phase = Phase.MAIN
    game_state.turn_number = 2
    game_state.first_player_id = player1.player_id
    
    # Create game engine
    game_engine = GameEngine(game_state)
    
    # Load cards
    csv_path = Path(__file__).parent.parent / "data" / "cards.csv"
    loader = CardLoader(str(csv_path))
    all_cards = loader.load_cards()
    
    umbruh = next(c for c in all_cards if c.name == "Umbruh")
    clean = next(c for c in all_cards if c.name == "Clean")
    
    # Put Umbruh in play for player1
    umbruh.zone = Zone.IN_PLAY
    umbruh.owner = player1.player_id
    umbruh.controller = player1.player_id
    player1.in_play.append(umbruh)
    
    # Player starts with 3 CC
    player1.cc = 3
    
    print(f"  Player CC before Clean: {player1.cc}")
    print(f"  Umbruh in play: {umbruh in player1.in_play}")
    
    # Play Clean (should sleep Umbruh and trigger effect)
    clean_effects = EffectRegistry.get_effects(clean)
    clean_effect = clean_effects[0]
    # Pass game_engine so Clean can properly trigger when-sleeped effects
    clean_effect.apply(game_engine.game_state, player=player1, game_engine=game_engine)
    
    print(f"  Player CC after Clean: {player1.cc}")
    print(f"  Umbruh in sleep: {umbruh in player1.sleep_zone}")
    
    if player1.cc != 4:
        print(f"✗ Player should have 4 CC (3 + 1 from Umbruh trigger), but has {player1.cc}")
        return False
    
    if umbruh not in player1.sleep_zone:
        print(f"✗ Umbruh should be in sleep zone")
        return False
    
    print(f"✓ Clean + Umbruh interaction works correctly")
    return True


if __name__ == "__main__":
    print("=" * 70)
    print("PHASE 3 EFFECT TESTS")
    print("=" * 70)
    
    tests = [
        test_parse_gain_cc_when_sleeped_effect,
        test_parse_set_self_tussle_cost_effect,
        test_umbruh_gains_cc_when_sleeped,
        test_raggy_tussle_cost_and_turn_restriction,
        test_clean_sleeps_umbruh_and_triggers,
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
            print(f"✗ Test failed with exception: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 70)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 70)
    
    exit(0 if failed == 0 else 1)
