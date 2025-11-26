"""Core data models for GGLTCG game engine."""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum
import uuid


class CardType(Enum):
    """Type of card."""
    TOY = "Toy"
    ACTION = "Action"


class Zone(Enum):
    """Game zones where cards can be located."""
    HAND = "Hand"
    IN_PLAY = "InPlay"
    SLEEP = "Sleep"


@dataclass
class Card:
    """
    Represents a card in the game.
    
    Attributes:
        id: Unique identifier for this card instance
        name: Card name (e.g., "Ka", "Twist")
        card_type: Type of card (Toy or Action)
        cost: CC cost to play the card
        effect_text: Text description of card's effect
        effect_definitions: Data-driven effect definitions from CSV (e.g., "stat_boost:strength:2")
        speed: Speed stat (Toys only)
        strength: Strength stat (Toys only)
        stamina: Stamina stat (Toys only)
        primary_color: Hex code for card border color (based on faction/type)
        accent_color: Hex code for icons and accents (based on faction/type)
        owner: Player ID who owns this card
        controller: Player ID who controls this card (can differ due to Twist)
        zone: Current zone where card is located
        current_stamina: Current stamina (can be reduced in tussles)
        modifications: Temporary stat modifications applied to this card
    """
    name: str
    card_type: CardType
    cost: int  # Can be -1 for variable cost cards like Copy
    effect_text: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    effect_definitions: str = ""  # Data-driven effects from CSV
    speed: Optional[int] = None
    strength: Optional[int] = None
    stamina: Optional[int] = None
    primary_color: str = "#C74444"  # Default red for Toys
    accent_color: str = "#C74444"  # Default red accent
    owner: str = ""
    controller: str = ""
    zone: Zone = Zone.HAND
    current_stamina: Optional[int] = None
    modifications: Dict[str, int] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize current_stamina to base stamina."""
        if self.stamina is not None and self.current_stamina is None:
            self.current_stamina = self.stamina
    
    def is_toy(self) -> bool:
        """Check if this is a Toy card."""
        return self.card_type == CardType.TOY
    
    def is_action(self) -> bool:
        """Check if this is an Action card."""
        return self.card_type == CardType.ACTION
    
    def reset_modifications(self):
        """Remove all modifications when card changes zones."""
        self.modifications = {}
        if self.stamina is not None:
            self.current_stamina = self.stamina
    
    def get_effective_speed(self) -> int:
        """Get speed including modifications."""
        if self.speed is None:
            return 0
        return self.speed + self.modifications.get("speed", 0)
    
    def get_effective_strength(self) -> int:
        """Get strength including modifications."""
        if self.strength is None:
            return 0
        return self.strength + self.modifications.get("strength", 0)
    
    def get_effective_stamina(self) -> int:
        """Get current stamina including modifications."""
        if self.current_stamina is None:
            return 0
        return self.current_stamina + self.modifications.get("stamina", 0)
    
    def apply_damage(self, damage: int):
        """Reduce current stamina by damage amount."""
        if self.current_stamina is not None:
            self.current_stamina -= damage
    
    def is_defeated(self) -> bool:
        """Check if card has 0 or less stamina."""
        return self.get_effective_stamina() <= 0
    
    def has_effect_type(self, effect_class) -> bool:
        """
        Check if this card has an effect of the specified type.
        
        This is the correct way to check for card-specific behavior instead of
        comparing card names.
        
        Args:
            effect_class: The effect class to check for (e.g., BallaberCostEffect)
            
        Returns:
            True if the card has an effect of this type
            
        Example:
            if card.has_effect_type(BallaberCostEffect):
                # Handle Ballaber's alternative cost
        """
        from ..rules.effects.effect_registry import EffectRegistry
        effects = EffectRegistry.get_effects(self)
        return any(isinstance(e, effect_class) for e in effects)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize card to dictionary for API responses."""
        return {
            "name": self.name,
            "card_type": self.card_type.value,
            "cost": self.cost,
            "effect_text": self.effect_text,
            "speed": self.speed,
            "strength": self.strength,
            "stamina": self.stamina,
            "primary_color": self.primary_color,
            "accent_color": self.accent_color,
            "owner": self.owner,
            "controller": self.controller,
            "zone": self.zone.value,
            "current_stamina": self.current_stamina,
            "modifications": self.modifications,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Card':
        """Deserialize card from dictionary."""
        return cls(
            name=data["name"],
            card_type=CardType(data["card_type"]),
            cost=data["cost"],
            effect_text=data["effect_text"],
            speed=data.get("speed"),
            strength=data.get("strength"),
            stamina=data.get("stamina"),
            primary_color=data.get("primary_color", "#C74444"),
            accent_color=data.get("accent_color", "#C74444"),
            owner=data.get("owner", ""),
            controller=data.get("controller", ""),
            zone=Zone(data.get("zone", "Hand")),
            current_stamina=data.get("current_stamina"),
            modifications=data.get("modifications", {}),
        )
