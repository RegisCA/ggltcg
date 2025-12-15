"""
Continuous effects that apply while cards are in play.

These effects modify game state continuously and stack if multiple copies exist.
They stop applying immediately when the source card leaves play.
"""

from typing import TYPE_CHECKING, Any
from .base_effect import (
    ContinuousEffect, CostModificationEffect, ProtectionEffect, BaseEffect,
    TriggeredEffect, TriggerTiming
)
from .effect_registry import EffectRegistry

if TYPE_CHECKING:
    from ...models.game_state import GameState
    from ...models.card import Card
    from ...models.player import Player


# ============================================================================
# GENERIC EFFECTS (Data-Driven)
# ============================================================================

class GainCCWhenSleepedEffect(TriggeredEffect):
    """
    Generic triggered effect for gaining CC when the card is sleeped.
    
    Triggers when the source card is sleeped from play.
    Does NOT trigger when sleeped from hand.
    
    Examples:
    - Umbruh: GainCCWhenSleepedEffect(source_card, amount=1)
    """
    
    def __init__(self, source_card: "Card", amount: int):
        """
        Initialize gain CC when sleeped effect.
        
        Args:
            source_card: The card providing this effect
            amount: How much CC to gain when sleeped
        """
        super().__init__(source_card, TriggerTiming.WHEN_SLEEPED, is_optional=False)
        self.amount = amount
    
    def should_trigger(self, game_state: "GameState", **kwargs: Any) -> bool:
        """Check if this is the card being sleeped."""
        sleeped_card = kwargs.get("sleeped_card")
        return sleeped_card == self.source_card
    
    def apply(self, game_state: "GameState", **kwargs: Any) -> None:
        """Grant CC to the card's owner when it's sleeped."""
        owner = game_state.get_card_owner(self.source_card)
        if owner:
            owner.gain_cc(self.amount)
    
    def modify_stat(self, card: "Card", stat_name: str, base_value: int,
                   game_state: "GameState") -> int:
        """Triggered effects don't modify stats."""
        return base_value


class StartOfTurnGainCCEffect(TriggeredEffect):
    """
    Belchaletta: "At the start of your turn, gain 2 charge."
    
    Triggered effect that grants CC at the start of the controller's turn.
    Only triggers while the card is in play.
    
    Examples:
    - Belchaletta: StartOfTurnGainCCEffect(source_card, amount=2)
    """
    
    def __init__(self, source_card: "Card", amount: int):
        """
        Initialize start of turn CC gain effect.
        
        Args:
            source_card: The card providing this effect
            amount: How much CC to gain at start of turn
        """
        super().__init__(source_card, TriggerTiming.START_OF_TURN, is_optional=False)
        self.amount = amount
    
    def should_trigger(self, game_state: "GameState", **kwargs: Any) -> bool:
        """
        Check if this effect should trigger.
        
        Only triggers if:
        1. Source card is in play
        2. It's the controller's turn
        """
        from ...models.card import Zone
        
        # Must be in play
        if self.source_card.zone != Zone.IN_PLAY:
            return False
        
        # Only trigger on controller's turn
        controller = game_state.get_card_controller(self.source_card)
        active_player = game_state.get_active_player()
        
        return controller == active_player
    
    def apply(self, game_state: "GameState", **kwargs: Any) -> None:
        """Grant CC to the card's controller at start of turn."""
        controller = game_state.get_card_controller(self.source_card)
        if controller:
            controller.gain_cc(self.amount)
    
    def modify_stat(self, card: "Card", stat_name: str, base_value: int,
                   game_state: "GameState") -> int:
        """Triggered effects don't modify stats."""
        return base_value


