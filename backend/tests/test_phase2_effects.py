"""
Tests for Phase 2 data-driven cost modification effects.

Verifies that Wizard and Dream work correctly with the new CSV-driven system.
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


def test_wizard_effect_parsing():
    """Test that Wizard effect is parsed correctly from CSV."""
    print("Testing Wizard effect parsing...")
    
    csv_path = Path(__file__).parent.parent / "data" / "cards.csv"
    loader = CardLoader(str(csv_path))
    all_cards = loader.load_cards()
    
    wizard = next(c for c in all_cards if c.name == "Wizard")
    print(f"  Wizard effect_definitions: '{wizard.effect_definitions}'")
    
    if wizard.effect_definitions != "set_tussle_cost:1":
        print(f"✗ Wizard should have effect_definitions='set_tussle_cost:1'")
        return False
    
    # Get the effect
    effects = EffectRegistry.get_effects(wizard)
    print(f"  Wizard has {len(effects)} effect(s): {[e.__class__.__name__ for e in effects]}")
    
    if len(effects) != 1:
        print(f"✗ Wizard should have 1 effect")
        return False
    
    if effects[0].__class__.__name__ != "SetTussleCostEffect":
        print(f"✗ Wizard effect should be SetTussleCostEffect")
        return False
    
    # Check parameters
    effect = effects[0]
    if effect.cost != 1:
        print(f"✗ Wizard should set tussle cost to 1, got {effect.cost}")
        return False
    
    print(f"✓ Wizard effect parsed correctly")
    return True


def test_dream_effect_parsing():
    """Test that Dream effect is parsed correctly from CSV."""
    print("\nTesting Dream effect parsing...")
    
    csv_path = Path(__file__).parent.parent / "data" / "cards.csv"
    loader = CardLoader(str(csv_path))
    all_cards = loader.load_cards()
    
    dream = next(c for c in all_cards if c.name == "Dream")
    print(f"  Dream effect_definitions: '{dream.effect_definitions}'")
    
    if dream.effect_definitions != "reduce_cost_by_sleeping":
        print(f"✗ Dream should have effect_definitions='reduce_cost_by_sleeping'")
        return False
    
    effects = EffectRegistry.get_effects(dream)
    print(f"  Dream has {len(effects)} effect(s): {[e.__class__.__name__ for e in effects]}")
    
    if len(effects) != 1 or effects[0].__class__.__name__ != "ReduceCostBySleepingEffect":
        print(f"✗ Dream should have 1 ReduceCostBySleepingEffect")
        return False
    
    print(f"✓ Dream effect parsed correctly")
    return True


def test_wizard_sets_tussle_cost():
    """Test that Wizard sets tussle cost to 1 for controller's cards."""
    print("\nTesting Wizard sets tussle cost...")
    
    csv_path = Path(__file__).parent.parent / "data" / "cards.csv"
    loader = CardLoader(str(csv_path))
    all_cards = loader.load_cards()
    
    wizard = next(c for c in all_cards if c.name == "Wizard")
    ka = next(c for c in all_cards if c.name == "Ka")
    
    # Set up Wizard in play
    wizard.owner = "p1"
    wizard.controller = "p1"
    wizard.zone = Zone.IN_PLAY
    
    ka.owner = "p1"
    ka.controller = "p1"
    ka.zone = Zone.IN_PLAY
    
    player1 = Player(
        player_id="p1",
        name="Player 1",
        hand=[],
        in_play=[wizard, ka],
    )
    
    player2 = Player(
        player_id="p2",
        name="Player 2",
        hand=[],
        in_play=[],
    )
    
    game_state = GameState(
        game_id="test",
        players={"p1": player1, "p2": player2},
        active_player_id="p1",
        first_player_id="p1",
        turn_number=2,
        phase=Phase.MAIN,
    )
    
    # Get Wizard's effect
    effects = EffectRegistry.get_effects(wizard)
    effect = effects[0]
    
    # Test tussle cost modification
    base_cost = 3  # Normal tussle cost
    modified_cost = effect.modify_tussle_cost(base_cost, game_state, player1)
    
    print(f"  Base tussle cost: {base_cost}, with Wizard: {modified_cost}")
    
    if modified_cost != 1:
        print(f"✗ Wizard should set tussle cost to 1, got {modified_cost}")
        return False
    
    # Test that it doesn't affect opponent
    opponent_cost = effect.modify_tussle_cost(base_cost, game_state, player2)
    print(f"  Opponent's tussle cost: {opponent_cost}")
    
    if opponent_cost != base_cost:
        print(f"✗ Wizard should not affect opponent's tussle cost")
        return False
    
    print(f"✓ Wizard sets tussle cost correctly")
    return True


