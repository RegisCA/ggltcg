"""Simulation deck loader for reading deck configurations from CSV."""

import csv
import logging
import os
from pathlib import Path
from typing import Dict, List

from .config import DeckConfig

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


# Singleton instance for easy access
_default_loader: SimulationDeckLoader | None = None


def get_deck_loader() -> SimulationDeckLoader:
    """
    Get or create the default simulation deck loader instance.
    
    Checks SIMULATION_DECKS_CSV_PATH environment variable first, 
    falls back to default path.
    
    Returns:
        SimulationDeckLoader instance with configured deck path
    """
    global _default_loader
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
