"""
Effect registry for mapping card names to their effect classes.

This module provides a central registry for looking up which effects
belong to each card in the game.
"""

from typing import Dict, List, Type, TYPE_CHECKING
from .base_effect import BaseEffect

if TYPE_CHECKING:
    from ...models.card import Card


class EffectRegistry:
    """
    Central registry for card effects.
    
    Maps card names to their corresponding effect classes.
    Effects are instantiated when needed and attached to cards.
    """
    
    # Will be populated as we implement each effect class
    _effect_map: Dict[str, List[Type[BaseEffect]]] = {}
    
    @classmethod
    def register_effect(cls, card_name: str, effect_class: Type[BaseEffect]) -> None:
        """
        Register an effect class for a card.
        
        Args:
            card_name: Name of the card (e.g., "Ka", "Beary")
            effect_class: The effect class to register
        """
        if card_name not in cls._effect_map:
            cls._effect_map[card_name] = []
        cls._effect_map[card_name].append(effect_class)
    
    @classmethod
    def get_effects(cls, card: "Card") -> List[BaseEffect]:
        """
        Get all effects for a card.
        
        Args:
            card: The card to get effects for
            
        Returns:
            List of instantiated effect objects for this card
        """
        card_name = card.name
        if card_name not in cls._effect_map:
            return []
        
        # Instantiate each effect class with the card as source
        effects = []
        for effect_class in cls._effect_map[card_name]:
            effect = effect_class(card)
            effects.append(effect)
        
        return effects
    
    @classmethod
    def has_effects(cls, card_name: str) -> bool:
        """
        Check if a card has any registered effects.
        
        Args:
            card_name: Name of the card
            
        Returns:
            True if the card has effects registered
        """
        return card_name in cls._effect_map and len(cls._effect_map[card_name]) > 0
    
    @classmethod
    def clear_registry(cls) -> None:
        """Clear all registered effects. Mainly for testing."""
        cls._effect_map.clear()
    
    @classmethod
    def get_all_cards_with_effects(cls) -> List[str]:
        """
        Get list of all card names that have effects.
        
        Returns:
            List of card names
        """
        return list(cls._effect_map.keys())


# Effect registration will happen in each effect module
# They will import this registry and call register_effect()
#
# Example:
# from .effect_registry import EffectRegistry
# EffectRegistry.register_effect("Ka", KaEffect)
