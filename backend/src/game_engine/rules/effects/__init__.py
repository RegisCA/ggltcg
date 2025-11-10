"""
Effect system for GGLTCG.

This package contains all card effects organized by type:
- base_effect: Abstract base classes for all effects
- effect_registry: Central registry for looking up effects by card name
- continuous_effects: Effects that apply while cards are in play
- triggered_effects: Effects that activate when conditions are met
- action_effects: Effects for Action cards and activated abilities

Usage:
    from game_engine.rules.effects import EffectRegistry
    
    # Get all effects for a card
    card_effects = EffectRegistry.get_effects(card)
    
    # Apply effects
    for effect in card_effects:
        if effect.can_apply(game_state):
            effect.apply(game_state)
"""

# Base classes
from .base_effect import (
    BaseEffect,
    ContinuousEffect,
    TriggeredEffect,
    ActivatedEffect,
    PlayEffect,
    CostModificationEffect,
    ProtectionEffect,
    EffectType,
    TriggerTiming,
)

# Effect registry
from .effect_registry import EffectRegistry

# Import all effect modules to trigger registration
# This ensures all effects are registered when the package is imported
from . import continuous_effects
from . import triggered_effects
from . import action_effects

__all__ = [
    # Base classes
    "BaseEffect",
    "ContinuousEffect",
    "TriggeredEffect",
    "ActivatedEffect",
    "PlayEffect",
    "CostModificationEffect",
    "ProtectionEffect",
    "EffectType",
    "TriggerTiming",
    # Registry
    "EffectRegistry",
]