class OnCardPlayedGainCCEffect(TriggeredEffect):
    """
    Hind Leg Kicker: "When you play a card (not this one), gain 1 charge."
    
    Triggered effect that grants CC whenever the controller plays another card.
    Does NOT trigger when Hind Leg Kicker itself is played.
    Only triggers while the card is in play.
    
    Examples:
    - Hind Leg Kicker: OnCardPlayedGainCCEffect(source_card, amount=1)
    """
    
    def __init__(self, source_card: "Card", amount: int):
        """
        Initialize on card played CC gain effect.
        
        Args:
            source_card: The card providing this effect
            amount: How much CC to gain when another card is played
        """
        super().__init__(source_card, TriggerTiming.WHEN_OTHER_CARD_PLAYED, is_optional=False)
        self.amount = amount
    
    def should_trigger(self, game_state: "GameState", **kwargs: Any) -> bool:
        """
        Check if this effect should trigger.
        
        Only triggers if:
        1. Source card is in play
        2. A card was played (not this one)
        3. The card was played by this card's controller
        """
        from ...models.card import Zone
        
        # Must be in play
        if self.source_card.zone != Zone.IN_PLAY:
            return False
        
        played_card = kwargs.get("played_card")
        player = kwargs.get("player")
        
        if not played_card or not player:
            return False
        
        # Don't trigger for itself being played
        if played_card == self.source_card:
            return False
        
        # Only trigger for controller's plays
        controller = game_state.get_card_controller(self.source_card)
        return controller == player
    
    def apply(self, game_state: "GameState", **kwargs: Any) -> None:
        """Grant CC to the card's controller when another card is played."""
        controller = game_state.get_card_controller(self.source_card)
        if controller:
            controller.gain_cc(self.amount)
    
    def modify_stat(self, card: "Card", stat_name: str, base_value: int,
                   game_state: "GameState") -> int:
        """Triggered effects don't modify stats."""
        return base_value


class StatBoostEffect(ContinuousEffect):
    """
    Generic stat boost effect for data-driven cards.
    
    Can boost a specific stat or all stats for cards controlled by the source card's controller.
    Stacks with multiple copies in play.
    
    Examples:
    - Ka: StatBoostEffect(source_card, "strength", 2)
    - Demideca: StatBoostEffect(source_card, "all", 1)
    """
    
    def __init__(self, source_card: "Card", stat_name: str, amount: int):
        """
        Initialize stat boost effect.
        
        Args:
            source_card: The card providing this effect
            stat_name: Which stat to boost ("speed", "strength", "stamina", or "all")
            amount: How much to boost the stat(s)
        """
        super().__init__(source_card)
        self.stat_name = stat_name
        self.amount = amount
    
    def modify_stat(self, card: "Card", stat_name: str, base_value: int,
                   game_state: "GameState") -> int:
        """Apply stat boost to controller's cards."""
        # FIX (Issue #123): Only buff cards in IN_PLAY zone
        from ...models.card import Zone
        if card.zone != Zone.IN_PLAY:
            return base_value
        
        # Also check source card is in play
        if self.source_card.zone != Zone.IN_PLAY:
            return base_value
        
        # Check if this effect applies to the requested stat
        if self.stat_name != "all" and self.stat_name != stat_name:
            return base_value
        
        # Only modify toy stats (speed, strength, stamina)
        if stat_name not in ("speed", "strength", "stamina"):
            return base_value
        
        # Check if the card being modified is controlled by this effect's source card's controller
        card_controller = game_state.get_card_controller(card)
        effect_controller = game_state.get_card_controller(self.source_card)
        
        if card_controller and effect_controller and card_controller == effect_controller:
            return base_value + self.amount
        
        return base_value


class SetTussleCostEffect(CostModificationEffect):
    """
    Generic effect that sets tussle cost to a fixed value.
    
    Sets the tussle cost for all cards controlled by the source card's controller.
    Multiple instances don't stack - the lowest cost is used.
    
    Examples:
    - Wizard: SetTussleCostEffect(source_card, 1)
    """
    
    def __init__(self, source_card: "Card", cost: int):
        """
        Initialize tussle cost effect.
        
        Args:
            source_card: The card providing this effect
            cost: The fixed tussle cost (e.g., 1 for Wizard)
        """
        super().__init__(source_card)
        self.cost = cost
    
    def modify_stat(self, card: "Card", stat_name: str, base_value: int,
                   game_state: "GameState") -> int:
        """Tussle cost effect doesn't modify card stats."""
        return base_value
    
    def modify_tussle_cost(self, base_cost: int, game_state: "GameState",
                          controller: "Player") -> int:
        """Set tussle cost for controller's cards."""
        # FIX (Issue #123): Only apply to cards in IN_PLAY zone
        # (Tussle cost only matters for cards in play, but adding check for consistency)
        from ...models.card import Zone
        if self.source_card.zone != Zone.IN_PLAY:
            return base_cost
        
        effect_controller = game_state.get_card_controller(self.source_card)
        
        if effect_controller and effect_controller == controller:
            return self.cost
        
        return base_cost


