"""
Tests for the GGLTCG effect system.

Tests that all card effects are properly registered and can be instantiated.
"""

import sys
from pathlib import Path

# Add the src directory to the path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from game_engine.rules.effects import EffectRegistry
from game_engine.data.card_loader import CardLoader


def test_effect_registry():
    """Test that all cards with effects are properly registered.

    All gameplay effects are now data-driven via `effect_definitions` in
    cards.csv (parsed by EffectFactory), not the legacy name-based
    `EffectRegistry._effect_map`. No card registers through
    `EffectRegistry.register_effect()` anymore, so the legacy map is
    expected to be empty.
    """
    print("Testing effect registry...")

    # Cards that should have effects
    cards_with_effects = {
        # Continuous effects
        "Ka", "Wizard", "Demideca", "Raggy",
        "Knight",  # 2 effects: protection + win condition
        "Beary",   # 2 effects: protection + tussle cancel
        "Archer",  # 2 effects: restriction + activated ability

        # Triggered effects
        "Umbruh",

        # Action effects
        "Clean", "Rush", "Wake", "Sun", "Toynado", "Twist", "Copy",
    }

    csv_path = Path(__file__).parent.parent / "data" / "cards.csv"
    loader = CardLoader(str(csv_path))
    all_cards = loader.load_cards()

    missing = set()
    for card_name in cards_with_effects:
        card = next((c for c in all_cards if c.name == card_name), None)
        if not card or not card.effect_definitions:
            missing.add(card_name)

    assert not missing, f"Missing data-driven effect_definitions for: {missing}"

    print("✓ All expected cards have data-driven effect_definitions")


def test_effect_instantiation():
    """Test that effects can be instantiated for each card."""
    print("\nTesting effect instantiation...")

    # Load all cards
    csv_path = Path(__file__).parent.parent / "data" / "cards.csv"
    loader = CardLoader(str(csv_path))
    all_cards = loader.load_cards()

    # All gameplay effects are data-driven via effect_definitions now;
    # exercise instantiation for every card that declares one.
    cards_with_effects = [c.name for c in all_cards if c.effect_definitions]

    for card_name in cards_with_effects:
        # Find the card
        card = next((c for c in all_cards if c.name == card_name), None)
        assert card, f"Card '{card_name}' not found in card data"

        # Get effects for this card
        effects = EffectRegistry.get_effects(card)

        assert effects, f"No effects returned for '{card_name}'"

        print(f"✓ {card_name}: {len(effects)} effect(s) - {[e.__class__.__name__ for e in effects]}")


def test_effect_types():
    """Test that effects have correct types."""
    print("\nTesting effect types...")
    
    from game_engine.rules.effects import EffectType
    
    csv_path = Path(__file__).parent.parent / "data" / "cards.csv"
    loader = CardLoader(str(csv_path))
    all_cards = loader.load_cards()
    
    # Test a few specific cards
    test_cases = {
        "Ka": EffectType.CONTINUOUS,
        "Umbruh": EffectType.TRIGGERED,
        "Clean": EffectType.PLAY,
        "Archer": [EffectType.CONTINUOUS, EffectType.ACTIVATED],  # Has both
    }
    
    for card_name, expected_type in test_cases.items():
        card = next((c for c in all_cards if c.name == card_name), None)
        if not card:
            continue
        
        effects = EffectRegistry.get_effects(card)
        
        if isinstance(expected_type, list):
            effect_types = [e.effect_type for e in effects]
            for et in expected_type:
                assert et in effect_types, f"{card_name} missing expected type {et}"
            print(f"✓ {card_name} has all expected effect types")
        else:
            assert any(e.effect_type == expected_type for e in effects), (
                f"{card_name} expected type {expected_type}, got {[e.effect_type for e in effects]}"
            )
            print(f"✓ {card_name} has correct effect type")


def main():
    """Run all tests."""
    print("=" * 60)
    print("GGLTCG Effect System Tests")
    print("=" * 60)
    
    tests = [
        test_effect_registry,
        test_effect_instantiation,
        test_effect_types,
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
        print("\n✅ All effect system tests passed!")
    else:
        print(f"\n❌ {failed} test(s) failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
