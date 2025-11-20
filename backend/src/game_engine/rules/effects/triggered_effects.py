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
    when Umbruh is sleeped (from play or hand).
    
    Triggers whenever Umbruh is moved to the sleep zone, regardless of
    whether it was in play or in hand.
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
        """
        sleeped_card: Optional["Card"] = kwargs.get("sleeped_card")
        
        if sleeped_card != self.source_card:
            return False
        
        # Triggers regardless of whether from play or hand
        return True
    
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
        
        # Sleep the target
        game_state.sleep_card(target, was_in_play=True)


class BearyTussleCancelEffect(TriggeredEffect):
    """
    Beary: "When your opponent tussles, you may play this card, the tussle is cancelled."
    
    Optional triggered ability that can be activated from hand when opponent
    declares a tussle. If used, Beary is played (paying 1 CC cost) and the
    tussle is cancelled.
    
    Important: The opponent does NOT get their tussle cost refunded.
    """
    
    def __init__(self, source_card: "Card"):
        super().__init__(
            source_card=source_card,
            trigger=TriggerTiming.WHEN_OPPONENT_TUSSLES,
            is_optional=True  # "may" means optional
        )
    
    def should_trigger(self, game_state: "GameState", **kwargs: Any) -> bool:
        """
        Check if Beary can cancel the tussle.
        
        Requirements:
        - Beary is in hand (not in play)
        - It's the opponent's turn (they're tussling)
        - Controller has enough CC to play Beary (1 CC)
        """
        # Check if Beary is in hand
        beary_controller = game_state.get_card_owner(self.source_card)
        if not beary_controller or self.source_card not in beary_controller.hand:
            return False
        
        # Check if controller has enough CC
        if beary_controller.cc < 1:  # Beary costs 1 CC
            return False
        
        # Check if it's opponent's turn
        active_player = game_state.get_active_player()
        if active_player == beary_controller:
            return False  # Can't cancel your own tussles
        
        return True
    
    def apply(self, game_state: "GameState", **kwargs: Any) -> None:
        """
        Cancel the tussle and play Beary.
        
        Steps:
        1. Pay Beary's cost (1 CC)
        2. Move Beary from hand to in play
        3. Cancel the tussle (game engine handles this)
        """
        beary_controller = game_state.get_card_owner(self.source_card)
        if not beary_controller:
            return
        
        # Pay the cost
        beary_controller.spend_cc(1)
        
        # Move Beary from hand to play
        game_state.play_card_from_hand(self.source_card, beary_controller)
        
        # Mark that tussle should be cancelled
        # The game engine will check this flag
        kwargs["tussle_cancelled"] = True


# Register all triggered effects
EffectRegistry.register_effect("Umbruh", UmbruhEffect)
EffectRegistry.register_effect("Snuggles", SnugglesWhenSleepedEffect)
EffectRegistry.register_effect("Beary", BearyTussleCancelEffect)
