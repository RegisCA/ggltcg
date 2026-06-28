"""
Effect definition constants for GGLTCG.

This module provides constants for all effect definition strings used in cards.csv.
Using these constants instead of raw strings helps prevent typos and provides
IDE autocompletion.

Usage:
    from game_engine.effects_constants import EffectDefinitions

    # In card creation:
    card.effect_definitions = EffectDefinitions.OPPONENT_IMMUNITY

    # In tests:
    assert card.effect_definitions == EffectDefinitions.STAT_BOOST_STRENGTH_2
"""

from enum import Enum
from typing import Dict


class EffectDefinitions:
    """
    Constants for effect definition strings.

    These match the 'effects' column in cards.csv.
    Use format methods for parameterized effects.
    """

    # === Immunity Effects ===
    OPPONENT_IMMUNITY = "opponent_immunity"
    TEAM_OPPONENT_IMMUNITY = "team_opponent_immunity"

    # === Combat Effects ===
    AUTO_WIN_TUSSLE_ON_OWN_TURN = "auto_win_tussle_on_own_turn"
    CANNOT_TUSSLE = "cannot_tussle"
    DIRECT_ATTACK = "direct_attack"

    # === Tussle Cost Effects ===
    SET_TUSSLE_COST_1 = "set_tussle_cost:1"
    SET_SELF_TUSSLE_COST_0_NOT_TURN_1 = "set_self_tussle_cost:0:not_turn_1"

    # === Stat Boost Effects ===
    STAT_BOOST_STRENGTH_2 = "stat_boost:strength:2"
    STAT_BOOST_SPEED_2 = "stat_boost:speed:2"
    STAT_BOOST_ALL_1 = "stat_boost:all:1"
    TURN_STAT_BOOST_ALL_1 = "turn_stat_boost:all:1"

    # === Charge Gain Effects ===
    GAIN_CHARGE_1 = "gain_charge:1"
    GAIN_CHARGE_2_NOT_FIRST_TURN = "gain_charge:2:not_first_turn"
    GAIN_CHARGE_WHEN_BROKEN_1 = "gain_charge_when_broken:1"
    START_OF_TURN_GAIN_CHARGE_2 = "start_of_turn_gain_charge:2"
    ON_CARD_PLAYED_GAIN_CHARGE_1 = "on_card_played_gain_charge:1"

    # === Cost Modification Effects ===
    REDUCE_COST_BY_BROKEN = "reduce_cost_by_broken"
    ALTERNATIVE_COST_BREAK_CARD = "alternative_cost_break_card"
    OPPONENT_COST_INCREASE_1 = "opponent_cost_increase:1"

    # === Targeting Effects ===
    COPY_CARD = "copy_card"
    TAKE_CONTROL = "take_control"
    RETURN_ALL_TO_HAND = "return_all_to_hand"
    RETURN_TARGET_TO_HAND_1 = "return_target_to_hand:1"
    BREAK_ALL = "break_all"
    BREAK_TARGET_1 = "break_target:1"
    FIX_1 = "fix:1"
    FIX_2 = "fix:2"
    FIX_ACTIONS_1 = "fix:actions:1"

    # === Ability Effects ===
    REMOVE_STAMINA_ABILITY_1 = "remove_stamina_ability:1"

    # === Damage Effects ===
    DAMAGE_ALL_OPPONENT_CARDS_1 = "damage_all_opponent_cards:1"

    # === Compound Effects (multiple effects separated by ;) ===
    ARCHER_EFFECTS = "cannot_tussle;remove_stamina_ability:1"

    @staticmethod
    def stat_boost(stat: str, amount: int) -> str:
        """Generate a stat boost effect definition.

        Args:
            stat: 'speed', 'strength', 'stamina', or 'all'
            amount: Amount to boost

        Returns:
            Effect definition string like 'stat_boost:strength:2'
        """
        return f"stat_boost:{stat}:{amount}"

    @staticmethod
    def gain_charge(amount: int, restriction: str = None) -> str:
        """Generate a Charge gain effect definition.

        Args:
            amount: Amount of Charge to gain
            restriction: Optional restriction like 'not_first_turn'

        Returns:
            Effect definition string like 'gain_charge:2:not_first_turn'
        """
        if restriction:
            return f"gain_charge:{amount}:{restriction}"
        return f"gain_charge:{amount}"

    @staticmethod
    def opponent_cost_increase(amount: int) -> str:
        """Generate an opponent cost increase effect definition.

        Args:
            amount: Amount to increase opponent's costs

        Returns:
            Effect definition string like 'opponent_cost_increase:1'
        """
        return f"opponent_cost_increase:{amount}"

    @staticmethod
    def set_tussle_cost(cost: int) -> str:
        """Generate a set tussle cost effect definition.

        Args:
            cost: The tussle cost to set

        Returns:
            Effect definition string like 'set_tussle_cost:1'
        """
        return f"set_tussle_cost:{cost}"


