"""Test alternate deck CSV loading functionality."""
import sys
import os
from pathlib import Path

# Add backend/src to path
backend_src = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(backend_src))


def test_alternate_deck_via_env():
    """Test loading cards from an alternate CSV file via environment variable."""
    print("\nTesting alternate deck loading via environment variable...")
    
    # Get path to test CSV
    test_csv = Path(__file__).parent / "test_alternate_deck.csv"
    assert test_csv.exists(), f"Test CSV not found: {test_csv}"
    
    # Set environment variable
    os.environ["CARDS_CSV_PATH"] = str(test_csv)
    
    # Import after setting env var to ensure it's picked up
    from game_engine.data.card_loader import CardLoader
    
    # Create a new loader with the test CSV
    loader = CardLoader(test_csv)
    cards = loader.load_cards()
    
    print(f"✓ Loaded {len(cards)} cards from alternate deck")
    
    # Verify we have 6 cards (4 toys, 2 actions)
    assert len(cards) == 6, f"Expected 6 cards, got {len(cards)}"
    
    # Verify the cards are the test cards
    card_names = [card.name for card in cards]
    assert "TestToy1" in card_names, "TestToy1 not found"
    assert "TestToy2" in card_names, "TestToy2 not found"
    assert "TestToy3" in card_names, "TestToy3 not found"
    assert "TestToy4" in card_names, "TestToy4 not found"
    assert "TestAction1" in card_names, "TestAction1 not found"
    assert "TestAction2" in card_names, "TestAction2 not found"
    
    # Check a specific card
    test_toy1 = next(card for card in cards if card.name == "TestToy1")
    assert test_toy1.is_toy(), "TestToy1 should be a Toy"
    assert test_toy1.speed == 2, f"TestToy1 speed should be 2, got {test_toy1.speed}"
    assert test_toy1.strength == 2, f"TestToy1 strength should be 2, got {test_toy1.strength}"
    assert test_toy1.stamina == 4, f"TestToy1 stamina should be 4, got {test_toy1.stamina}"
    assert test_toy1.cost == 1, f"TestToy1 cost should be 1, got {test_toy1.cost}"
    print(f"✓ TestToy1: Speed {test_toy1.speed}, Strength {test_toy1.strength}, Stamina {test_toy1.stamina}, Cost {test_toy1.cost}")
    
    # Check action card
    test_action1 = next(card for card in cards if card.name == "TestAction1")
    assert test_action1.is_action(), "TestAction1 should be an Action"
    assert test_action1.cost == 0, f"TestAction1 cost should be 0, got {test_action1.cost}"
    print(f"✓ TestAction1: Action card, Cost {test_action1.cost}")
    
    # Clean up environment variable
    del os.environ["CARDS_CSV_PATH"]
    
    print("✅ Alternate deck loading test passed!")


def test_game_service_with_alternate_deck():
    """Test that GameService can use alternate deck CSV."""
    print("\nTesting GameService with alternate deck...")
    
    # Get path to test CSV
    test_csv = Path(__file__).parent / "test_alternate_deck.csv"
    assert test_csv.exists(), f"Test CSV not found: {test_csv}"
    
    # Import and create service directly with test CSV
    from api.game_service import GameService
    
    service = GameService(str(test_csv))
    
    # Verify cards were loaded
    assert len(service.all_cards) == 6, f"Expected 6 cards, got {len(service.all_cards)}"
    
    card_names = [card.name for card in service.all_cards]
    assert "TestToy1" in card_names, "TestToy1 not found in service"
    assert "TestToy2" in card_names, "TestToy2 not found in service"
    assert "TestToy3" in card_names, "TestToy3 not found in service"
    assert "TestToy4" in card_names, "TestToy4 not found in service"
    assert "TestAction1" in card_names, "TestAction1 not found in service"
    assert "TestAction2" in card_names, "TestAction2 not found in service"
    
    print(f"✓ GameService loaded {len(service.all_cards)} cards from alternate deck")
    print("✅ GameService alternate deck test passed!")


if __name__ == "__main__":
    test_alternate_deck_via_env()
    test_game_service_with_alternate_deck()
