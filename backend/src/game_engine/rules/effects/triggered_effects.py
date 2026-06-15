"""
Triggered effects that activate when specific conditions are met.

Triggered effects:
- Have a specific trigger condition (when sleeped, when opponent tussles, etc.)
- May be optional (using "may") or mandatory
- Only trigger if the condition is met at the right time
"""

from typing import TYPE_CHECKING, Any, Optional
from .base_effect import TriggeredEffect, TriggerTiming

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
