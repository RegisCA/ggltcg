"""Simulation deck loader for reading deck configurations from CSV."""

import csv
import logging
import os
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .config import DeckConfig
from game_engine.data.card_loader import load_cards_dict

logger = logging.getLogger(__name__)


class SimulationDeckLoader:
    """Handles loading simulation deck configurations from CSV file."""
    
    def __init__(self, csv_path: str | Path):
        """
        Initialize deck loader.
        
        Args:
            csv_path: Path to the simulation decks CSV file
        """
        self.csv_path = Path(csv_path)
        if not self.csv_path.exists():
            raise FileNotFoundError(f"Simulation decks CSV file not found: {self.csv_path}")
    
    def load_decks(self) -> List[DeckConfig]:
        """
        Load all deck configurations from the CSV file.
        
        Returns:
            List of DeckConfig objects
        """
        decks = []
        
        with open(self.csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                deck = self._parse_deck_row(row)
                decks.append(deck)
        
        logger.info(f"Loaded {len(decks)} simulation decks from {self.csv_path}")
        return decks
    
    def load_decks_dict(self) -> Dict[str, DeckConfig]:
        """
        Load all decks and return as dictionary keyed by name.
        
        Returns:
            Dictionary mapping deck name to DeckConfig object
        """
        decks = self.load_decks()
        return {deck.name: deck for deck in decks}
    
    def _parse_deck_row(self, row: Dict[str, str]) -> DeckConfig:
        """
        Parse a single CSV row into a DeckConfig object.
        
        Args:
            row: Dictionary from CSV DictReader
            
        Returns:
            DeckConfig object
        """
        name = row['deck_name'].strip()
        description = row.get('description', '').strip()
        
        # Extract card names from card1-card6 columns
        cards = []
        for i in range(1, 7):
            card_key = f'card{i}'
            if card_key in row and row[card_key].strip():
                cards.append(row[card_key].strip())
        
        return DeckConfig(
            name=name,
            description=description,
            cards=cards
        )
    
    @staticmethod
    def get_default_deck_path() -> Path:
        """Get the default path to the simulation decks CSV file."""
        # Navigate from src/simulation/ to backend/data/simulation_decks.csv
        return Path(__file__).parent.parent.parent / "data" / "simulation_decks.csv"


# Singleton instance for easy access (thread-safe)
_default_loader: SimulationDeckLoader | None = None
_loader_lock = threading.Lock()


def get_deck_loader() -> SimulationDeckLoader:
    """
    Get or create the default simulation deck loader instance.
    
    Checks SIMULATION_DECKS_CSV_PATH environment variable first, 
    falls back to default path.
    
    Thread-safe using double-checked locking pattern.
    
    Returns:
        SimulationDeckLoader instance with configured deck path
    """
    global _default_loader
    if _default_loader is None:
        with _loader_lock:
            # Double-check after acquiring lock
            if _default_loader is None:
                # Check for environment variable first
                decks_path_str = os.environ.get("SIMULATION_DECKS_CSV_PATH")
                
                if decks_path_str:
                    decks_path = Path(decks_path_str)
                    logger.info(f"Loading simulation decks from environment variable: {decks_path}")
                else:
                    decks_path = SimulationDeckLoader.get_default_deck_path()
                    logger.info(f"Loading simulation decks from default path: {decks_path}")
                
                _default_loader = SimulationDeckLoader(decks_path)
    return _default_loader


def load_simulation_decks() -> List[DeckConfig]:
    """
    Convenience function to load all simulation decks using default path.
    
    Returns:
        List of all DeckConfig objects
    """
    return get_deck_loader().load_decks()


def load_simulation_decks_dict() -> Dict[str, DeckConfig]:
    """
    Convenience function to load all simulation decks as dictionary.
    
    Returns:
        Dictionary mapping deck name to DeckConfig object
    """
    return get_deck_loader().load_decks_dict()


def validate_deck(deck: DeckConfig, card_templates: Optional[Dict[str, any]] = None) -> List[str]:
    """
    Validate a deck configuration against available cards.
    
    Args:
        deck: DeckConfig to validate
        card_templates: Optional dictionary of valid card templates. If None, loads from default path.
        
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    # Load card templates if not provided
    if card_templates is None:
        try:
            card_templates = load_cards_dict()
        except Exception as e:
            errors.append(f"Failed to load card templates: {e}")
            return errors
    
    # Check deck size
    if len(deck.cards) != 6:
        errors.append(f"Deck '{deck.name}' must have exactly 6 cards, has {len(deck.cards)}")
    
    # Check all cards exist
    valid_card_names = set(card_templates.keys())
    for card_name in deck.cards:
        if card_name not in valid_card_names:
            errors.append(f"Card not found in '{deck.name}': '{card_name}'")
            
            # Provide fuzzy match suggestions
            suggestions = _find_similar_card_names(card_name, valid_card_names)
            if suggestions:
                errors.append(f"  Did you mean: {', '.join(suggestions[:3])}?")
    
    # Check for duplicates
    seen = set()
    duplicates = []
    for card_name in deck.cards:
        if card_name in seen:
            duplicates.append(card_name)
        seen.add(card_name)
    
    if duplicates:
        errors.append(f"Duplicate cards in '{deck.name}': {', '.join(set(duplicates))}")
    
    return errors


def validate_deck_names(deck_names: List[str], available_decks: Optional[Dict[str, DeckConfig]] = None) -> List[str]:
    """
    Validate that deck names exist in the available simulation decks.
    
    Args:
        deck_names: List of deck names to validate
        available_decks: Optional dictionary of available decks. If None, loads from default path.
        
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    # Load available decks if not provided
    if available_decks is None:
        try:
            available_decks = load_simulation_decks_dict()
        except Exception as e:
            errors.append(f"Failed to load simulation decks: {e}")
            return errors
    
    # Check each deck name exists
    available_names = set(available_decks.keys())
    for deck_name in deck_names:
        if deck_name not in available_names:
            errors.append(f"Simulation deck not found: '{deck_name}'")
            
            # Provide suggestions
            suggestions = _find_similar_card_names(deck_name, available_names)
            if suggestions:
                errors.append(f"  Did you mean: {', '.join(suggestions[:3])}?")
    
    return errors


def _find_similar_card_names(target: str, valid_names: set[str], max_distance: int = 3) -> List[str]:
    """
    Find card names similar to the target using simple string matching.
    
    Args:
        target: The target string to match
        valid_names: Set of valid names to search
        max_distance: Maximum edit distance (not used in simple implementation)
        
    Returns:
        List of similar names, sorted by relevance
    """
    target_lower = target.lower()
    
    # Collect matches in priority order
    exact_matches = []
    starts_with = []
    contains = []
    similar = []
    
    for name in valid_names:
        name_lower = name.lower()
        
        if name_lower == target_lower:
            exact_matches.append(name)
        elif name_lower.startswith(target_lower) or target_lower.startswith(name_lower):
            starts_with.append(name)
        elif target_lower in name_lower or name_lower in target_lower:
            contains.append(name)
        elif _simple_similarity(target_lower, name_lower) <= max_distance:
            similar.append(name)
    
    # Return in priority order
    return exact_matches + starts_with + contains + similar


def _simple_similarity(s1: str, s2: str) -> int:
    """
    Calculate a simple character difference score between two strings.
    Lower score = more similar.
    
    Args:
        s1: First string
        s2: Second string
        
    Returns:
        Difference score
    """
    # Simple implementation: count character differences
    max_len = max(len(s1), len(s2))
    if max_len == 0:
        return 0
    
    # Count matching characters at same positions
    matches = sum(1 for i in range(min(len(s1), len(s2))) if s1[i] == s2[i])
    
    # Return difference score
    return max_len - matches