def test_dream_cost_reduction_no_sleeping():
    """Test Dream's cost with no sleeping cards."""
    print("\nTesting Dream cost with 0 sleeping cards...")
    
    csv_path = Path(__file__).parent.parent / "data" / "cards.csv"
    loader = CardLoader(str(csv_path))
    all_cards = loader.load_cards()
    
    dream = next(c for c in all_cards if c.name == "Dream")
    dream.owner = "p1"
    dream.controller = "p1"
    
    player1 = Player(
        player_id="p1",
        name="Player 1",
        hand=[dream],
        sleep_zone=[],  # No sleeping cards
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
        turn_number=2,
        phase=Phase.MAIN,
    )
    
    # Get Dream's effect
    effects = EffectRegistry.get_effects(dream)
    effect = effects[0]
    
    # Test cost modification with no sleeping cards
    base_cost = 4  # Dream's base cost
    modified_cost = effect.modify_card_cost(dream, base_cost, game_state, player1)
    
    print(f"  Sleeping cards: {len(player1.sleep_zone)}")
    print(f"  Base cost: {base_cost}, modified cost: {modified_cost}")
    
    if modified_cost != 4:
        print(f"✗ Dream with 0 sleeping cards should cost 4, got {modified_cost}")
        return False
    
    print(f"✓ Dream costs 4 with no sleeping cards")
    return True


def test_dream_cost_reduction_with_sleeping():
    """Test Dream's cost reduction with sleeping cards."""
    print("\nTesting Dream cost reduction with sleeping cards...")
    
    csv_path = Path(__file__).parent.parent / "data" / "cards.csv"
    loader = CardLoader(str(csv_path))
    all_cards = loader.load_cards()
    
    dream = next(c for c in all_cards if c.name == "Dream")
    ka = next(c for c in all_cards if c.name == "Ka")
    wizard = next(c for c in all_cards if c.name == "Wizard")
    beary = next(c for c in all_cards if c.name == "Beary")
    
    dream.owner = "p1"
    dream.controller = "p1"
    
    ka.owner = "p1"
    wizard.owner = "p1"
    beary.owner = "p1"
    
    player1 = Player(
        player_id="p1",
        name="Player 1",
        hand=[dream],
        sleep_zone=[ka, wizard, beary],  # 3 sleeping cards
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
        turn_number=2,
        phase=Phase.MAIN,
    )
    
    # Get Dream's effect
    effects = EffectRegistry.get_effects(dream)
    effect = effects[0]
    
    # Test cost modification with 3 sleeping cards
    base_cost = 4
    modified_cost = effect.modify_card_cost(dream, base_cost, game_state, player1)
    
    print(f"  Sleeping cards: {len(player1.sleep_zone)}")
    print(f"  Base cost: {base_cost}, modified cost: {modified_cost}")
    
    expected_cost = 4 - 3  # 4 base - 3 sleeping = 1
    if modified_cost != expected_cost:
        print(f"✗ Dream with 3 sleeping cards should cost {expected_cost}, got {modified_cost}")
        return False
    
    print(f"✓ Dream costs {expected_cost} with 3 sleeping cards")
    return True


def test_dream_cost_cannot_go_negative():
    """Test that Dream's cost cannot go below 0."""
    print("\nTesting Dream cost cannot go negative...")
    
    csv_path = Path(__file__).parent.parent / "data" / "cards.csv"
    loader = CardLoader(str(csv_path))
    all_cards = loader.load_cards()
    
    dream = next(c for c in all_cards if c.name == "Dream")
    
    # Create 5 cards for sleep zone
    sleeping_cards = [
        next(c for c in all_cards if c.name == "Ka"),
        next(c for c in all_cards if c.name == "Wizard"),
        next(c for c in all_cards if c.name == "Beary"),
        next(c for c in all_cards if c.name == "Knight"),
        next(c for c in all_cards if c.name == "Raggy"),
    ]
    
    dream.owner = "p1"
    dream.controller = "p1"
    
    for card in sleeping_cards:
        card.owner = "p1"
    
    player1 = Player(
        player_id="p1",
        name="Player 1",
        hand=[dream],
        sleep_zone=sleeping_cards,  # 5 sleeping cards (more than Dream's base cost)
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
        turn_number=2,
        phase=Phase.MAIN,
    )
    
    # Get Dream's effect
    effects = EffectRegistry.get_effects(dream)
    effect = effects[0]
    
    # Test cost modification with 5 sleeping cards
    base_cost = 4
    modified_cost = effect.modify_card_cost(dream, base_cost, game_state, player1)
    
    print(f"  Sleeping cards: {len(player1.sleep_zone)}")
    print(f"  Base cost: {base_cost}, modified cost: {modified_cost}")
    
    if modified_cost != 0:
        print(f"✗ Dream cost should not go below 0, got {modified_cost}")
        return False
    
    print(f"✓ Dream cost correctly capped at 0")
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("Phase 2 Data-Driven Cost Modification Effects Tests")
    print("=" * 60)
    
    tests = [
        test_wizard_effect_parsing,
        test_dream_effect_parsing,
        test_wizard_sets_tussle_cost,
        test_dream_cost_reduction_no_sleeping,
        test_dream_cost_reduction_with_sleeping,
        test_dream_cost_cannot_go_negative,
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
        print("\n✅ All Phase 2 effect tests passed!")
    else:
        print(f"\n❌ {failed} test(s) failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