class ReduceCostBySleepingEffect(CostModificationEffect):
    """
    Generic effect that reduces a card's cost based on sleeping cards.
    
    Reduces the source card's play cost by 1 for each card in the controller's
    sleep zone. Cost cannot go below 0.
    
    Examples:
    - Dream: ReduceCostBySleepingEffect(source_card)
    """
    
    def __init__(self, source_card: "Card"):
        """
        Initialize sleeping card cost reduction.
        
        Args:
            source_card: The card whose cost is reduced (e.g., Dream)
        """
        super().__init__(source_card)
    
    def modify_stat(self, card: "Card", stat_name: str, base_value: int,
                   game_state: "GameState") -> int:
        """Cost reduction doesn't modify card stats."""
        return base_value
    
    def modify_card_cost(self, card: "Card", base_cost: int,
                        game_state: "GameState", player: "Player") -> int:
        """Reduce source card's cost based on sleeping cards."""
        # Only applies to the source card itself
        if card != self.source_card:
            return base_cost
        
        # Get the card owner (the player trying to play it)
        card_owner = game_state.get_card_owner(self.source_card)
        
        # Only applies when the owner is playing it
        if card_owner != player:
            return base_cost
        
        # Count sleeping cards
        sleeping_count = len(player.sleep_zone)
        
        # Reduce cost by 1 per sleeping card
        modified_cost = base_cost - sleeping_count
        
        return max(0, modified_cost)  # Cost can't go below 0


class OpponentCostIncreaseEffect(CostModificationEffect):
    """
    Generic effect that increases the cost of opponent's cards while in play.
    
    Applies to all cards in the opponent's hand, making them more expensive to play.
    Only active while the source card is in play.
    
    Examples:
    - Gibbers: OpponentCostIncreaseEffect(source_card, amount=1)
    """
    
    def __init__(self, source_card: "Card", amount: int):
        """
        Initialize opponent cost increase effect.
        
        Args:
            source_card: The card providing this effect (e.g., Gibbers)
            amount: How much to increase opponent's card costs by
        """
        super().__init__(source_card)
        self.amount = amount
    
    def modify_stat(self, card: "Card", stat_name: str, base_value: int,
                   game_state: "GameState") -> int:
        """Cost increase doesn't modify card stats."""
        return base_value
    
    def modify_card_cost(self, card: "Card", base_cost: int,
                        game_state: "GameState", player: "Player") -> int:
        """Increase opponent's card costs while Gibbers is in play."""
        from ...models.card import Zone
        
        # Only applies while source card is in play
        if self.source_card.zone != Zone.IN_PLAY:
            return base_cost
        
        # Get the controller of the effect source (Gibbers)
        effect_controller = game_state.get_card_controller(self.source_card)
        
        # Only affects opponent's cards
        if effect_controller is None or player == effect_controller:
            return base_cost
        
        # Check if the card being modified is protected from this effect (e.g., Beary)
        if game_state.is_protected_from_effect(card, self):
            return base_cost
        
        # Increase the cost
        return base_cost + self.amount


class SetSelfTussleCostEffect(CostModificationEffect):
    """
    Generic effect that sets the source card's tussle cost with optional turn restriction.
    
    Sets the source card's tussle cost to a specific value.
    Can optionally prevent tussling on turn 1.
    
    Examples:
    - Raggy: SetSelfTussleCostEffect(source_card, cost=0, not_turn_1=True)
    """
    
    def __init__(self, source_card: "Card", cost: int, not_turn_1: bool = False):
        """
        Initialize self tussle cost effect.
        
        Args:
            source_card: The card whose tussle cost is modified
            cost: The fixed tussle cost (e.g., 0 for Raggy)
            not_turn_1: If True, card cannot tussle on turn 1 of the game
        """
        super().__init__(source_card)
        self.cost = cost
        self.not_turn_1 = not_turn_1
    
    def modify_stat(self, card: "Card", stat_name: str, base_value: int,
                   game_state: "GameState") -> int:
        """Self tussle cost doesn't modify card stats."""
        return base_value
    
    def modify_tussle_cost(self, base_cost: int, game_state: "GameState",
                          controller: "Player") -> int:
        """Set source card's tussle cost."""
        # This effect only applies to the source card itself
        # The game engine should pass context to know which card is tussling
        return self.cost
    
    def can_tussle(self, game_state: "GameState") -> bool:
        """
        Check if source card can tussle.
        
        If not_turn_1 is True, cannot tussle on turn 1 of the game.
        """
        if not self.not_turn_1:
            return True
        
        # Cannot tussle on turn 1 of the game
        return game_state.turn_number > 1


