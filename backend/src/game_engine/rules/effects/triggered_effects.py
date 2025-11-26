"""
Triggered effects that activate when specific conditions are met.

Triggered effects:
- Have a specific trigger condition (when sleeped, when opponent tussles, etc.)
- May be optional (using "may") or mandatory
- Only trigger if the condition is met at the right time
"""

from typing import TYPE_CHECKING, Any, Optional
from .base_effect import TriggeredEffect, TriggerTiming
from .effect_registry import EffectRegistry

if TYPE_CHECKING:
    from ...models.game_state import GameState
    from ...models.card import Card


class UmbruhEffect(TriggeredEffect):
    """
    Umbruh: "When sleeped, gain 1 CC."
    
    Mandatory triggered ability that grants 1 CC to Umbruh's controller
    when Umbruh is sleeped from play.
    
    Important: Only triggers if Umbruh was in play when sleeped.
    Does NOT trigger if sleeped from hand (e.g., via direct attack).
    """
    
    def __init__(self, source_card: "Card"):
        super().__init__(
            source_card=source_card,
            trigger=TriggerTiming.WHEN_SLEEPED,
            is_optional=False  # Mandatory trigger
        )
    
    def should_trigger(self, game_state: "GameState", **kwargs: Any) -> bool:
        """
        Check if Umbruh's effect should trigger.
        
        Only triggers if:
        - The sleeped card is Umbruh itself
        - Umbruh was in play when it was sleeped (not from hand)
        """
        sleeped_card: Optional["Card"] = kwargs.get("sleeped_card")
        was_in_play: bool = kwargs.get("was_in_play", False)
        
        if sleeped_card != self.source_card:
            return False
        
        # Must have been in play to trigger
        return was_in_play
    
    def apply(self, game_state: "GameState", **kwargs: Any) -> None:
        """Grant 1 CC to Umbruh's controller."""
        controller = game_state.get_card_owner(self.source_card)
        if controller:
            controller.gain_cc(1)


class SnugglesWhenSleepedEffect(TriggeredEffect):
    """
    Snuggles: "When sleeped, you may sleep a card that is in play."
    
    Optional trigger when Snuggles is sleeped from play.
    Controller may choose a card from either play zone to sleep.
    """
    
    def __init__(self, source_card: "Card"):
        super().__init__(
            source_card=source_card,
            trigger=TriggerTiming.WHEN_SLEEPED,
            is_optional=True  # "may" means optional
        )
    
    def should_trigger(self, game_state: "GameState", **kwargs: Any) -> bool:
        """
        Check if Snuggles' sleep effect should trigger.
        
        Only triggers if Snuggles was in play when sleeped.
        """
        sleeped_card: Optional["Card"] = kwargs.get("sleeped_card")
        was_in_play: bool = kwargs.get("was_in_play", False)
        
        if sleeped_card != self.source_card:
            return False
        
        return was_in_play
    
    def apply(self, game_state: "GameState", **kwargs: Any) -> None:
        """
        Sleep a card in play.
        
        Requires 'target' in kwargs specifying which card to sleep.
        If no target provided, does nothing (optional effect).
        Can target cards from either player's play zone.
        """
        target: Optional["Card"] = kwargs.get("target")
        
        if not target:
            return  # Optional, player chose not to use it
        
        # Verify target is in play (either player's zone)
        all_cards_in_play = game_state.get_all_cards_in_play()
        if target not in all_cards_in_play:
            return  # Invalid target
        
        # Sleep the target via game engine to trigger cascading effects
        game_engine = kwargs.get("game_engine")
        if game_engine:
            owner = game_state.get_card_owner(target)
            game_engine._sleep_card(target, owner, was_in_play=True)
        else:
            # Fallback for tests without game_engine
            game_state.sleep_card(target, was_in_play=True)


# Register legacy effects (cards not yet migrated to data-driven system)
# Note: Umbruh now uses data-driven effect_definitions (gain_cc_when_sleeped:1)
EffectRegistry.register_effect("Snuggles", SnugglesWhenSleepedEffect)  # NOT WORKING - needs implementation
