"""
Effect registry for mapping card names to their effect classes.

This module provides a central registry for looking up which effects
belong to each card in the game.
"""

from typing import List, TYPE_CHECKING
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
    - "stat_boost:strength:2;fix" -> [StatBoostEffect(...), FixEffect(...)]
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
            elif effect_type == "gain_charge":
                effect = cls._parse_gain_charge(parts, source_card)
                effects.append(effect)
            elif effect_type == "fix":
                effect = cls._parse_fix(parts, source_card)
                effects.append(effect)
            elif effect_type == "break_all":
                effect = cls._parse_break_all(parts, source_card)
                effects.append(effect)
            elif effect_type == "set_tussle_cost":
                effect = cls._parse_set_tussle_cost(parts, source_card)
                effects.append(effect)
            elif effect_type == "reduce_cost_by_broken":
                effect = cls._parse_reduce_cost_by_broken(parts, source_card)
                effects.append(effect)
            elif effect_type == "self_cost_increase_by_broken":
                effect = cls._parse_self_cost_increase_by_broken(parts, source_card)
                effects.append(effect)
            elif effect_type == "gain_charge_when_broken":
                effect = cls._parse_gain_charge_when_broken(parts, source_card)
                effects.append(effect)
            elif effect_type == "set_self_tussle_cost":
                effect = cls._parse_set_self_tussle_cost(parts, source_card)
                effects.append(effect)
            elif effect_type == "opponent_immunity":
                effect = cls._parse_opponent_immunity(parts, source_card)
                effects.append(effect)
            elif effect_type == "auto_win_tussle_on_own_turn":
                effect = cls._parse_auto_win_tussle(parts, source_card)
                effects.append(effect)
            elif effect_type == "return_all_to_hand":
                effect = cls._parse_return_all_to_hand(parts, source_card)
                effects.append(effect)
            elif effect_type == "take_control":
                effect = cls._parse_take_control(parts, source_card)
                effects.append(effect)
            elif effect_type == "copy_card":
                effect = cls._parse_copy_card(parts, source_card)
                effects.append(effect)
            elif effect_type == "alternative_cost_break_card":
                effect = cls._parse_alternative_cost_break_card(parts, source_card)
                effects.append(effect)
            elif effect_type == "cannot_tussle":
                effect = cls._parse_cannot_tussle(parts, source_card)
                effects.append(effect)
            elif effect_type == "direct_attack":
                effect = cls._parse_direct_attack(parts, source_card)
                effects.append(effect)
            elif effect_type == "remove_stamina_ability":
                effect = cls._parse_remove_stamina_ability(parts, source_card)
                effects.append(effect)
            elif effect_type == "break_target":
                effect = cls._parse_break_target(parts, source_card)
                effects.append(effect)
            elif effect_type == "return_target_to_hand":
                effect = cls._parse_return_target_to_hand(parts, source_card)
                effects.append(effect)
            elif effect_type == "team_opponent_immunity":
                effect = cls._parse_team_opponent_immunity(parts, source_card)
                effects.append(effect)
            elif effect_type == "turn_stat_boost":
                effect = cls._parse_turn_stat_boost(parts, source_card)
                effects.append(effect)
            elif effect_type == "start_of_turn_gain_charge":
                effect = cls._parse_start_of_turn_gain_charge(parts, source_card)
                effects.append(effect)
            elif effect_type == "on_card_played_gain_charge":
                effect = cls._parse_on_card_played_gain_charge(parts, source_card)
                effects.append(effect)
            elif effect_type == "opponent_cost_increase":
                effect = cls._parse_opponent_cost_increase(parts, source_card)
                effects.append(effect)
            elif effect_type == "damage_all_opponent_cards":
                effect = cls._parse_damage_all_opponent_cards(parts, source_card)
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
    def _parse_gain_charge(cls, parts: List[str], source_card: "Card") -> BaseEffect:
        """
        Parse a gain_charge effect definition.
        
        Format: "gain_charge:amount" or "gain_charge:amount:not_first_turn"
        - amount: integer Charge to gain
        - not_first_turn: optional restriction
        
        Args:
            parts: Split effect definition parts
            source_card: The card providing this effect
            
        Returns:
            GainChargeEffect instance
            
        Raises:
            ValueError: If format is invalid
        """
        if len(parts) < 2 or len(parts) > 3:
            raise ValueError(
                f"gain_charge effect requires 1-2 parameters: amount and optional restriction. "
                f"Got {len(parts) - 1} parameters: {':'.join(parts)}"
            )
        
        # Parse amount
        try:
            amount = int(parts[1].strip())
        except ValueError:
            raise ValueError(
                f"Invalid amount '{parts[1]}' for gain_charge. Must be an integer."
            )
        
        # Parse optional restriction
        not_first_turn = False
        if len(parts) == 3:
            restriction = parts[2].strip().lower()
            if restriction == "not_first_turn":
                not_first_turn = True
            else:
                raise ValueError(
                    f"Invalid restriction '{restriction}' for gain_charge. "
                    f"Only 'not_first_turn' is supported."
                )
        
        # Import here to avoid circular dependency
        from .action_effects import GainChargeEffect
        return GainChargeEffect(source_card, amount, not_first_turn)
    
    @classmethod
    def _parse_fix(cls, parts: List[str], source_card: "Card") -> BaseEffect:
        """
        Parse a fix effect definition.
        
        Formats:
        - "fix:count" - fix N cards (any type)
        - "fix:card_type:count" - fix N cards of specific type
        
        Args:
            parts: Split effect definition parts
            source_card: The card providing this effect
            
        Returns:
            FixEffect instance
            
        Raises:
            ValueError: If format is invalid
        """
        if len(parts) not in (2, 3):
            raise ValueError(
                f"fix effect requires 1-2 parameters: [card_type:]count. "
                f"Got {len(parts) - 1} parameters: {':'.join(parts)}"
            )
        
        card_type_filter = None
        count_str = None
        
        if len(parts) == 2:
            # Format: fix:count
            count_str = parts[1].strip()
        else:
            # Format: fix:card_type:count
            card_type_filter = parts[1].strip().lower()
            count_str = parts[2].strip()
            
            if card_type_filter not in ("actions", "toys"):
                raise ValueError(
                    f"Invalid card_type_filter '{card_type_filter}' for fix. "
                    f"Must be 'actions' or 'toys'."
                )
        
        # Parse count
        try:
            count = int(count_str)
        except ValueError:
            raise ValueError(
                f"Invalid count '{count_str}' for fix. Must be an integer."
            )
        
        if count < 1:
            raise ValueError(
                f"Invalid count '{count}' for fix. Must be at least 1."
            )
        
        # Import here to avoid circular dependency
        from .action_effects import FixEffect
        return FixEffect(source_card, count, card_type_filter)
    
    @classmethod
    def _parse_break_all(cls, parts: List[str], source_card: "Card") -> BaseEffect:
        """
        Parse a break_all effect definition.
        
        Format: "break_all" (no parameters)
        
        Args:
            parts: Split effect definition parts
            source_card: The card providing this effect
            
        Returns:
            BreakAllEffect instance
            
        Raises:
            ValueError: If format is invalid
        """
        if len(parts) != 1:
            raise ValueError(
                f"break_all effect takes no parameters. "
                f"Got {len(parts) - 1} parameters: {':'.join(parts)}"
            )
        
        # Import here to avoid circular dependency
        from .action_effects import BreakAllEffect
        return BreakAllEffect(source_card)
    
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
    def _parse_reduce_cost_by_broken(cls, parts: List[str], source_card: "Card") -> BaseEffect:
        """
        Parse a reduce_cost_by_broken effect definition.
        
        Format: "reduce_cost_by_broken"
        No parameters - reduces cost by 1 per broken card.
        
        Args:
            parts: Split effect definition parts
            source_card: The card providing this effect
            
        Returns:
            ReduceCostByBrokenEffect instance
            
        Raises:
            ValueError: If format is invalid
        """
        if len(parts) != 1:
            raise ValueError(
                f"reduce_cost_by_broken effect takes no parameters. "
                f"Got {len(parts) - 1} parameters: {':'.join(parts)}"
            )
        
        # Import here to avoid circular dependency
        from .continuous_effects import ReduceCostByBrokenEffect
        return ReduceCostByBrokenEffect(source_card)

    @classmethod
    def _parse_self_cost_increase_by_broken(cls, parts: List[str], source_card: "Card") -> BaseEffect:
        """
        Parse a self_cost_increase_by_broken effect definition.

        Format: "self_cost_increase_by_broken"
        No parameters - increases cost by 1 per broken card.

        Args:
            parts: Split effect definition parts
            source_card: The card providing this effect

        Returns:
            SelfCostIncreaseByBrokenEffect instance

        Raises:
            ValueError: If format is invalid
        """
        if len(parts) != 1:
            raise ValueError(
                f"self_cost_increase_by_broken effect takes no parameters. "
                f"Got {len(parts) - 1} parameters: {':'.join(parts)}"
            )

        # Import here to avoid circular dependency
        from .continuous_effects import SelfCostIncreaseByBrokenEffect
        return SelfCostIncreaseByBrokenEffect(source_card)

    @classmethod
    def _parse_gain_charge_when_broken(cls, parts: List[str], source_card: "Card") -> BaseEffect:
        """
        Parse a gain_charge_when_broken effect definition.
        
        Format: "gain_charge_when_broken:amount"
        - amount: integer Charge to gain when broken
        
        Args:
            parts: Split effect definition parts
            source_card: The card providing this effect
            
        Returns:
            GainChargeWhenBrokenEffect instance
            
        Raises:
            ValueError: If format is invalid
        """
        if len(parts) != 2:
            raise ValueError(
                f"gain_charge_when_broken effect requires 1 parameter: amount. "
                f"Got {len(parts) - 1} parameters: {':'.join(parts)}"
            )
        
        # Parse amount
        try:
            amount = int(parts[1].strip())
        except ValueError:
            raise ValueError(
                f"Invalid amount '{parts[1]}' for gain_charge_when_broken. Must be an integer."
            )
        
        if amount < 1:
            raise ValueError(
                f"Invalid amount {amount} for gain_charge_when_broken. Must be at least 1."
            )
        
        # Import here to avoid circular dependency
        from .continuous_effects import GainChargeWhenBrokenEffect
        return GainChargeWhenBrokenEffect(source_card, amount)
    
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
    
    @classmethod
    def _parse_opponent_immunity(cls, parts: List[str], source_card: "Card") -> BaseEffect:
        """
        Parse an opponent_immunity effect definition.
        
        Format: "opponent_immunity" (no parameters)
        
        Provides immunity from opponent's card effects.
        Tussle damage is not an effect and can still harm the card.
        
        Args:
            parts: Split effect definition parts
            source_card: The card providing this effect
            
        Returns:
            OpponentImmunityEffect instance
            
        Raises:
            ValueError: If format is invalid
        """
        if len(parts) != 1:
            raise ValueError(
                f"opponent_immunity effect takes no parameters. "
                f"Got {len(parts) - 1} parameters: {':'.join(parts)}"
            )
        
        # Import here to avoid circular dependency
        from .continuous_effects import OpponentImmunityEffect
        return OpponentImmunityEffect(source_card)
    
    @classmethod
    def _parse_auto_win_tussle(cls, parts: List[str], source_card: "Card") -> BaseEffect:
        """
        Parse an auto_win_tussle_on_own_turn effect definition.
        
        Format: "auto_win_tussle_on_own_turn" (no parameters)
        
        On the controller's turn, this card automatically wins all tussles.
        The opponent is broken without striking back.
        
        Args:
            parts: Split effect definition parts
            source_card: The card providing this effect
            
        Returns:
            KnightWinConditionEffect instance
            
        Raises:
            ValueError: If format is invalid
        """
        if len(parts) != 1:
            raise ValueError(
                f"auto_win_tussle_on_own_turn effect takes no parameters. "
                f"Got {len(parts) - 1} parameters: {':'.join(parts)}"
            )
        
        # Import here to avoid circular dependency
        from .continuous_effects import KnightWinConditionEffect
        return KnightWinConditionEffect(source_card)
    
    @classmethod
    def _parse_return_all_to_hand(cls, parts: List[str], source_card: "Card") -> BaseEffect:
        """
        Parse a return_all_to_hand effect definition.
        
        Format: "return_all_to_hand" (no parameters)
        
        Returns all cards in play to their owners' hands.
        Respects protection effects.
        
        Args:
            parts: Split effect definition parts
            source_card: The card providing this effect
            
        Returns:
            ToynadoEffect instance
            
        Raises:
            ValueError: If format is invalid
        """
        if len(parts) != 1:
            raise ValueError(
                f"return_all_to_hand effect takes no parameters. "
                f"Got {len(parts) - 1} parameters: {':'.join(parts)}"
            )
        
        # Import here to avoid circular dependency
        from .action_effects import ToynadoEffect
        return ToynadoEffect(source_card)
    
    @classmethod
    def _parse_take_control(cls, parts: List[str], source_card: "Card") -> BaseEffect:
        """
        Parse a take_control effect definition.
        
        Format: "take_control" (no parameters)
        
        Takes control of an opponent's card in play.
        Requires target selection.
        Respects protection effects.
        
        Args:
            parts: Split effect definition parts
            source_card: The card providing this effect
            
        Returns:
            TwistEffect instance
            
        Raises:
            ValueError: If format is invalid
        """
        if len(parts) != 1:
            raise ValueError(
                f"take_control effect takes no parameters. "
                f"Got {len(parts) - 1} parameters: {':'.join(parts)}"
            )
        
        # Import here to avoid circular dependency
        from .action_effects import TwistEffect
        return TwistEffect(source_card)
    
    @classmethod
    def _parse_copy_card(cls, parts: List[str], source_card: "Card") -> BaseEffect:
        """
        Parse a copy_card effect definition.
        
        Format: "copy_card" (no parameters)
        
        Transforms this card into a copy of a target card in play.
        Requires target selection.
        Copies stats, effects, and appearance.
        
        Args:
            parts: Split effect definition parts
            source_card: The card providing this effect
            
        Returns:
            CopyEffect instance
            
        Raises:
            ValueError: If format is invalid
        """
        if len(parts) != 1:
            raise ValueError(
                f"copy_card effect takes no parameters. "
                f"Got {len(parts) - 1} parameters: {':'.join(parts)}"
            )
        
        # Import here to avoid circular dependency
        from .action_effects import CopyEffect
        return CopyEffect(source_card)
    
    @classmethod
    def _parse_alternative_cost_break_card(cls, parts: List[str], source_card: "Card") -> BaseEffect:
        """
        Parse an alternative_cost_break_card effect definition.
        
        Format: "alternative_cost_break_card" (no parameters)
        
        Allows playing this card for free by breaking one of your cards in play.
        Provides an alternative to paying the normal Charge cost.
        
        Args:
            parts: Split effect definition parts
            source_card: The card providing this effect
            
        Returns:
            BallaberCostEffect instance
            
        Raises:
            ValueError: If format is invalid
        """
        if len(parts) != 1:
            raise ValueError(
                f"alternative_cost_break_card effect takes no parameters. "
                f"Got {len(parts) - 1} parameters: {':'.join(parts)}"
            )
        
        # Import here to avoid circular dependency
        from .continuous_effects import BallaberCostEffect
        return BallaberCostEffect(source_card)
    
    @classmethod
    def _parse_cannot_tussle(cls, parts: List[str], source_card: "Card") -> BaseEffect:
        """
        Parse a cannot_tussle effect definition.
        
        Format: "cannot_tussle" (no parameters)
        
        Prevents this card from being declared as an attacker in tussles.
        
        Args:
            parts: Split effect definition parts
            source_card: The card providing this effect
            
        Returns:
            ArcherRestrictionEffect instance
            
        Raises:
            ValueError: If format is invalid
        """
        if len(parts) != 1:
            raise ValueError(
                f"cannot_tussle effect takes no parameters. "
                f"Got {len(parts) - 1} parameters: {':'.join(parts)}"
            )
        
        # Import here to avoid circular dependency
        from .continuous_effects import ArcherRestrictionEffect
        return ArcherRestrictionEffect(source_card)
    
    @classmethod
    def _parse_direct_attack(cls, parts: List[str], source_card: "Card") -> BaseEffect:
        """
        Parse a direct_attack effect definition.
        
        Format: "direct_attack" (no parameters)
        
        Allows this card to perform direct attacks against the opponent's hand
        even when the opponent has cards in play.
        
        Args:
            parts: Split effect definition parts
            source_card: The card providing this effect
            
        Returns:
            DirectAttackEffect instance
            
        Raises:
            ValueError: If format is invalid
        """
        if len(parts) != 1:
            raise ValueError(
                f"direct_attack effect takes no parameters. "
                f"Got {len(parts) - 1} parameters: {':'.join(parts)}"
            )
        
        # Import here to avoid circular dependency
        from .continuous_effects import DirectAttackEffect
        return DirectAttackEffect(source_card)
    
    @classmethod
    def _parse_remove_stamina_ability(cls, parts: List[str], source_card: "Card") -> BaseEffect:
        """
        Parse a remove_stamina_ability effect definition.
        
        Format: "remove_stamina_ability:charge_cost" or "remove_stamina_ability:charge_cost:amount"
        - charge_cost: Charge cost per activation (typically 1)
        - amount: Amount of stamina to remove per activation (defaults to 1)
        
        Activated ability: spend Charge to remove stamina from any card in play.
        
        Args:
            parts: Split effect definition parts
            source_card: The card providing this effect
            
        Returns:
            ArcherActivatedAbility instance
            
        Raises:
            ValueError: If format is invalid
        """
        if len(parts) < 2 or len(parts) > 3:
            raise ValueError(
                f"remove_stamina_ability effect requires 1-2 parameters: charge_cost and optional amount. "
                f"Got {len(parts) - 1} parameters: {':'.join(parts)}"
            )
        
        # Parse charge_cost
        try:
            charge_cost = int(parts[1].strip())
        except ValueError:
            raise ValueError(
                f"Invalid charge_cost '{parts[1]}' for remove_stamina_ability. Must be an integer."
            )
        
        if charge_cost < 0:
            raise ValueError(
                f"Invalid charge_cost {charge_cost} for remove_stamina_ability. Must be non-negative."
            )
        
        # Parse optional amount (default 1)
        amount = 1
        if len(parts) == 3:
            try:
                amount = int(parts[2].strip())
            except ValueError:
                raise ValueError(
                    f"Invalid amount '{parts[2]}' for remove_stamina_ability. Must be an integer."
                )
            
            if amount < 1:
                raise ValueError(
                    f"Invalid amount {amount} for remove_stamina_ability. Must be at least 1."
                )
        
        # Import here to avoid circular dependency
        from .action_effects import ArcherActivatedAbility
        # Note: ArcherActivatedAbility currently only uses charge_cost in __init__
        # The amount parameter would need to be added if we want variable damage
        return ArcherActivatedAbility(source_card)

    @classmethod
    def _parse_damage_all_opponent_cards(cls, parts: List[str], source_card: "Card") -> BaseEffect:
        """
        Parse a damage_all_opponent_cards effect definition.
        
        Format: "damage_all_opponent_cards:amount"
        - amount: Damage to deal to each opponent card (typically 1)
        
        One-time effect when played: deals damage to all opponent's cards in play.
        Cards that reach 0 stamina are broken.
        
        Args:
            parts: Split effect definition parts
            source_card: The card providing this effect
            
        Returns:
            DamageAllOpponentCardsEffect instance
            
        Raises:
            ValueError: If format is invalid
        """
        if len(parts) != 2:
            raise ValueError(
                f"damage_all_opponent_cards effect requires exactly 1 parameter: amount. "
                f"Got {len(parts) - 1} parameters: {':'.join(parts)}"
            )
        
        try:
            damage = int(parts[1].strip())
        except ValueError:
            raise ValueError(
                f"Invalid damage '{parts[1]}' for damage_all_opponent_cards. Must be an integer."
            )
        
        if damage < 1:
            raise ValueError(
                f"Invalid damage {damage} for damage_all_opponent_cards. Must be at least 1."
            )
        
        # Import here to avoid circular dependency
        from .action_effects import DamageAllOpponentCardsEffect
        return DamageAllOpponentCardsEffect(source_card, damage)

    @classmethod
    def _parse_break_target(cls, parts: List[str], source_card: "Card") -> BaseEffect:
        """
        Parse a break_target effect definition.
        
        Format: "break_target:count"
        - count: Number of targets to break (typically 1)
        
        Targeted action: Break a card in play.
        
        Args:
            parts: Split effect definition parts
            source_card: The card providing this effect
            
        Returns:
            BreakTargetEffect instance
            
        Raises:
            ValueError: If format is invalid
        """
        if len(parts) != 2:
            raise ValueError(
                f"break_target effect requires exactly 1 parameter: count. "
                f"Got {len(parts) - 1} parameters: {':'.join(parts)}"
            )
        
        try:
            count = int(parts[1].strip())
        except ValueError:
            raise ValueError(
                f"Invalid count '{parts[1]}' for break_target. Must be an integer."
            )
        
        if count < 1:
            raise ValueError(
                f"Invalid count {count} for break_target. Must be at least 1."
            )
        
        from .action_effects import BreakTargetEffect
        return BreakTargetEffect(source_card, count=count)

    @classmethod
    def _parse_return_target_to_hand(cls, parts: List[str], source_card: "Card") -> BaseEffect:
        """
        Parse a return_target_to_hand effect definition.
        
        Format: "return_target_to_hand:count"
        - count: Number of targets to return to hand (typically 1)
        
        Targeted action: Return a card in play to its owner's hand.
        
        Args:
            parts: Split effect definition parts
            source_card: The card providing this effect
            
        Returns:
            ReturnTargetToHandEffect instance
            
        Raises:
            ValueError: If format is invalid
        """
        if len(parts) != 2:
            raise ValueError(
                f"return_target_to_hand effect requires exactly 1 parameter: count. "
                f"Got {len(parts) - 1} parameters: {':'.join(parts)}"
            )
        
        try:
            count = int(parts[1].strip())
        except ValueError:
            raise ValueError(
                f"Invalid count '{parts[1]}' for return_target_to_hand. Must be an integer."
            )
        
        if count < 1:
            raise ValueError(
                f"Invalid count {count} for return_target_to_hand. Must be at least 1."
            )
        
        from .action_effects import ReturnTargetToHandEffect
        return ReturnTargetToHandEffect(source_card, count=count)

    @classmethod
    def _parse_team_opponent_immunity(cls, parts: List[str], source_card: "Card") -> BaseEffect:
        """
        Parse a team_opponent_immunity effect definition.
        
        Format: "team_opponent_immunity" (no parameters)
        
        Sock Sorcerer: All cards controlled by this card's controller
        are immune to effects from opponent-controlled cards.
        
        Args:
            parts: Split effect definition parts
            source_card: The card providing this effect
            
        Returns:
            TeamOpponentImmunityEffect instance
            
        Raises:
            ValueError: If format is invalid
        """
        if len(parts) != 1:
            raise ValueError(
                f"team_opponent_immunity effect takes no parameters. "
                f"Got {len(parts) - 1} parameters: {':'.join(parts)}"
            )
        
        from .continuous_effects import TeamOpponentImmunityEffect
        return TeamOpponentImmunityEffect(source_card)

    @classmethod
    def _parse_turn_stat_boost(cls, parts: List[str], source_card: "Card") -> BaseEffect:
        """
        Parse a turn_stat_boost effect definition.
        
        Format: "turn_stat_boost:stat_name:amount"
        - stat_name: "speed", "strength", "stamina", or "all"
        - amount: Integer amount to boost
        
        VeryVeryAppleJuice: Boost all stats by 1 for the current turn only.
        
        Args:
            parts: Split effect definition parts
            source_card: The card providing this effect
            
        Returns:
            TurnStatBoostEffect instance
            
        Raises:
            ValueError: If format is invalid
        """
        if len(parts) != 3:
            raise ValueError(
                f"turn_stat_boost effect requires exactly 2 parameters: stat_name and amount. "
                f"Got {len(parts) - 1} parameters: {':'.join(parts)}"
            )
        
        stat_name = parts[1].strip().lower()
        valid_stats = ("speed", "strength", "stamina", "all")
        if stat_name not in valid_stats:
            raise ValueError(
                f"Invalid stat name '{stat_name}' for turn_stat_boost. "
                f"Must be one of: {valid_stats}"
            )
        
        try:
            amount = int(parts[2].strip())
        except ValueError:
            raise ValueError(
                f"Invalid amount '{parts[2]}' for turn_stat_boost. Must be an integer."
            )
        
        from .action_effects import TurnStatBoostEffect
        return TurnStatBoostEffect(source_card, stat_name=stat_name, amount=amount)

    @classmethod
    def _parse_start_of_turn_gain_charge(cls, parts: List[str], source_card: "Card") -> BaseEffect:
        """
        Parse a start_of_turn_gain_charge effect definition.
        
        Format: "start_of_turn_gain_charge:amount"
        - amount: Integer amount of Charge to gain
        
        Belchaletta: Gain 2 Charge at the start of your turn.
        
        Args:
            parts: Split effect definition parts
            source_card: The card providing this effect
            
        Returns:
            StartOfTurnGainChargeEffect instance
            
        Raises:
            ValueError: If format is invalid
        """
        if len(parts) != 2:
            raise ValueError(
                f"start_of_turn_gain_charge effect requires exactly 1 parameter: amount. "
                f"Got {len(parts) - 1} parameters: {':'.join(parts)}"
            )
        
        try:
            amount = int(parts[1].strip())
        except ValueError:
            raise ValueError(
                f"Invalid amount '{parts[1]}' for start_of_turn_gain_charge. Must be an integer."
            )
        
        if amount < 1:
            raise ValueError(
                f"Invalid amount {amount} for start_of_turn_gain_charge. Must be at least 1."
            )
        
        from .continuous_effects import StartOfTurnGainChargeEffect
        return StartOfTurnGainChargeEffect(source_card, amount=amount)

    @classmethod
    def _parse_on_card_played_gain_charge(cls, parts: List[str], source_card: "Card") -> BaseEffect:
        """
        Parse an on_card_played_gain_charge effect definition.
        
        Format: "on_card_played_gain_charge:amount"
        - amount: Integer amount of Charge to gain
        
        Hind Leg Kicker: When you play a card (not this one), gain 1 Charge.
        
        Args:
            parts: Split effect definition parts
            source_card: The card providing this effect
            
        Returns:
            OnCardPlayedGainChargeEffect instance
            
        Raises:
            ValueError: If format is invalid
        """
        if len(parts) != 2:
            raise ValueError(
                f"on_card_played_gain_charge effect requires exactly 1 parameter: amount. "
                f"Got {len(parts) - 1} parameters: {':'.join(parts)}"
            )
        
        try:
            amount = int(parts[1].strip())
        except ValueError:
            raise ValueError(
                f"Invalid amount '{parts[1]}' for on_card_played_gain_charge. Must be an integer."
            )
        
        if amount < 1:
            raise ValueError(
                f"Invalid amount {amount} for on_card_played_gain_charge. Must be at least 1."
            )
        
        from .continuous_effects import OnCardPlayedGainChargeEffect
        return OnCardPlayedGainChargeEffect(source_card, amount=amount)

    @classmethod
    def _parse_opponent_cost_increase(cls, parts: List[str], source_card: "Card") -> BaseEffect:
        """
        Parse an opponent_cost_increase effect definition.
        
        Format: "opponent_cost_increase:amount"
        - amount: integer increase to apply to opponent's card costs
        
        Args:
            parts: Split effect definition parts
            source_card: The card providing this effect
            
        Returns:
            OpponentCostIncreaseEffect instance
            
        Raises:
            ValueError: If format is invalid
        """
        if len(parts) != 2:
            raise ValueError(
                f"opponent_cost_increase effect requires exactly 1 parameter: amount. "
                f"Got {len(parts) - 1} parameters: {':'.join(parts)}"
            )
        
        try:
            amount = int(parts[1].strip())
        except ValueError:
            raise ValueError(
                f"Invalid amount '{parts[1]}' for opponent_cost_increase. Must be an integer."
            )
        
        if amount < 1:
            raise ValueError(
                f"Invalid amount {amount} for opponent_cost_increase. Must be at least 1."
            )
        
        from .continuous_effects import OpponentCostIncreaseEffect
        return OpponentCostIncreaseEffect(source_card, amount=amount)


class EffectRegistry:
    """
    Central registry for card effects.

    Effects are instantiated when needed and attached to cards.
    """

    @classmethod
    def get_effects(cls, card: "Card") -> List[BaseEffect]:
        """
        Get all effects for a card.

        First checks if the card has pre-parsed copied effects (for Copy card).
        Otherwise parses the card's data-driven effect_definitions.

        Args:
            card: The card to get effects for

        Returns:
            List of instantiated effect objects for this card
        """
        # Priority 0: Check for pre-parsed copied effects (Copy card transformation)
        if hasattr(card, '_copied_effects') and card._copied_effects:
            return card._copied_effects

        # Priority 1: Check for data-driven effect definitions
        if hasattr(card, 'effect_definitions') and card.effect_definitions:
            try:
                return EffectFactory.parse_effects(card.effect_definitions, card)
            except ValueError as e:
                print(f"Warning: Failed to parse effects for {card.name}: {e}")

        return []
