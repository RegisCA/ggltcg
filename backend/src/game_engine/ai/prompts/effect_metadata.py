"""
Effect Metadata for AI Planning

This module provides metadata about effect types to help the AI understand
how to use cards with different effects. The metadata is aligned with the
EffectFactory implementation and includes:
- Effect classification (continuous/triggered/activated/passive)
- Targeting requirements
- Strategic implications
- Which action_type to use

This is the single source of truth for effect behavior in AI planning.
"""

from typing import Dict, Optional, List


class EffectMetadata:
    """Metadata about a single effect type."""
    
    def __init__(
        self,
        effect_type: str,
        classification: str,  # "continuous", "triggered", "activated", "passive"
        action_type: Optional[str],  # Which action_type to use, if any
        requires_targets: bool,
        target_description: Optional[str],  # Description of valid targets
        strategic_note: str,  # How to use this effect strategically
    ):
        self.effect_type = effect_type
        self.classification = classification
        self.action_type = action_type
        self.requires_targets = requires_targets
        self.target_description = target_description
        self.strategic_note = strategic_note
    
    def to_guidance_text(self) -> str:
        """Generate guidance text for the AI prompt."""
        parts = [f"**{self.effect_type}** ({self.classification})"]
        
        if self.action_type:
            parts.append(f"- Action: Use `action_type: {self.action_type}`")
        
        if self.requires_targets:
            parts.append(f"- Targeting: {self.target_description}")
        
        parts.append(f"- Strategy: {self.strategic_note}")
        
        return "\n".join(parts)


