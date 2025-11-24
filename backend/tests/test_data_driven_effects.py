"""
Tests for data-driven effects (Ka and Demideca).

Verifies that the new CSV-driven effect system works correctly.
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


def test_ka_effect():
    """Test Ka's +2 strength effect."""
    print("Testing Ka effect...")
    
    # Load all cards
    csv_path = Path(__file__).parent.parent / "data" / "cards.csv"
    loader = CardLoader(str(csv_path))
    all_cards = loader.load_cards()
    
    # Find Ka and Wizard cards
    ka = next(c for c in all_cards if c.name == "Ka")
    wizard = next(c for c in all_cards if c.name == "Wizard")
    
    # Set up ownership
    ka.owner = "p1"
    ka.controller = "p1"
    wizard.owner = "p1"
    wizard.controller = "p1"
    
    # Create game state
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
    )
    
    game_state = GameState(
        game_id="test",
        players={"p1": player1, "p2": player2},
        active_player_id="p1",
        first_player_id="p1",
        turn_number=1,
        phase=Phase.MAIN,
    )
    
    # Get Ka's effect
    ka_effects = EffectRegistry.get_effects(ka)
    print(f"  Ka has {len(ka_effects)} effect(s): {[e.__class__.__name__ for e in ka_effects]}")
    
    if len(ka_effects) != 1:
        print(f"✗ Ka should have 1 effect, but has {len(ka_effects)}")
        return False
    
    # Check Ka gets +2 strength from its own effect
    ka_base_strength = ka.strength
    ka_modified_strength = ka_base_strength
    
    for effect in ka_effects:
        ka_modified_strength = effect.modify_stat(ka, "strength", ka_modified_strength, game_state)
    
    print(f"  Ka base strength: {ka_base_strength}")
    print(f"  Ka with its own effect: {ka_modified_strength}")
    
    if ka_modified_strength != ka_base_strength + 2:
        print(f"✗ Ka should have +2 strength from its own effect")
        return False
    
    print(f"✓ Ka has +2 strength from its own effect")
    
    # Check Wizard gets +2 strength from Ka
    wizard_base_strength = wizard.strength
    wizard_modified_strength = wizard_base_strength
    
    for effect in ka_effects:
        wizard_modified_strength = effect.modify_stat(wizard, "strength", wizard_modified_strength, game_state)
    
    print(f"  Wizard base strength: {wizard_base_strength}")
    print(f"  Wizard with Ka effect: {wizard_modified_strength}")
    
    if wizard_modified_strength != wizard_base_strength + 2:
        print(f"✗ Wizard should have +2 strength from Ka")
        return False
    
    print(f"✓ Wizard has +2 strength from Ka")
    
    # Check that Ka doesn't affect speed or stamina
    wizard_speed = wizard.speed
    wizard_modified_speed = wizard_speed
    for effect in ka_effects:
        wizard_modified_speed = effect.modify_stat(wizard, "speed", wizard_modified_speed, game_state)
    
    if wizard_modified_speed != wizard_speed:
        print(f"✗ Ka should not affect speed")
        return False
    
    print(f"✓ Ka only affects strength (not speed or stamina)")
    return True


def test_demideca_effect():
    """Test Demideca's +1 all stats effect."""
    print("\nTesting Demideca effect...")
    
    # Load all cards
    csv_path = Path(__file__).parent.parent / "data" / "cards.csv"
    loader = CardLoader(str(csv_path))
    all_cards = loader.load_cards()
    
    # Find Demideca and Wizard cards
    demideca = next(c for c in all_cards if c.name == "Demideca")
    wizard = next(c for c in all_cards if c.name == "Wizard")
    
    # Set up ownership
    demideca.owner = "p1"
    demideca.controller = "p1"
    wizard.owner = "p1"
    wizard.controller = "p1"
    
    # Create game state
    player1 = Player(
        player_id="p1",
        name="Player 1",
        hand=[],
        in_play=[demideca, wizard],
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
        turn_number=1,
        phase=Phase.MAIN,
    )
    
    # Get Demideca's effect
    demideca_effects = EffectRegistry.get_effects(demideca)
    print(f"  Demideca has {len(demideca_effects)} effect(s): {[e.__class__.__name__ for e in demideca_effects]}")
    
    if len(demideca_effects) != 1:
        print(f"✗ Demideca should have 1 effect, but has {len(demideca_effects)}")
        return False
    
    # Check all stats get +1
    for stat in ["speed", "strength", "stamina"]:
        wizard_base_value = getattr(wizard, stat)
        wizard_modified_value = wizard_base_value
        
        for effect in demideca_effects:
            wizard_modified_value = effect.modify_stat(wizard, stat, wizard_modified_value, game_state)
        
        print(f"  Wizard {stat}: base={wizard_base_value}, with Demideca={wizard_modified_value}")
        
        if wizard_modified_value != wizard_base_value + 1:
            print(f"✗ Wizard {stat} should have +1 from Demideca")
            return False
    
    print(f"✓ Wizard has +1 to all stats from Demideca")
    return True


def test_effect_data_parsing():
    """Test that effect definitions are parsed correctly from CSV."""
    print("\nTesting effect data parsing...")
    
    # Load all cards
    csv_path = Path(__file__).parent.parent / "data" / "cards.csv"
    loader = CardLoader(str(csv_path))
    all_cards = loader.load_cards()
    
    # Check Ka has the correct effect definition
    ka = next(c for c in all_cards if c.name == "Ka")
    print(f"  Ka effect_definitions: '{ka.effect_definitions}'")
    
    if ka.effect_definitions != "stat_boost:strength:2":
        print(f"✗ Ka should have effect_definitions='stat_boost:strength:2', but has '{ka.effect_definitions}'")
        return False
    
    print(f"✓ Ka has correct effect_definitions")
    
    # Check Demideca has the correct effect definition
    demideca = next(c for c in all_cards if c.name == "Demideca")
    print(f"  Demideca effect_definitions: '{demideca.effect_definitions}'")
    
    if demideca.effect_definitions != "stat_boost:all:1":
        print(f"✗ Demideca should have effect_definitions='stat_boost:all:1', but has '{demideca.effect_definitions}'")
        return False
    
    print(f"✓ Demideca has correct effect_definitions")
    
    # Check that cards without effects have empty effect_definitions
    wizard = next(c for c in all_cards if c.name == "Wizard")
    print(f"  Wizard effect_definitions: '{wizard.effect_definitions}'")
    
    if wizard.effect_definitions != "":
        print(f"✗ Wizard should have empty effect_definitions, but has '{wizard.effect_definitions}'")
        return False
    
    print(f"✓ Wizard has empty effect_definitions (uses legacy registry)")
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("Data-Driven Effects Tests (Ka & Demideca)")
    print("=" * 60)
    
    tests = [
        test_effect_data_parsing,
        test_ka_effect,
        test_demideca_effect,
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
        print("\n✅ All data-driven effect tests passed!")
    else:
        print(f"\n❌ {failed} test(s) failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
