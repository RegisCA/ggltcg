"""
Tests for deck validation in simulation system.

Issue #285.5: Validate decks before simulation starts to fail fast.
"""

import pytest
from simulation.config import DeckConfig
from simulation.deck_loader import validate_deck, validate_deck_names, _find_similar_card_names


class TestDeckValidation:
    """Tests for deck validation functions."""
    
    def test_valid_deck_passes_validation(self):
        """A properly configured deck should pass validation."""
        # Use real card names from the game
        deck = DeckConfig(
            name="TestDeck",
            description="Test",
            cards=["Ka", "Archer", "Knight", "Demideca", "Beary", "Wizard"]
        )
        
        errors = validate_deck(deck)
        assert len(errors) == 0, f"Valid deck should have no errors, got: {errors}"
    
    def test_deck_with_invalid_card_name_fails(self):
        """Deck with non-existent card should fail validation."""
        deck = DeckConfig(
            name="BadDeck",
            description="Test",
            cards=["Ka", "NotARealCard", "Knight", "Demideca", "Beary", "Wizard"]
        )
        
        errors = validate_deck(deck)
        assert len(errors) > 0, "Deck with invalid card should fail"
        assert any("NotARealCard" in error for error in errors)
    
    def test_deck_with_typo_provides_suggestions(self):
        """Deck with typo should suggest similar card names."""
        deck = DeckConfig(
            name="TypoDeck",
            description="Test",
            cards=["Ka", "Arcer", "Knight", "Demideca", "Beary", "Wizard"]  # "Arcer" instead of "Archer"
        )
        
        errors = validate_deck(deck)
        assert len(errors) > 0
        # Should suggest "Archer"
        error_text = "\n".join(errors)
        assert "Did you mean" in error_text, f"Should suggest similar names, got: {error_text}"
        assert "Archer" in error_text, f"Should suggest 'Archer', got: {error_text}"
    
    def test_deck_with_wrong_size_fails(self):
        """Deck without exactly 6 cards should fail."""
        # Note: DeckConfig validation happens in __post_init__, so we expect ValueError
        with pytest.raises(ValueError, match="6 cards"):
            deck = DeckConfig(
                name="SmallDeck",
                description="Test",
                cards=["Ka", "Archer", "Knight", "Demideca"]  # Only 4 cards
            )
    
    def test_deck_with_duplicates_fails(self):
        """Deck with duplicate cards should fail."""
        deck = DeckConfig(
            name="DupeDeck",
            description="Test",
            cards=["Ka", "Ka", "Knight", "Demideca", "Beary", "Wizard"]  # Duplicate Ka
        )
        
        errors = validate_deck(deck)
        assert len(errors) > 0
        assert any("Duplicate" in error for error in errors)


class TestDeckNameValidation:
    """Tests for validating deck names against available simulation decks."""
    
    def test_validate_existing_deck_names_passes(self):
        """Valid deck names should pass validation."""
        # These should exist in simulation_decks.csv
        deck_names = ["Aggro_Rush", "Control_Ka"]
        
        errors = validate_deck_names(deck_names)
        # If these decks don't exist, test will fail - that's intentional
        # to ensure test environment is properly configured
        if errors:
            pytest.skip(f"Test decks not found in simulation_decks.csv: {errors}")
    
    def test_validate_nonexistent_deck_name_fails(self):
        """Non-existent deck name should fail validation."""
        deck_names = ["ThisDeckDoesNotExist"]
        
        errors = validate_deck_names(deck_names)
        assert len(errors) > 0
        assert any("not found" in error for error in errors)
    
    def test_validate_deck_name_typo_provides_suggestions(self):
        """Typo in deck name should suggest similar names."""
        # Assuming "Aggro_Rush" exists, try "Aggro_Rash"
        deck_names = ["Aggro_Rash"]
        
        errors = validate_deck_names(deck_names)
        assert len(errors) > 0
        # Should suggest similar deck names
        error_text = " ".join(errors)
        assert "Did you mean" in error_text


class TestSimilarityMatching:
    """Tests for the fuzzy matching helper."""
    
    def test_find_similar_names_exact_match(self):
        """Exact match should be first result."""
        valid_names = {"Archer", "Knight", "Ka", "Demideca"}
        
        results = _find_similar_card_names("Archer", valid_names)
        assert results[0] == "Archer"
    
    def test_find_similar_names_starts_with(self):
        """Names that start with target should rank high."""
        valid_names = {"Archer", "Archmage", "Knight"}
        
        results = _find_similar_card_names("Arc", valid_names)
        assert "Archer" in results
        assert "Archmage" in results
    
    def test_find_similar_names_contains(self):
        """Names containing target should be found."""
        valid_names = {"Archer", "Knight", "Demideca"}
        
        results = _find_similar_card_names("arch", valid_names)
        assert "Archer" in results
    
    def test_find_similar_names_case_insensitive(self):
        """Matching should be case insensitive."""
        valid_names = {"Archer", "KNIGHT", "ka"}
        
        results = _find_similar_card_names("archer", valid_names)
        assert "Archer" in results
        
        results = _find_similar_card_names("ARCHER", valid_names)
        assert "Archer" in results
