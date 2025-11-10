"""Card loader for reading card data from CSV file."""
import csv
import logging
from pathlib import Path
from typing import List, Dict
from ..models.card import Card, CardType

logger = logging.getLogger(__name__)


class CardLoader:
    """Handles loading card data from CSV file."""
    
    def __init__(self, csv_path: str | Path):
        """
        Initialize card loader.
        
        Args:
            csv_path: Path to the cards CSV file
        """
        self.csv_path = Path(csv_path)
        if not self.csv_path.exists():
            raise FileNotFoundError(f"Card CSV file not found: {self.csv_path}")
    
    def load_cards(self) -> List[Card]:
        """
        Load all cards from the CSV file.
        
        Returns:
            List of Card objects
        """
        cards = []
        
        with open(self.csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                card = self._parse_card_row(row)
                cards.append(card)
        
        return cards
    
    def load_cards_dict(self) -> Dict[str, Card]:
        """
        Load all cards and return as dictionary keyed by name.
        
        Returns:
            Dictionary mapping card name to Card object
        """
        cards = self.load_cards()
        return {card.name: card for card in cards}
    
    def _parse_card_row(self, row: Dict[str, str]) -> Card:
        """
        Parse a single CSV row into a Card object.
        
        Args:
            row: Dictionary from CSV DictReader
            
        Returns:
            Card object
        """
        name = row['name'].strip()
        effect = row['effect'].strip()
        
        # Determine card type based on presence of stats
        has_stats = row['speed'].strip() and row['strength'].strip() and row['stamina'].strip()
        card_type = CardType.TOY if has_stats else CardType.ACTION
        
        # Parse cost (handle special case of "?" for Copy)
        cost_str = row['cost'].strip()
        if cost_str == '?':
            cost = -1  # Special marker for variable cost
        else:
            try:
                cost = int(cost_str)
            except ValueError:
                cost = 0
        
        # Parse stats (only for Toys)
        speed = None
        strength = None
        stamina = None
        
        if card_type == CardType.TOY:
            try:
                speed = int(row['speed'].strip())
                strength = int(row['strength'].strip())
                stamina = int(row['stamina'].strip())
            except (ValueError, KeyError):
                # If stats are missing or invalid, treat as Action
                card_type = CardType.ACTION
        
        return Card(
            name=name,
            card_type=card_type,
            cost=cost,
            effect_text=effect,
            speed=speed,
            strength=strength,
            stamina=stamina,
        )
    
    @staticmethod
    def get_default_card_path() -> Path:
        """Get the default path to the cards CSV file."""
        # Navigate from data/ to backend/data/cards.csv
        return Path(__file__).parent.parent.parent.parent / "data" / "cards.csv"


# Singleton instance for easy access
_default_loader = None


def get_card_loader() -> CardLoader:
    """
    Get or create the default card loader instance.
    
    Returns:
        CardLoader instance with default card path
    """
    global _default_loader
    if _default_loader is None:
        _default_loader = CardLoader(CardLoader.get_default_card_path())
    return _default_loader


def load_all_cards() -> List[Card]:
    """
    Convenience function to load all cards using default path.
    
    Returns:
        List of all Card objects
    """
    return get_card_loader().load_cards()


def load_cards_dict() -> Dict[str, Card]:
    """
    Convenience function to load all cards as dictionary.
    
    Returns:
        Dictionary mapping card name to Card object
    """
    return get_card_loader().load_cards_dict()