# ============================================================================
# LEGACY CARD-SPECIFIC EFFECTS (To be deprecated)
# ============================================================================

class KaEffect(ContinuousEffect):
    """
    Ka: "Your cards have +2 Strength."
    
    Applies +2 Strength to all cards controlled by Ka's controller.
    Stacks with multiple Ka in play.
    """
    
    def modify_stat(self, card: "Card", stat_name: str, base_value: int,
                   game_state: "GameState") -> int:
        """Apply +2 Strength to controller's cards."""
        # FIX (Issue #123): Only buff cards in IN_PLAY zone
        from ...models.card import Zone
        if card.zone != Zone.IN_PLAY:
            return base_value
        
        # Also check source card (Ka) is in play
        if self.source_card.zone != Zone.IN_PLAY:
            return base_value
        
        if stat_name != "strength":
            return base_value
        
        # Check if the card being modified is controlled by Ka's controller
        card_controller = game_state.get_card_controller(card)
        ka_controller = game_state.get_card_controller(self.source_card)
        
        if card_controller and ka_controller and card_controller == ka_controller:
            return base_value + 2
        
        return base_value


class WizardEffect(CostModificationEffect):
    """
    Wizard: "Your cards' tussles cost 1."
    
    Sets the tussle cost to 1 CC for all cards controlled by Wizard's controller.
    Multiple Wizards don't stack (cost stays at 1).
    """
    
    def modify_stat(self, card: "Card", stat_name: str, base_value: int,
                   game_state: "GameState") -> int:
        """Wizard doesn't modify stats."""
        return base_value
    
    def modify_tussle_cost(self, base_cost: int, game_state: "GameState",
                          controller: "Player") -> int:
        """Set tussle cost to 1 for Wizard's controller."""
        # FIX (Issue #123): Only apply when Wizard is in IN_PLAY zone
        from ...models.card import Zone
        if self.source_card.zone != Zone.IN_PLAY:
            return base_cost
        
        wizard_controller = game_state.get_card_controller(self.source_card)
        
        if wizard_controller and wizard_controller == controller:
            return 1
        
        return base_cost


class DemidecaEffect(ContinuousEffect):
    """
    Demideca: "Your cards have +1 of all stats."
    
    Applies +1 to Speed, Strength, and Stamina for all cards controlled by
    Demideca's controller. Stacks with multiple Demideca in play.
    """
    
    def modify_stat(self, card: "Card", stat_name: str, base_value: int,
                   game_state: "GameState") -> int:
        """Apply +1 to all stats for controller's cards."""
        # FIX (Issue #123): Only buff cards in IN_PLAY zone
        from ...models.card import Zone
        if card.zone != Zone.IN_PLAY:
            return base_value
        
        # Also check source card (Demideca) is in play
        if self.source_card.zone != Zone.IN_PLAY:
            return base_value
        
        # Only modify toy stats (speed, strength, stamina)
        if stat_name not in ("speed", "strength", "stamina"):
            return base_value
        
        card_controller = game_state.get_card_controller(card)
        demideca_controller = game_state.get_card_controller(self.source_card)
        
        if card_controller and demideca_controller and card_controller == demideca_controller:
            return base_value + 1
        
        return base_value


