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
    
    # === Tussle Cost Effects ===
    SET_TUSSLE_COST_1 = "set_tussle_cost:1"
    SET_SELF_TUSSLE_COST_0_NOT_TURN_1 = "set_self_tussle_cost:0:not_turn_1"
    
    # === Stat Boost Effects ===
    STAT_BOOST_STRENGTH_2 = "stat_boost:strength:2"
    STAT_BOOST_SPEED_2 = "stat_boost:speed:2"
    STAT_BOOST_ALL_1 = "stat_boost:all:1"
    TURN_STAT_BOOST_ALL_1 = "turn_stat_boost:all:1"
    
    # === CC Gain Effects ===
    GAIN_CC_1 = "gain_cc:1"
    GAIN_CC_2_NOT_FIRST_TURN = "gain_cc:2:not_first_turn"
    GAIN_CC_WHEN_SLEEPED_1 = "gain_cc_when_sleeped:1"
    START_OF_TURN_GAIN_CC_2 = "start_of_turn_gain_cc:2"
    ON_CARD_PLAYED_GAIN_CC_1 = "on_card_played_gain_cc:1"
    
    # === Cost Modification Effects ===
    REDUCE_COST_BY_SLEEPING = "reduce_cost_by_sleeping"
    ALTERNATIVE_COST_SLEEP_CARD = "alternative_cost_sleep_card"
    OPPONENT_COST_INCREASE_1 = "opponent_cost_increase:1"
    
    # === Targeting Effects ===
    COPY_CARD = "copy_card"
    TAKE_CONTROL = "take_control"
    RETURN_ALL_TO_HAND = "return_all_to_hand"
    RETURN_TARGET_TO_HAND_1 = "return_target_to_hand:1"
    SLEEP_ALL = "sleep_all"
    SLEEP_TARGET_1 = "sleep_target:1"
    UNSLEEP_1 = "unsleep:1"
    UNSLEEP_2 = "unsleep:2"
    
    # === Ability Effects ===
    REMOVE_STAMINA_ABILITY_1 = "remove_stamina_ability:1"
    
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
    def gain_cc(amount: int, restriction: str = None) -> str:
        """Generate a CC gain effect definition.
        
        Args:
            amount: Amount of CC to gain
            restriction: Optional restriction like 'not_first_turn'
            
        Returns:
            Effect definition string like 'gain_cc:2:not_first_turn'
        """
        if restriction:
            return f"gain_cc:{amount}:{restriction}"
        return f"gain_cc:{amount}"
    
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
    "Umbruh": EffectDefinitions.GAIN_CC_WHEN_SLEEPED_1,
    "Ka": EffectDefinitions.STAT_BOOST_STRENGTH_2,
    "Demideca": EffectDefinitions.STAT_BOOST_ALL_1,
    "Raggy": EffectDefinitions.SET_SELF_TUSSLE_COST_0_NOT_TURN_1,
    "Ballaber": EffectDefinitions.ALTERNATIVE_COST_SLEEP_CARD,
    "Dream": EffectDefinitions.REDUCE_COST_BY_SLEEPING,
    "Copy": EffectDefinitions.COPY_CARD,
    "Twist": EffectDefinitions.TAKE_CONTROL,
    "Rush": EffectDefinitions.GAIN_CC_2_NOT_FIRST_TURN,
    "Toynado": EffectDefinitions.RETURN_ALL_TO_HAND,
    "Clean": EffectDefinitions.SLEEP_ALL,
    "Wake": EffectDefinitions.UNSLEEP_1,
    "Sun": EffectDefinitions.UNSLEEP_2,
    "Surge": EffectDefinitions.GAIN_CC_1,
    "Drum": EffectDefinitions.STAT_BOOST_SPEED_2,
    "Violin": EffectDefinitions.STAT_BOOST_STRENGTH_2,
    "Drop": EffectDefinitions.SLEEP_TARGET_1,
    "Jumpscare": EffectDefinitions.RETURN_TARGET_TO_HAND_1,
    "Sock Sorcerer": EffectDefinitions.TEAM_OPPONENT_IMMUNITY,
    "VeryVeryAppleJuice": EffectDefinitions.TURN_STAT_BOOST_ALL_1,
    "Belchaletta": EffectDefinitions.START_OF_TURN_GAIN_CC_2,
    "Hind Leg Kicker": EffectDefinitions.ON_CARD_PLAYED_GAIN_CC_1,
    "Gibbers": EffectDefinitions.OPPONENT_COST_INCREASE_1,
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
