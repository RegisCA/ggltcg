#!/usr/bin/env python3
"""
Validate new cards have all required pieces in place.

This script checks that:
1. All cards in CSV have entries in prompts.py CARD_EFFECTS_LIBRARY
2. All effect_definitions in CSV are recognized effect types
3. No orphaned prompts.py entries (cards that don't exist in CSV)

Run this after adding new cards to catch missing pieces.

Usage:
    python scripts/validate_new_cards.py
"""

import csv
import sys
from pathlib import Path

# Add backend/src to path
backend_root = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_root / "src"))

# Known effect types that the system recognizes
KNOWN_EFFECT_TYPES = {
    # Stat boosts
    "stat_boost",
    "turn_stat_boost",
    
    # CC effects
    "gain_cc",
    "start_of_turn_gain_cc",
    "on_card_played_gain_cc",
    "gain_cc_when_sleeped",
    
    # Targeting effects
    "sleep_target",
    "sleep_all",
    "return_target_to_hand",
    "return_all_to_hand",
    "unsleep_target",
    
    # Protection effects
    "opponent_immunity",
    "team_opponent_immunity",
    
    # Combat modifiers
    "auto_win_tussle_on_own_turn",
    "set_tussle_cost",
    "cannot_tussle",
    "free_tussle",
    "no_tussle_turn_1",
    
    # Special effects
    "cascade_sleep",
    "remove_stamina_ability",
    "cost_reduction_per_sleep",
    "alternative_cost_sleep_toy",
    
    # Restrictions/conditions
    "not_first_turn",
}


def load_csv_cards() -> dict[str, dict]:
    """Load all active cards from CSV."""
    csv_path = backend_root / "data" / "cards.csv"
    cards = {}
    
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("status") == "18":  # Active cards only
                cards[row["name"]] = row
    
    return cards


def load_prompts_cards() -> set[str]:
    """Load card names from prompts.py CARD_EFFECTS_LIBRARY."""
    # Import the module
    from game_engine.ai.prompts import CARD_EFFECTS_LIBRARY
    return set(CARD_EFFECTS_LIBRARY.keys())


def parse_effect_definitions(effect_str: str) -> list[str]:
    """Parse effect_definitions string into list of effect types."""
    if not effect_str or not effect_str.strip():
        return []
    
    effects = []
    # Split by semicolon for multiple effects
    for effect in effect_str.split(";"):
        effect = effect.strip()
        if not effect:
            continue
        # Extract the effect type (before first colon)
        effect_type = effect.split(":")[0]
        effects.append(effect_type)
    
    return effects


def validate_cards() -> tuple[list[str], list[str], list[str]]:
    """
    Validate all cards have required pieces.
    
    Returns:
        Tuple of (errors, warnings, info messages)
    """
    errors = []
    warnings = []
    info = []
    
    # Load data
    csv_cards = load_csv_cards()
    prompts_cards = load_prompts_cards()
    
    info.append(f"Found {len(csv_cards)} active cards in CSV")
    info.append(f"Found {len(prompts_cards)} cards in prompts.py")
    
    # Check 1: CSV cards have prompts.py entries
    missing_prompts = set(csv_cards.keys()) - prompts_cards
    if missing_prompts:
        for card in sorted(missing_prompts):
            errors.append(f"Card '{card}' in CSV but missing from prompts.py CARD_EFFECTS_LIBRARY")
    
    # Check 2: No orphaned prompts.py entries
    orphaned_prompts = prompts_cards - set(csv_cards.keys())
    if orphaned_prompts:
        for card in sorted(orphaned_prompts):
            warnings.append(f"Card '{card}' in prompts.py but not in CSV (orphaned entry)")
    
    # Check 3: All effect_definitions are recognized
    for card_name, card_data in csv_cards.items():
        effect_defs = card_data.get("effect_definitions", "")
        effect_types = parse_effect_definitions(effect_defs)
        
        for effect_type in effect_types:
            if effect_type not in KNOWN_EFFECT_TYPES:
                warnings.append(f"Card '{card_name}' uses unknown effect type: '{effect_type}'")
    
    # Check 4: Toy cards have stats
    for card_name, card_data in csv_cards.items():
        # Determine if Toy by checking if it has stats
        has_stats = any([
            card_data.get("speed"),
            card_data.get("strength"),
            card_data.get("stamina")
        ])
        
        if has_stats:
            # Toy should have all three stats
            if not all([
                card_data.get("speed"),
                card_data.get("strength"),
                card_data.get("stamina")
            ]):
                errors.append(f"Toy '{card_name}' is missing some stats (speed/strength/stamina)")
    
    # Check 5: All cards have colors
    for card_name, card_data in csv_cards.items():
        if not card_data.get("primary_color"):
            warnings.append(f"Card '{card_name}' is missing primary_color")
        elif not card_data["primary_color"].startswith("#"):
            errors.append(f"Card '{card_name}' has invalid primary_color: {card_data['primary_color']}")
    
    return errors, warnings, info


def main():
    print("=" * 60)
    print("GGLTCG Card Validation")
    print("=" * 60)
    print()
    
    try:
        errors, warnings, info = validate_cards()
    except Exception as e:
        print(f"❌ Validation failed with error: {e}")
        sys.exit(2)
    
    # Print info
    for msg in info:
        print(f"ℹ️  {msg}")
    print()
    
    # Print warnings
    if warnings:
        print(f"⚠️  {len(warnings)} warning(s):")
        for msg in warnings:
            print(f"   - {msg}")
        print()
    
    # Print errors
    if errors:
        print(f"❌ {len(errors)} error(s):")
        for msg in errors:
            print(f"   - {msg}")
        print()
    
    # Summary
    print("-" * 60)
    if errors:
        print(f"❌ VALIDATION FAILED: {len(errors)} error(s), {len(warnings)} warning(s)")
        sys.exit(1)
    elif warnings:
        print(f"⚠️  VALIDATION PASSED WITH WARNINGS: {len(warnings)} warning(s)")
        sys.exit(0)
    else:
        print("✅ VALIDATION PASSED: All cards are properly configured!")
        sys.exit(0)


if __name__ == "__main__":
    main()
