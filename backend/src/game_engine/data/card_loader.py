"""Card loader for reading card data from CSV file."""
import csv
import logging
import random
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
        
        # Parse colors with defaults
        primary_color = '#C74444'  # Default red for Toys
        accent_color = '#C74444'  # Default red accent
        
        # Try to read from CSV first
        if 'primary_color' in row and row['primary_color'] and row['primary_color'].strip():
            primary_color = row['primary_color'].strip()
        elif card_type == CardType.ACTION:
            # Default purple for Actions if not in CSV
            primary_color = '#8B5FA8'
            
        if 'accent_color' in row and row['accent_color'] and row['accent_color'].strip():
            accent_color = row['accent_color'].strip()
        elif card_type == CardType.ACTION:
            # Default purple for Actions if not in CSV
            accent_color = '#8B5FA8'
        
        return Card(
            name=name,
            card_type=card_type,
            cost=cost,
            effect_text=effect,
            speed=speed,
            strength=strength,
            stamina=stamina,
            primary_color=primary_color,
            accent_color=accent_color,
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


def random_deck(num_toys: int, num_actions: int) -> List[str]:
    """
    Generate a random deck of unique cards.
    
    Args:
        num_toys: Number of Toy cards to include (0-6)
        num_actions: Number of Action cards to include (0-6)
        
    Returns:
        List of card names
        
    Raises:
        ValueError: If parameters are invalid or not enough cards available
    """
    # Validate parameters
    if num_toys < 0 or num_actions < 0:
        raise ValueError("Card counts must be non-negative")
    
    total_cards = num_toys + num_actions
    if total_cards != 6:
        raise ValueError(f"Total cards must equal 6, got {total_cards}")
    
    # Load all cards
    all_cards = load_all_cards()
    
    # Separate by type
    toys = [card.name for card in all_cards if card.card_type == CardType.TOY]
    actions = [card.name for card in all_cards if card.card_type == CardType.ACTION]
    
    # Validate we have enough cards
    if len(toys) < num_toys:
        raise ValueError(f"Not enough Toy cards available: requested {num_toys}, have {len(toys)}")
    if len(actions) < num_actions:
        raise ValueError(f"Not enough Action cards available: requested {num_actions}, have {len(actions)}")
    
    # Randomly select cards
    selected_toys = random.sample(toys, num_toys) if num_toys > 0 else []
    selected_actions = random.sample(actions, num_actions) if num_actions > 0 else []
    
    # Combine and shuffle
    deck = selected_toys + selected_actions
    random.shuffle(deck)
    
    logger.info(f"Generated random deck: {num_toys} Toys, {num_actions} Actions - {deck}")
    
    return deck
