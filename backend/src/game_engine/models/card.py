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
    turn_modifications: Dict[str, Any] = field(default_factory=dict)  # Turn-scoped boosts {turn_num: {stat: amount}}
    
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
        """Remove all modifications and transformations when card changes zones."""
        self.modifications = {}
        self.turn_modifications = {}  # Clear turn-scoped modifications too
        if self.stamina is not None:
            self.current_stamina = self.stamina
        
        # Reset Copy card transformation by reloading from definition
        if hasattr(self, '_is_transformed') and self._is_transformed:
            self._reset_copy_transformation()
    
    def _reset_copy_transformation(self):
        """Reset Copy card to original state by reloading from card definition."""
        from ..data.card_loader import load_cards_dict
        
        # Load Copy card definition from CSV (single source of truth)
        try:
            cards_dict = load_cards_dict()
            copy_definition = cards_dict.get("Copy")
            
            if copy_definition:
                # Restore properties from card definition
                self.name = copy_definition.name
                self.card_type = copy_definition.card_type
                self.cost = copy_definition.cost
                self.effect_text = copy_definition.effect_text
                self.effect_definitions = copy_definition.effect_definitions
                self.speed = copy_definition.speed
                self.strength = copy_definition.strength
                self.stamina = copy_definition.stamina
                self.current_stamina = copy_definition.current_stamina
                self.primary_color = copy_definition.primary_color
                self.accent_color = copy_definition.accent_color
            else:
                # Fallback if Copy not found in CSV (shouldn't happen)
                self.name = "Copy"
                self.card_type = CardType.ACTION
                self.cost = -1
                self.effect_text = "This card acts as an exact copy of a card you have in play."
                self.effect_definitions = "copy_card"
                self.speed = None
                self.strength = None
                self.stamina = None
                self.current_stamina = None
                self.primary_color = "#8B5FA8"
                self.accent_color = "#8B5FA8"
        except Exception:
            # Fallback if CardLoader fails (shouldn't happen in normal operation)
            self.name = "Copy"
            self.card_type = CardType.ACTION
            self.cost = -1
            self.effect_text = "This card acts as an exact copy of a card you have in play."
            self.effect_definitions = "copy_card"
            self.speed = None
            self.strength = None
            self.stamina = None
            self.current_stamina = None
            self.primary_color = "#8B5FA8"
            self.accent_color = "#8B5FA8"
        
        # Clean up transformation tracking attributes
        if hasattr(self, '_is_transformed'):
            delattr(self, '_is_transformed')
        if hasattr(self, '_original_name'):
            delattr(self, '_original_name')
        if hasattr(self, '_original_cost'):
            delattr(self, '_original_cost')
        if hasattr(self, '_copied_effects'):
            delattr(self, '_copied_effects')
    
    def get_turn_modification(self, stat_name: str, current_turn: int) -> int:
        """
        Get the turn-scoped modification for a stat.
        
        Turn modifications only apply for the turn they were applied.
        
        Args:
            stat_name: Stat name ("speed", "strength", "stamina", or "all")
            current_turn: Current turn number
            
        Returns:
            Modification amount (0 if no modification for current turn)
        """
        if not self.turn_modifications:
            return 0
        
        total = 0
        for turn_num, mods in self.turn_modifications.items():
            if int(turn_num) == current_turn:
                # Check for specific stat or "all"
                if stat_name in mods:
                    total += mods[stat_name]
                if "all" in mods and stat_name in ("speed", "strength", "stamina"):
                    total += mods["all"]
        return total
    
    def add_turn_modification(self, turn_num: int, stat_name: str, amount: int):
        """
        Add a turn-scoped modification.
        
        Args:
            turn_num: Turn number when this modification was applied
            stat_name: Stat name or "all"
            amount: Amount to modify
        """
        turn_key = str(turn_num)
        if turn_key not in self.turn_modifications:
            self.turn_modifications[turn_key] = {}
        
        # Stack modifications
        current = self.turn_modifications[turn_key].get(stat_name, 0)
        self.turn_modifications[turn_key][stat_name] = current + amount
    
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