class RaggyEffect(CostModificationEffect):
    """
    Raggy: "This card's tussles cost 0."
    
    Sets Raggy's tussle cost to 0 CC.
    Restriction: Cannot tussle on Turn 1.
    """
    
    def modify_stat(self, card: "Card", stat_name: str, base_value: int,
                   game_state: "GameState") -> int:
        """Raggy doesn't modify stats."""
        return base_value
    
    def modify_tussle_cost(self, base_cost: int, game_state: "GameState",
                          controller: "Player") -> int:
        """Set Raggy's tussle cost to 0."""
        # This effect only applies to Raggy itself
        # The game engine should check the attacking card
        return 0
    
    def can_tussle(self, game_state: "GameState") -> bool:
        """
        Check if Raggy can tussle.
        
        Raggy cannot tussle on Turn 1 (the starting player's first turn).
        """
        return game_state.turn_number > 1


class OpponentImmunityEffect(ProtectionEffect):
    """
    Beary: "Your opponent's cards' effects don't affect this card."
    
    Prevents effects from opponent-controlled cards from affecting this card.
    Exception: Tussle damage is not an "effect" and can still harm this card.
    
    Note: This was originally Knight's effect, now swapped to Beary.
    """
    
    def __init__(self, source_card: "Card"):
        super().__init__(source_card, protects_from="opponent")
    
    def modify_stat(self, card: "Card", stat_name: str, base_value: int,
                   game_state: "GameState") -> int:
        """Opponent immunity doesn't modify stats."""
        return base_value
    
    def is_protected_from(self, effect: "BaseEffect", game_state: "GameState") -> bool:
        """
        Check if this card is protected from the given effect.
        
        Protected from effects of cards controlled by opponent.
        """
        # Get the controllers
        card_controller = game_state.get_card_controller(self.source_card)
        effect_controller = game_state.get_card_controller(effect.source_card)
        
        if not card_controller or not effect_controller:
            return False
        
        # Protected from opponent's effects
        return card_controller != effect_controller


class TeamOpponentImmunityEffect(ProtectionEffect):
    """
    Sock Sorcerer: "Your opponent's cards' effects don't affect your cards."
    
    Team-wide protection effect. While Sock Sorcerer is in play, ALL cards
    controlled by Sock Sorcerer's controller are protected from opponent's effects.
    
    This is like Beary's effect, but applied to the entire team.
    
    Note: This effect must be checked in is_protected_from_effect() for ALL cards,
    not just the target card's own effects.
    """
    
    def __init__(self, source_card: "Card"):
        super().__init__(source_card, protects_from="opponent_team")
    
    def modify_stat(self, card: "Card", stat_name: str, base_value: int,
                   game_state: "GameState") -> int:
        """Team immunity doesn't modify stats."""
        return base_value
    
    def is_card_protected(self, target_card: "Card", effect: "BaseEffect", 
                         game_state: "GameState") -> bool:
        """
        Check if a target card is protected by Sock Sorcerer.
        
        Args:
            target_card: The card being targeted by an effect
            effect: The effect trying to affect the target
            game_state: The current game state
            
        Returns:
            True if target is protected by this Sock Sorcerer
        """
        from ...models.card import Zone
        
        # Sock Sorcerer must be in play to provide protection
        if self.source_card.zone != Zone.IN_PLAY:
            return False
        
        # Get controllers
        sorcerer_controller = game_state.get_card_controller(self.source_card)
        target_controller = game_state.get_card_controller(target_card)
        effect_controller = game_state.get_card_controller(effect.source_card)
        
        if not sorcerer_controller or not target_controller or not effect_controller:
            return False
        
        # Protect all cards controlled by Sock Sorcerer's controller
        # from effects controlled by opponents
        if target_controller == sorcerer_controller:
            if effect_controller != sorcerer_controller:
                return True
        
        return False
    
    def is_protected_from(self, effect: "BaseEffect", game_state: "GameState") -> bool:
        """
        Check if Sock Sorcerer ITSELF is protected from the effect.
        
        Sock Sorcerer protects itself too (since it's part of "your cards").
        """
        return self.is_card_protected(self.source_card, effect, game_state)


