"""Test card loading functionality."""
import sys
from pathlib import Path

# Add backend/src to path
backend_src = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(backend_src))

from game_engine.data.card_loader import load_all_cards, load_cards_dict


def test_load_cards():
    """Test loading all cards from CSV."""
    print("Testing card loader...")
    
    cards = load_all_cards()
    print(f"✓ Loaded {len(cards)} cards")
    
    # Verify we have 26 cards (17 original + 9 new cards from Issue #204)
    assert len(cards) == 26, f"Expected 26 cards, got {len(cards)}"
    
    # Check some specific cards
    cards_dict = load_cards_dict()
    
    # Test Toy card
    beary = cards_dict.get("Beary")
    assert beary is not None, "Beary not found"
    assert beary.is_toy(), "Beary should be a Toy"
    assert beary.speed == 5, f"Beary speed should be 5, got {beary.speed}"
    assert beary.strength == 3, f"Beary strength should be 3, got {beary.strength}"
    assert beary.stamina == 3, f"Beary stamina should be 3, got {beary.stamina}"
    assert beary.cost == 1, f"Beary cost should be 1, got {beary.cost}"
    assert beary.primary_color == "#C74444", f"Beary primary_color should be #C74444, got {beary.primary_color}"
    assert beary.accent_color == "#C74444", f"Beary accent_color should be #C74444, got {beary.accent_color}"
    print(f"✓ Beary: {beary.name} - Speed {beary.speed}, Strength {beary.strength}, Stamina {beary.stamina}, Cost {beary.cost}")
    
    # Test Action card
    rush = cards_dict.get("Rush")
    assert rush is not None, "Rush not found"
    assert rush.is_action(), "Rush should be an Action"
    assert rush.speed is None, "Rush should not have speed"
    assert rush.cost == 0, f"Rush cost should be 0, got {rush.cost}"
    assert rush.primary_color == "#ffeb99", f"Rush primary_color should be #ffeb99, got {rush.primary_color}"
    assert rush.accent_color == "#ffa51f", f"Rush accent_color should be #ffa51f, got {rush.accent_color}"
    print(f"✓ Rush: {rush.name} - Action card, Cost {rush.cost}")
    
    # Test variable cost card
    copy = cards_dict.get("Copy")
    assert copy is not None, "Copy not found"
    assert copy.cost == -1, f"Copy cost should be -1 (variable), got {copy.cost}"
    print(f"✓ Copy: {copy.name} - Variable cost card")
    
    # Test Dream (cost reduction)
    dream = cards_dict.get("Dream")
    assert dream is not None, "Dream not found"
    assert dream.cost == 4, f"Dream base cost should be 4, got {dream.cost}"
    print(f"✓ Dream: {dream.name} - Base cost {dream.cost}")
    
    # Print all cards
    print("\nAll Cards:")
    print("-" * 80)
    for card in sorted(cards, key=lambda c: c.name):
        if card.is_toy():
            print(f"  {card.name:12} | TOY    | Cost: {card.cost:2} | {card.speed}/{card.strength}/{card.stamina}")
        else:
            print(f"  {card.name:12} | ACTION | Cost: {card.cost:2} | {card.effect_text[:50]}...")
    
    print("\n✅ All card loading tests passed!")


if __name__ == "__main__":
    test_load_cards()