# Effect Metadata Registry
# Maps effect type patterns to their metadata
EFFECT_METADATA_REGISTRY: Dict[str, EffectMetadata] = {
    # === Stat Boosts (Continuous) ===
    "stat_boost:strength": EffectMetadata(
        effect_type="stat_boost:strength:N",
        classification="continuous",
        action_type=None,  # Automatic when in play
        requires_targets=False,
        target_description=None,
        strategic_note="Permanent strength boost to your Toys while this card is in play. Stacks with other stat boosts.",
    ),
    "stat_boost:speed": EffectMetadata(
        effect_type="stat_boost:speed:N",
        classification="continuous",
        action_type=None,
        requires_targets=False,
        target_description=None,
        strategic_note="Permanent speed boost to your Toys. Helps win tussles and affects attack priority.",
    ),
    "stat_boost:stamina": EffectMetadata(
        effect_type="stat_boost:stamina:N",
        classification="continuous",
        action_type=None,
        requires_targets=False,
        target_description=None,
        strategic_note="Permanent stamina boost to your Toys. Makes them harder to break via tussles.",
    ),
    "stat_boost:all": EffectMetadata(
        effect_type="stat_boost:all:N",
        classification="continuous",
        action_type=None,
        requires_targets=False,
        target_description=None,
        strategic_note="Boosts all stats for your Toys. Powerful force multiplier.",
    ),
    
    # === Temporary Boosts ===
    "turn_stat_boost:all": EffectMetadata(
        effect_type="turn_stat_boost:all:N",
        classification="temporary",
        action_type=None,  # Automatic when played
        requires_targets=False,
        target_description=None,
        strategic_note="Temporary boost this turn only. Play before tussles for maximum value.",
    ),
    
    # === Charge Effects ===
    "gain_charge": EffectMetadata(
        effect_type="gain_charge:N",
        classification="passive",
        action_type=None,  # Automatic when played
        requires_targets=False,
        target_description=None,
        strategic_note="Charge refund on play. Effectively reduces the card's cost.",
    ),
    "gain_charge:not_first_turn": EffectMetadata(
        effect_type="gain_charge:N:not_first_turn",
        classification="passive",
        action_type=None,
        requires_targets=False,
        target_description=None,
        strategic_note="Charge refund, but cannot play on turn 1. Plan accordingly.",
    ),
    "start_of_turn_gain_charge": EffectMetadata(
        effect_type="start_of_turn_gain_charge:N",
        classification="triggered",
        action_type=None,  # Automatic at start of turn
        requires_targets=False,
        target_description=None,
        strategic_note="Charge engine. Generates Charge each turn while in play. High priority to protect.",
    ),
    "on_card_played_gain_charge": EffectMetadata(
        effect_type="on_card_played_gain_charge:N",
        classification="triggered",
        action_type=None,  # Automatic when you play cards
        requires_targets=False,
        target_description=None,
        strategic_note="Charge engine that rewards playing multiple cards. Combos well with low-cost cards.",
    ),
    "gain_charge_when_broken": EffectMetadata(
        effect_type="gain_charge_when_broken:N",
        classification="triggered",
        action_type=None,  # Automatic when broken
        requires_targets=False,
        target_description=None,
        strategic_note="Charge refund when removed. Can sacrifice strategically.",
    ),
    
    # === Targeting Effects ===
    "break_target": EffectMetadata(
        effect_type="break_target:N",
        classification="activated",
        action_type="activate_ability",
        requires_targets=True,
        target_description="Target N opponent cards in play (usually Toys)",
        strategic_note="Precision removal. Use to eliminate threats or clear blockers. Targets must be valid.",
    ),
    "remove_stamina_ability": EffectMetadata(
        effect_type="remove_stamina_ability:N",
        classification="activated",
        action_type="activate_ability",
        requires_targets=True,
        target_description="Target any card in play, remove N stamina",
        strategic_note="Chip damage ability. Repeatable. Reduce stamina to 0 to auto-break target.",
    ),
    "return_target_to_hand": EffectMetadata(
        effect_type="return_target_to_hand:N",
        classification="activated",
        action_type="activate_ability",
        requires_targets=True,
        target_description="Target N cards in play (any player)",
        strategic_note="Tempo disruption. Removes threats without breaking. Can target your own cards.",
    ),
    "fix": EffectMetadata(
        effect_type="fix:N",
        classification="activated",
        action_type="activate_ability",
        requires_targets=True,
        target_description="Target N cards in YOUR break zone",
        strategic_note="Card advantage. Recover broken cards. Check for type restrictions (toys/actions).",
    ),
    "fix:actions": EffectMetadata(
        effect_type="fix:actions:N",
        classification="activated",
        action_type="activate_ability",
        requires_targets=True,
        target_description="Target N Action cards in your break zone",
        strategic_note="Recover Action cards from the break zone. Enables action recursion.",
    ),
    "fix:toys": EffectMetadata(
        effect_type="fix:toys:N",
        classification="activated",
        action_type="activate_ability",
        requires_targets=True,
        target_description="Target N Toy cards in your break zone",
        strategic_note="Recover Toy cards from the break zone. Rebuild board presence.",
    ),
    
    # === Protection Effects ===
    "opponent_immunity": EffectMetadata(
        effect_type="opponent_immunity",
        classification="continuous",
        action_type=None,
        requires_targets=False,
        target_description=None,
        strategic_note="This card cannot be targeted by opponent effects. Still vulnerable to tussles and board wipes.",
    ),
    "team_opponent_immunity": EffectMetadata(
        effect_type="team_opponent_immunity",
        classification="continuous",
        action_type=None,
        requires_targets=False,
        target_description=None,
        strategic_note="All your cards are immune to opponent targeting. Critical threat - protect this card.",
    ),
    
    # === Combat Modifiers ===
    "auto_win_tussle_on_own_turn": EffectMetadata(
        effect_type="auto_win_tussle_on_own_turn",
        classification="continuous",
        action_type=None,
        requires_targets=False,
        target_description=None,
        strategic_note="Wins all tussles on your turn regardless of stats. Powerful attacker.",
    ),
    "set_tussle_cost": EffectMetadata(
        effect_type="set_tussle_cost:N",
        classification="continuous",
        action_type=None,
        requires_targets=False,
        target_description=None,
        strategic_note="Changes tussle cost for all your Toys. Factor into Charge budgeting.",
    ),
    "set_self_tussle_cost": EffectMetadata(
        effect_type="set_self_tussle_cost:N:not_turn_1",
        classification="continuous",
        action_type=None,
        requires_targets=False,
        target_description=None,
        strategic_note="Changes this card's tussle cost (not turn 1). Budget Charge accordingly.",
    ),
    "cannot_tussle": EffectMetadata(
        effect_type="cannot_tussle",
        classification="continuous",
        action_type=None,
        requires_targets=False,
        target_description=None,
        strategic_note="This card cannot initiate tussles. Use for passive effects or other abilities only.",
    ),
    
    # === Special Effects ===
    "break_all": EffectMetadata(
        effect_type="break_all",
        classification="passive",
        action_type=None,  # Automatic when played
        requires_targets=False,
        target_description=None,
        strategic_note="Board wipe. Breaks ALL Toys in play (yours and opponent's). Game-changing effect.",
    ),
    "return_all_to_hand": EffectMetadata(
        effect_type="return_all_to_hand",
        classification="passive",
        action_type=None,
        requires_targets=False,
        target_description=None,
        strategic_note="Board wipe. Returns all cards in play to hand. Resets board state.",
    ),
    "copy_card": EffectMetadata(
        effect_type="copy_card",
        classification="activated",
        action_type="activate_ability",
        requires_targets=True,
        target_description="Target one card in play to copy its effects",
        strategic_note="Flexible effect. Copy the best card on the board. High strategic value.",
    ),
    "take_control": EffectMetadata(
        effect_type="take_control",
        classification="activated",
        action_type="activate_ability",
        requires_targets=True,
        target_description="Target one opponent Toy",
        strategic_note="Steals opponent's Toy. Powerful swing effect. Prioritize high-value targets.",
    ),
    
    # === Cost Modifiers ===
    "reduce_cost_by_broken": EffectMetadata(
        effect_type="reduce_cost_by_broken",
        classification="continuous",
        action_type=None,
        requires_targets=False,
        target_description=None,
        strategic_note="Cost reduced by 1 per card in break zone. Gets cheaper as game progresses.",
    ),
    "self_cost_increase_by_broken": EffectMetadata(
        effect_type="self_cost_increase_by_broken",
        classification="continuous",
        action_type=None,
        requires_targets=False,
        target_description=None,
        strategic_note="Cost increased by 1 per card in your break zone. Play early before your break zone fills up.",
    ),
    "alternative_cost_break_card": EffectMetadata(
        effect_type="alternative_cost_break_card",
        classification="passive",
        action_type=None,
        requires_targets=False,
        target_description=None,
        strategic_note="Can pay by breaking one of your cards instead of Charge. Useful when Charge-starved.",
    ),
    "opponent_cost_increase": EffectMetadata(
        effect_type="opponent_cost_increase:N",
        classification="continuous",
        action_type=None,
        requires_targets=False,
        target_description=None,
        strategic_note="Increases opponent's card costs. Disrupts their tempo and Charge economy.",
    ),
}


