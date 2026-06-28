"""
Tests for Phase 3 of data-driven effect refactoring.

Phase 3: Triggered Effects and Self-Cost Modifications
- Umbruh: Triggered effect (gain Charge when broken)
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


def test_parse_gain_charge_when_broken_effect():
    """Test parsing gain_charge_when_broken effect."""
    print("Testing gain_charge_when_broken effect parsing...")
    
    csv_path = Path(__file__).parent.parent / "data" / "cards.csv"
    loader = CardLoader(str(csv_path))
    all_cards = loader.load_cards()
    
    umbruh = next(c for c in all_cards if c.name == "Umbruh")
    print(f"  Umbruh effect_definitions: '{umbruh.effect_definitions}'")
    
    assert umbruh.effect_definitions == "gain_charge_when_broken:1", (
        "Umbruh should have effect_definitions='gain_charge_when_broken:1'"
    )

    effects = EffectRegistry.get_effects(umbruh)
    print(f"  Umbruh has {len(effects)} effect(s): {[e.__class__.__name__ for e in effects]}")

    assert len(effects) == 1, "Umbruh should have 1 effect"
    assert effects[0].__class__.__name__ == "GainChargeWhenBrokenEffect", (
        "Umbruh effect should be GainChargeWhenBrokenEffect"
    )

    effect = effects[0]
    assert effect.amount == 1, f"Umbruh should gain 1 Charge, got {effect.amount}"
    assert effect.trigger == TriggerTiming.WHEN_BROKEN, "Umbruh should trigger when broken"

    print(f"✓ Umbruh effect parsed correctly")


def test_parse_set_self_tussle_cost_effect():
    """Test parsing set_self_tussle_cost effect with turn restriction."""
    print("\nTesting set_self_tussle_cost effect parsing...")
    
    csv_path = Path(__file__).parent.parent / "data" / "cards.csv"
    loader = CardLoader(str(csv_path))
    all_cards = loader.load_cards()
    
    raggy = next(c for c in all_cards if c.name == "Raggy")
    print(f"  Raggy effect_definitions: '{raggy.effect_definitions}'")
    
    assert raggy.effect_definitions == "set_self_tussle_cost:0:not_turn_1", (
        "Raggy should have effect_definitions='set_self_tussle_cost:0:not_turn_1'"
    )

    effects = EffectRegistry.get_effects(raggy)
    print(f"  Raggy has {len(effects)} effect(s): {[e.__class__.__name__ for e in effects]}")

    assert len(effects) == 1, "Raggy should have 1 effect"
    assert effects[0].__class__.__name__ == "SetSelfTussleCostEffect", (
        "Raggy effect should be SetSelfTussleCostEffect"
    )

    effect = effects[0]
    assert effect.cost == 0, f"Raggy tussle cost should be 0, got {effect.cost}"
    assert effect.not_turn_1, "Raggy should have not_turn_1 restriction"

    print(f"✓ Raggy effect parsed correctly")


def test_umbruh_gains_charge_when_broken():
    """Test that Umbruh's controller gains Charge when broken from play."""
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
    
    # Player starts with 5 Charge
    player1.charge = 5
    
    print(f"  Player Charge before: {player1.charge}")
    
    # Break Umbruh from play using GameEngine (which triggers effects)
    game_engine._break_card(umbruh, player1, was_in_play=True)
    
    print(f"  Player Charge after: {player1.charge}")
    
    assert player1.charge == 6, f"Player should have 6 Charge (gained 1), but has {player1.charge}"
    assert umbruh in player1.break_zone, "Umbruh should be in break zone"

    print(f"✓ Umbruh triggered effect works correctly")


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
    
    assert not can_tussle_t1, "Raggy should NOT be able to tussle on turn 1"

    # Test turn 2 (can tussle)
    game_state.turn_number = 2
    can_tussle_t2 = effect.can_tussle(game_state)
    print(f"  Can tussle on turn 2: {can_tussle_t2}")

    assert can_tussle_t2, "Raggy SHOULD be able to tussle on turn 2"

    # Test tussle cost is 0
    tussle_cost = effect.modify_tussle_cost(2, game_state, player1)
    print(f"  Tussle cost: {tussle_cost}")

    assert tussle_cost == 0, f"Raggy tussle cost should be 0, got {tussle_cost}"

    print(f"✓ Raggy cost effect and restriction work correctly")


def test_clean_breaks_umbruh_and_triggers():
    """Test that Clean broken Umbruh triggers its effect."""
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
    
    # Player starts with 3 Charge
    player1.charge = 3
    
    print(f"  Player Charge before Clean: {player1.charge}")
    print(f"  Umbruh in play: {umbruh in player1.in_play}")
    
    # Play Clean (should break Umbruh and trigger effect)
    clean_effects = EffectRegistry.get_effects(clean)
    clean_effect = clean_effects[0]
    # Pass game_engine so Clean can properly trigger when-broken effects
    clean_effect.apply(game_engine.game_state, player=player1, game_engine=game_engine)
    
    print(f"  Player Charge after Clean: {player1.charge}")
    print(f"  Umbruh in break: {umbruh in player1.break_zone}")
    
    assert player1.charge == 4, f"Player should have 4 Charge (3 + 1 from Umbruh trigger), but has {player1.charge}"
    assert umbruh in player1.break_zone, "Umbruh should be in break zone"

    print(f"✓ Clean + Umbruh interaction works correctly")


if __name__ == "__main__":
    print("=" * 70)
    print("PHASE 3 EFFECT TESTS")
    print("=" * 70)
    
    tests = [
        test_parse_gain_charge_when_broken_effect,
        test_parse_set_self_tussle_cost_effect,
        test_umbruh_gains_charge_when_broken,
        test_raggy_tussle_cost_and_turn_restriction,
        test_clean_breaks_umbruh_and_triggers,
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