# Mapping of card names to their effect definitions (for quick reference)
CARD_EFFECT_DEFINITIONS: Dict[str, str] = {
    "Beary": EffectDefinitions.OPPONENT_IMMUNITY,
    "Knight": EffectDefinitions.AUTO_WIN_TUSSLE_ON_OWN_TURN,
    "Wizard": EffectDefinitions.SET_TUSSLE_COST_1,
    "Archer": EffectDefinitions.ARCHER_EFFECTS,
    "Umbruh": EffectDefinitions.GAIN_CHARGE_WHEN_BROKEN_1,
    "Ka": EffectDefinitions.STAT_BOOST_STRENGTH_2,
    "Demideca": EffectDefinitions.STAT_BOOST_ALL_1,
    "Raggy": EffectDefinitions.SET_SELF_TUSSLE_COST_0_NOT_TURN_1,
    "Ballaber": EffectDefinitions.ALTERNATIVE_COST_BREAK_CARD,
    "Dream": EffectDefinitions.REDUCE_COST_BY_BROKEN,
    "Copy": EffectDefinitions.COPY_CARD,
    "Twist": EffectDefinitions.TAKE_CONTROL,
    "Rush": EffectDefinitions.GAIN_CHARGE_2_NOT_FIRST_TURN,
    "Toynado": EffectDefinitions.RETURN_ALL_TO_HAND,
    "Clean": EffectDefinitions.BREAK_ALL,
    "Wake": EffectDefinitions.FIX_1,
    "Sun": EffectDefinitions.FIX_2,
    "Surge": EffectDefinitions.GAIN_CHARGE_1,
    "Drum": EffectDefinitions.STAT_BOOST_SPEED_2,
    "Violin": EffectDefinitions.STAT_BOOST_STRENGTH_2,
    "Drop": EffectDefinitions.BREAK_TARGET_1,
    "Jumpscare": EffectDefinitions.RETURN_TARGET_TO_HAND_1,
    "Sock Sorcerer": EffectDefinitions.TEAM_OPPONENT_IMMUNITY,
    "VeryVeryAppleJuice": EffectDefinitions.TURN_STAT_BOOST_ALL_1,
    "Belchaletta": EffectDefinitions.START_OF_TURN_GAIN_CHARGE_2,
    "Hind Leg Kicker": EffectDefinitions.ON_CARD_PLAYED_GAIN_CHARGE_1,
    "Gibbers": EffectDefinitions.OPPONENT_COST_INCREASE_1,
    "That was fun": EffectDefinitions.FIX_ACTIONS_1,
    "Paper Plane": EffectDefinitions.DIRECT_ATTACK,
    "Monster": EffectDefinitions.DAMAGE_ALL_OPPONENT_CARDS_1,
}


def get_effect_definition(card_name: str) -> str:
    """
    Get the effect definition for a card by name.

    Args:
        card_name: Name of the card

    Returns:
        Effect definition string

    Raises:
        KeyError: If card not found
    """
    if card_name not in CARD_EFFECT_DEFINITIONS:
        raise KeyError(f"Card '{card_name}' not found in effect definitions")
    return CARD_EFFECT_DEFINITIONS[card_name]