class KnightWinConditionEffect(ContinuousEffect):
    """
    Knight: "On your turn, this card wins all tussles it enters."
    
    When Knight tussles on its controller's turn, it automatically wins:
    - The opposing Toy is sleeped immediately
    - The opposing Toy does not strike back
    """
    
    def modify_stat(self, card: "Card", stat_name: str, base_value: int,
                   game_state: "GameState") -> int:
        """Knight win condition doesn't modify stats."""
        return base_value
    
    def wins_tussle(self, game_state: "GameState", opponent_card: "Card") -> bool:
        """
        Check if Knight auto-wins the tussle.
        
        Args:
            game_state: Current game state
            opponent_card: The card Knight is tussling against
            
        Returns:
            True if Knight auto-wins (opponent is sleeped without striking back)
        """
        knight_controller = game_state.get_card_controller(self.source_card)
        active_player = game_state.get_active_player()
        
        # Only works on Knight's controller's turn
        if not knight_controller or knight_controller != active_player:
            return False
        
        return True


class DreamCostEffect(CostModificationEffect):
    """
    Dream: "This card costs 1 less for each of your sleeping cards."
    
    Reduces Dream's cost by 1 CC for each card in the controller's Sleep Zone.
    Cost cannot go below 0.
    """
    
    def modify_stat(self, card: "Card", stat_name: str, base_value: int,
                   game_state: "GameState") -> int:
        """Dream cost effect doesn't modify card stats."""
        return base_value
    
    def modify_card_cost(self, card: "Card", base_cost: int,
                        game_state: "GameState", player: "Player") -> int:
        """Reduce Dream's cost based on sleeping cards."""
        # Only applies to Dream itself
        if card != self.source_card:
            return base_cost
        
        # Get the controller of Dream (the player trying to play it)
        dream_controller = game_state.get_card_owner(self.source_card)
        
        # Only applies when the controller is playing it
        if dream_controller != player:
            return base_cost
        
        # Count sleeping cards
        sleeping_count = len(player.sleep_zone)
        
        # Reduce cost by 1 per sleeping card
        modified_cost = base_cost - sleeping_count
        
        return max(0, modified_cost)  # Cost can't go below 0


class BallaberCostEffect(CostModificationEffect):
    """
    Ballaber: "You may sleep 1 of your cards to play this card for free."
    
    Offers an alternative cost: instead of paying 3 CC, the player can
    sleep one of their own cards in play to play Ballaber for 0 CC.
    """
    
    def modify_stat(self, card: "Card", stat_name: str, base_value: int,
                   game_state: "GameState") -> int:
        """Ballaber cost effect doesn't modify card stats."""
        return base_value
    
    def modify_card_cost(self, card: "Card", base_cost: int,
                        game_state: "GameState", player: "Player") -> int:
        """If using alternative cost, set cost to 0."""
        # Only applies to Ballaber itself
        if card != self.source_card:
            return base_cost
        
        # Check if player is using alternative cost
        # This is indicated by 'use_alternative_cost' in game state context
        # The actual sleeping of the card happens during payment
        return base_cost  # Default cost, modified by payment method choice


class ArcherRestrictionEffect(ContinuousEffect):
    """
    Archer: "This card can't start tussles."
    
    Prevents Archer from being declared as an attacker in a tussle.
    """
    
    def modify_stat(self, card: "Card", stat_name: str, base_value: int,
                   game_state: "GameState") -> int:
        """Archer restriction doesn't modify stats."""
        return base_value
    
    def can_tussle(self, game_state: "GameState") -> bool:
        """Archer cannot start tussles."""
        return False


class DirectAttackEffect(ContinuousEffect):
    """
    Paper Plane: "This card can direct attack, even if your opponent has cards in play."
    
    Allows this card to perform direct attacks against the opponent's hand
    regardless of whether the opponent has cards in play. Bypasses the normal
    requirement that direct attacks can only happen when opponent's play zone is empty.
    """
    
    def modify_stat(self, card: "Card", stat_name: str, base_value: int,
                   game_state: "GameState") -> int:
        """Direct attack effect doesn't modify stats."""
        return base_value
    
    def can_direct_attack(self, game_state: "GameState") -> bool:
        """This card can always direct attack."""
        return True


# Register legacy effects (cards not yet migrated to data-driven system)
# Note: All cards now use data-driven effect_definitions from CSV!
# (Snuggles is registered in triggered_effects.py)