def get_effect_metadata(effect_definition: str) -> Optional[EffectMetadata]:
    """
    Get metadata for an effect definition.
    
    Args:
        effect_definition: Full effect string (e.g., "stat_boost:strength:2")
    
    Returns:
        EffectMetadata if found, None otherwise
    """
    # Extract the effect type pattern (without numeric parameters)
    parts = effect_definition.split(":")
    
    # Try exact match first
    if effect_definition in EFFECT_METADATA_REGISTRY:
        return EFFECT_METADATA_REGISTRY[effect_definition]
    
    # Try pattern match (e.g., "stat_boost:strength" for "stat_boost:strength:2")
    if len(parts) >= 2:
        pattern = ":".join(parts[:2])
        if pattern in EFFECT_METADATA_REGISTRY:
            return EFFECT_METADATA_REGISTRY[pattern]
    
    # Try base type
    if parts[0] in EFFECT_METADATA_REGISTRY:
        return EFFECT_METADATA_REGISTRY[parts[0]]
    
    return None


def extract_unique_effect_types(cards: List) -> List[str]:
    """
    Extract unique effect types from a list of cards.
    
    Args:
        cards: List of Card objects with effect_definitions field
    
    Returns:
        List of unique effect definition strings
    """
    effect_types = set()
    
    for card in cards:
        if hasattr(card, 'effect_definitions') and card.effect_definitions:
            # Split multiple effects
            effects = card.effect_definitions.split(";")
            for effect in effects:
                effect = effect.strip()
                if effect:
                    effect_types.add(effect)
    
    return sorted(effect_types)
