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


class SnugglesOnPlayEffect(TriggeredEffect):
    """
    Snuggles: "When played, you may sleep one of your opponent's cards."
    
    Optional triggered ability when Snuggles enters play.
    The controller chooses an opponent's card in play to sleep.
    """
    
    def __init__(self, source_card: "Card"):
        super().__init__(
            source_card=source_card,
            trigger=TriggerTiming.WHEN_PLAYED,
            is_optional=True  # "may" means optional
        )
    
    def should_trigger(self, game_state: "GameState", **kwargs: Any) -> bool:
        """Triggers when Snuggles is played."""
        played_card: Optional["Card"] = kwargs.get("played_card")
        return played_card == self.source_card
    
    def apply(self, game_state: "GameState", **kwargs: Any) -> None:
        """
        Sleep an opponent's card.
        
        Requires 'target' in kwargs specifying which card to sleep.
        If no target provided or target is invalid, does nothing.
        """
        target: Optional["Card"] = kwargs.get("target")
        
        if not target:
            return  # Optional, player chose not to use it
        
        # Verify target is an opponent's card in play
        snuggles_controller = game_state.get_card_controller(self.source_card)
        target_controller = game_state.get_card_controller(target)
        
        if not snuggles_controller or not target_controller:
            return
        
        if snuggles_controller == target_controller:
            return  # Can't target own cards
        
        # Check if target is protected (e.g., Knight)
        if game_state.is_protected_from_effect(target, self):
            return
        
        # Sleep the target
        game_state.sleep_card(target, was_in_play=True)


class SnugglesWhenSleepedEffect(TriggeredEffect):
    """
    Snuggles: "When sleeped, your opponent discards a card."
    
    Mandatory trigger when Snuggles is sleeped from play.
    Opponent must discard a random card from their hand.
    """
    
    def __init__(self, source_card: "Card"):
        super().__init__(
            source_card=source_card,
            trigger=TriggerTiming.WHEN_SLEEPED,
            is_optional=False  # Mandatory
        )
    
    def should_trigger(self, game_state: "GameState", **kwargs: Any) -> bool:
        """
        Check if Snuggles' discard effect should trigger.
        
        Only triggers if Snuggles was in play when sleeped.
        """
        sleeped_card: Optional["Card"] = kwargs.get("sleeped_card")
        was_in_play: bool = kwargs.get("was_in_play", False)
        
        if sleeped_card != self.source_card:
            return False
        
        return was_in_play
    
    def apply(self, game_state: "GameState", **kwargs: Any) -> None:
        """Make opponent discard a random card from hand."""
        snuggles_controller = game_state.get_card_owner(self.source_card)
        if not snuggles_controller:
            return
        
        # Get opponent
        opponent = game_state.get_opponent(snuggles_controller)
        if not opponent or not opponent.hand:
            return  # No cards to discard
        
        # Sleep a random card from opponent's hand
        # Note: Sleeping from hand does NOT trigger "when sleeped" abilities
        import random
        card_to_sleep = random.choice(opponent.hand)
        game_state.sleep_card(card_to_sleep, was_in_play=False)


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
EffectRegistry.register_effect("Snuggles", SnugglesOnPlayEffect)
EffectRegistry.register_effect("Snuggles", SnugglesWhenSleepedEffect)
EffectRegistry.register_effect("Beary", BearyTussleCancelEffect)
