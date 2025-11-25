"""
Effect registry for mapping card names to their effect classes.

This module provides a central registry for looking up which effects
belong to each card in the game.
"""

from typing import Dict, List, Type, TYPE_CHECKING, Optional
from .base_effect import BaseEffect

if TYPE_CHECKING:
    from ...models.card import Card


class EffectFactory:
    """
    Factory for parsing effect definitions from CSV data.
    
    Effect strings use the format: "effect_type:param1:param2"
    Multiple effects are separated by semicolons: "effect1:p1;effect2:p1:p2"
    
    Examples:
    - "stat_boost:strength:2" -> StatBoostEffect(card, "strength", 2)
    - "stat_boost:all:1" -> StatBoostEffect(card, "all", 1)
    - "stat_boost:strength:2;unsleep" -> [StatBoostEffect(...), UnsleepEffect(...)]
    """
    
    @classmethod
    def parse_effects(cls, effect_string: str, source_card: "Card") -> List[BaseEffect]:
        """
        Parse an effect definition string and return instantiated effects.
        
        Args:
            effect_string: Semicolon-separated effect definitions
            source_card: The card providing these effects
            
        Returns:
            List of instantiated effect objects
            
        Raises:
            ValueError: If effect_string format is invalid
        """
        if not effect_string or not effect_string.strip():
            return []
        
        effects = []
        
        # Split multiple effects
        effect_definitions = [e.strip() for e in effect_string.split(";") if e.strip()]
        
        for definition in effect_definitions:
            # Parse individual effect
            parts = definition.split(":")
            effect_type = parts[0].strip().lower()
            
            # Dispatch to appropriate parser
            if effect_type == "stat_boost":
                effect = cls._parse_stat_boost(parts, source_card)
                effects.append(effect)
            elif effect_type == "gain_cc":
                effect = cls._parse_gain_cc(parts, source_card)
                effects.append(effect)
            elif effect_type == "unsleep":
                effect = cls._parse_unsleep(parts, source_card)
                effects.append(effect)
            elif effect_type == "sleep_all":
                effect = cls._parse_sleep_all(parts, source_card)
                effects.append(effect)
            elif effect_type == "set_tussle_cost":
                effect = cls._parse_set_tussle_cost(parts, source_card)
                effects.append(effect)
            elif effect_type == "reduce_cost_by_sleeping":
                effect = cls._parse_reduce_cost_by_sleeping(parts, source_card)
                effects.append(effect)
            elif effect_type == "gain_cc_when_sleeped":
                effect = cls._parse_gain_cc_when_sleeped(parts, source_card)
                effects.append(effect)
            elif effect_type == "set_self_tussle_cost":
                effect = cls._parse_set_self_tussle_cost(parts, source_card)
                effects.append(effect)
            else:
                raise ValueError(f"Unknown effect type: {effect_type}")
        
        return effects
    
    @classmethod
    def _parse_stat_boost(cls, parts: List[str], source_card: "Card") -> BaseEffect:
        """
        Parse a stat_boost effect definition.
        
        Format: "stat_boost:stat_name:amount"
        - stat_name: "speed", "strength", "stamina", or "all"
        - amount: integer boost amount
        
        Args:
            parts: Split effect definition parts
            source_card: The card providing this effect
            
        Returns:
            StatBoostEffect instance
            
        Raises:
            ValueError: If format is invalid
        """
        if len(parts) != 3:
            raise ValueError(
                f"stat_boost effect requires 2 parameters: stat_name and amount. "
                f"Got {len(parts) - 1} parameters: {':'.join(parts)}"
            )
        
        stat_name = parts[1].strip().lower()
        
        # Validate stat_name
        valid_stats = {"speed", "strength", "stamina", "all"}
        if stat_name not in valid_stats:
            raise ValueError(
                f"Invalid stat_name '{stat_name}' for stat_boost. "
                f"Must be one of: {', '.join(sorted(valid_stats))}"
            )
        
        # Parse amount
        try:
            amount = int(parts[2].strip())
        except ValueError:
            raise ValueError(
                f"Invalid amount '{parts[2]}' for stat_boost. Must be an integer."
            )
        
        # Import here to avoid circular dependency
        from .continuous_effects import StatBoostEffect
        return StatBoostEffect(source_card, stat_name, amount)
    
    @classmethod
    def _parse_gain_cc(cls, parts: List[str], source_card: "Card") -> BaseEffect:
        """
        Parse a gain_cc effect definition.
        
        Format: "gain_cc:amount" or "gain_cc:amount:not_first_turn"
        - amount: integer CC to gain
        - not_first_turn: optional restriction
        
        Args:
            parts: Split effect definition parts
            source_card: The card providing this effect
            
        Returns:
            GainCCEffect instance
            
        Raises:
            ValueError: If format is invalid
        """
        if len(parts) < 2 or len(parts) > 3:
            raise ValueError(
                f"gain_cc effect requires 1-2 parameters: amount and optional restriction. "
                f"Got {len(parts) - 1} parameters: {':'.join(parts)}"
            )
        
        # Parse amount
        try:
            amount = int(parts[1].strip())
        except ValueError:
            raise ValueError(
                f"Invalid amount '{parts[1]}' for gain_cc. Must be an integer."
            )
        
        # Parse optional restriction
        not_first_turn = False
        if len(parts) == 3:
            restriction = parts[2].strip().lower()
            if restriction == "not_first_turn":
                not_first_turn = True
            else:
                raise ValueError(
                    f"Invalid restriction '{restriction}' for gain_cc. "
                    f"Only 'not_first_turn' is supported."
                )
        
        # Import here to avoid circular dependency
        from .action_effects import GainCCEffect
        return GainCCEffect(source_card, amount, not_first_turn)
    
    @classmethod
    def _parse_unsleep(cls, parts: List[str], source_card: "Card") -> BaseEffect:
        """
        Parse an unsleep effect definition.
        
        Format: "unsleep:count"
        - count: integer number of cards to unsleep
        
        Args:
            parts: Split effect definition parts
            source_card: The card providing this effect
            
        Returns:
            UnsleepEffect instance
            
        Raises:
            ValueError: If format is invalid
        """
        if len(parts) != 2:
            raise ValueError(
                f"unsleep effect requires 1 parameter: count. "
                f"Got {len(parts) - 1} parameters: {':'.join(parts)}"
            )
        
        # Parse count
        try:
            count = int(parts[1].strip())
        except ValueError:
            raise ValueError(
                f"Invalid count '{parts[1]}' for unsleep. Must be an integer."
            )
        
        if count < 1:
            raise ValueError(
                f"Invalid count '{count}' for unsleep. Must be at least 1."
            )
        
        # Import here to avoid circular dependency
        from .action_effects import UnsleepEffect
        return UnsleepEffect(source_card, count)
    
    @classmethod
    def _parse_sleep_all(cls, parts: List[str], source_card: "Card") -> BaseEffect:
        """
        Parse a sleep_all effect definition.
        
        Format: "sleep_all" (no parameters)
        
        Args:
            parts: Split effect definition parts
            source_card: The card providing this effect
            
        Returns:
            SleepAllEffect instance
            
        Raises:
            ValueError: If format is invalid
        """
        if len(parts) != 1:
            raise ValueError(
                f"sleep_all effect takes no parameters. "
                f"Got {len(parts) - 1} parameters: {':'.join(parts)}"
            )
        
        # Import here to avoid circular dependency
        from .action_effects import SleepAllEffect
        return SleepAllEffect(source_card)
    
    @classmethod
    def _parse_set_tussle_cost(cls, parts: List[str], source_card: "Card") -> BaseEffect:
        """
        Parse a set_tussle_cost effect definition.
        
        Format: "set_tussle_cost:cost"
        - cost: integer tussle cost (e.g., 1 for Wizard)
        
        Args:
            parts: Split effect definition parts
            source_card: The card providing this effect
            
        Returns:
            SetTussleCostEffect instance
            
        Raises:
            ValueError: If format is invalid
        """
        if len(parts) != 2:
            raise ValueError(
                f"set_tussle_cost effect requires 1 parameter: cost. "
                f"Got {len(parts) - 1} parameters: {':'.join(parts)}"
            )
        
        # Parse cost
        try:
            cost = int(parts[1].strip())
        except ValueError:
            raise ValueError(
                f"Invalid cost '{parts[1]}' for set_tussle_cost. Must be an integer."
            )
        
        if cost < 0:
            raise ValueError(
                f"Invalid cost {cost} for set_tussle_cost. Must be non-negative."
            )
        
        # Import here to avoid circular dependency
        from .continuous_effects import SetTussleCostEffect
        return SetTussleCostEffect(source_card, cost)
    
    @classmethod
    def _parse_reduce_cost_by_sleeping(cls, parts: List[str], source_card: "Card") -> BaseEffect:
        """
        Parse a reduce_cost_by_sleeping effect definition.
        
        Format: "reduce_cost_by_sleeping"
        No parameters - reduces cost by 1 per sleeping card.
        
        Args:
            parts: Split effect definition parts
            source_card: The card providing this effect
            
        Returns:
            ReduceCostBySleepingEffect instance
            
        Raises:
            ValueError: If format is invalid
        """
        if len(parts) != 1:
            raise ValueError(
                f"reduce_cost_by_sleeping effect takes no parameters. "
                f"Got {len(parts) - 1} parameters: {':'.join(parts)}"
            )
        
        # Import here to avoid circular dependency
        from .continuous_effects import ReduceCostBySleepingEffect
        return ReduceCostBySleepingEffect(source_card)
    
    @classmethod
    def _parse_gain_cc_when_sleeped(cls, parts: List[str], source_card: "Card") -> BaseEffect:
        """
        Parse a gain_cc_when_sleeped effect definition.
        
        Format: "gain_cc_when_sleeped:amount"
        - amount: integer CC to gain when sleeped
        
        Args:
            parts: Split effect definition parts
            source_card: The card providing this effect
            
        Returns:
            GainCCWhenSleepedEffect instance
            
        Raises:
            ValueError: If format is invalid
        """
        if len(parts) != 2:
            raise ValueError(
                f"gain_cc_when_sleeped effect requires 1 parameter: amount. "
                f"Got {len(parts) - 1} parameters: {':'.join(parts)}"
            )
        
        # Parse amount
        try:
            amount = int(parts[1].strip())
        except ValueError:
            raise ValueError(
                f"Invalid amount '{parts[1]}' for gain_cc_when_sleeped. Must be an integer."
            )
        
        if amount < 1:
            raise ValueError(
                f"Invalid amount {amount} for gain_cc_when_sleeped. Must be at least 1."
            )
        
        # Import here to avoid circular dependency
        from .continuous_effects import GainCCWhenSleepedEffect
        return GainCCWhenSleepedEffect(source_card, amount)
    
    @classmethod
    def _parse_set_self_tussle_cost(cls, parts: List[str], source_card: "Card") -> BaseEffect:
        """
        Parse a set_self_tussle_cost effect definition.
        
        Format: "set_self_tussle_cost:cost" or "set_self_tussle_cost:cost:not_turn_1"
        - cost: integer tussle cost (e.g., 0 for Raggy)
        - not_turn_1: optional restriction preventing tussles on turn 1
        
        Args:
            parts: Split effect definition parts
            source_card: The card providing this effect
            
        Returns:
            SetSelfTussleCostEffect instance
            
        Raises:
            ValueError: If format is invalid
        """
        if len(parts) < 2 or len(parts) > 3:
            raise ValueError(
                f"set_self_tussle_cost effect requires 1-2 parameters: cost and optional restriction. "
                f"Got {len(parts) - 1} parameters: {':'.join(parts)}"
            )
        
        # Parse cost
        try:
            cost = int(parts[1].strip())
        except ValueError:
            raise ValueError(
                f"Invalid cost '{parts[1]}' for set_self_tussle_cost. Must be an integer."
            )
        
        if cost < 0:
            raise ValueError(
                f"Invalid cost {cost} for set_self_tussle_cost. Must be non-negative."
            )
        
        # Parse optional restriction
        not_turn_1 = False
        if len(parts) == 3:
            restriction = parts[2].strip().lower()
            if restriction == "not_turn_1":
                not_turn_1 = True
            else:
                raise ValueError(
                    f"Invalid restriction '{restriction}' for set_self_tussle_cost. "
                    f"Only 'not_turn_1' is supported."
                )
        
        # Import here to avoid circular dependency
        from .continuous_effects import SetSelfTussleCostEffect
        return SetSelfTussleCostEffect(source_card, cost, not_turn_1)


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
        
        First checks if the card has data-driven effect_definitions.
        If not, falls back to name-based registry for legacy cards.
        
        Args:
            card: The card to get effects for
            
        Returns:
            List of instantiated effect objects for this card
        """
        # Priority 1: Check for data-driven effect definitions
        if hasattr(card, 'effect_definitions') and card.effect_definitions:
            try:
                return EffectFactory.parse_effects(card.effect_definitions, card)
            except ValueError as e:
                # Log error but don't crash - fallback to name-based registry
                print(f"Warning: Failed to parse effects for {card.name}: {e}")
        
        # Priority 2: Fallback to name-based registry for legacy cards
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
