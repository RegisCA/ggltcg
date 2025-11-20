"""
Continuous effects that apply while cards are in play.

These effects modify game state continuously and stack if multiple copies exist.
They stop applying immediately when the source card leaves play.
"""

from typing import TYPE_CHECKING, Any
from .base_effect import ContinuousEffect, CostModificationEffect, ProtectionEffect, BaseEffect
from .effect_registry import EffectRegistry

if TYPE_CHECKING:
    from ...models.game_state import GameState
    from ...models.card import Card
    from ...models.player import Player


class KaEffect(ContinuousEffect):
    """
    Ka: "Your cards have +2 Strength."
    
    Applies +2 Strength to all cards controlled by Ka's controller.
    Stacks with multiple Ka in play.
    """
    
    def modify_stat(self, card: "Card", stat_name: str, base_value: int,
                   game_state: "GameState") -> int:
        """Apply +2 Strength to controller's cards."""
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
    
    def modify_tussle_cost(self, base_cost: int, game_state: "GameState",
                          controller: "Player") -> int:
        """Set tussle cost to 1 for Wizard's controller."""
        wizard_controller = game_state.get_card_controller(self.source_card)
        
        if wizard_controller and wizard_controller == controller:
            return 1
        
        return base_cost
    
    def modify_stat(self, card: "Card", stat_name: str, base_value: int,
                   game_state: "GameState") -> int:
        """Wizard also grants +1 to all stats."""
        card_controller = game_state.get_card_controller(card)
        wizard_controller = game_state.get_card_controller(self.source_card)
        
        if card_controller and wizard_controller and card_controller == wizard_controller:
            return base_value + 1
        
        return base_value


class DemidecaEffect(ContinuousEffect):
    """
    Demideca: "Your cards have +1 of all stats."
    
    Applies +1 to Speed, Strength, and Stamina for all cards controlled by
    Demideca's controller. Stacks with multiple Demideca in play.
    """
    
    def modify_stat(self, card: "Card", stat_name: str, base_value: int,
                   game_state: "GameState") -> int:
        """Apply +1 to all stats for controller's cards."""
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


class KnightProtectionEffect(ProtectionEffect):
    """
    Knight: "Your opponent's cards' effects don't affect this card."
    
    Prevents effects from opponent-controlled cards from affecting Knight.
    Exception: Tussle damage is not an "effect" and can still harm Knight.
    """
    
    def __init__(self, source_card: "Card"):
        super().__init__(source_card, protects_from="opponent")
    
    def modify_stat(self, card: "Card", stat_name: str, base_value: int,
                   game_state: "GameState") -> int:
        """Knight protection doesn't modify stats."""
        return base_value
    
    def is_protected_from(self, effect: "BaseEffect", game_state: "GameState") -> bool:
        """
        Check if Knight is protected from the given effect.
        
        Protected from effects of cards controlled by opponent.
        NOT protected from Beary's effects.
        """
        # Get the controllers
        knight_controller = game_state.get_card_controller(self.source_card)
        effect_controller = game_state.get_card_controller(effect.source_card)
        
        if not knight_controller or not effect_controller:
            return False
        
        # Special case: Beary's effects work on Knight
        if effect.source_card.name == "Beary":
            return False
        
        # Protected from opponent's effects
        return knight_controller != effect_controller


class KnightWinConditionEffect(ContinuousEffect):
    """
    Knight: "On your turn, this card wins all tussles it enters."
    
    When Knight tussles on its controller's turn, it automatically wins:
    - The opposing Toy is sleeped immediately
    - The opposing Toy does not strike back
    
    Exception: Doesn't work against Beary.
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
        
        # Doesn't work against Beary
        if opponent_card.name == "Beary":
            return False
        
        return True


class BearyProtectionEffect(ProtectionEffect):
    """
    Beary: "Knight's effects don't affect this card."
    
    Prevents effects from cards named "Knight" from affecting Beary.
    This means Knight's auto-win ability doesn't work against Beary.
    """
    
    def __init__(self, source_card: "Card"):
        super().__init__(source_card, protects_from="Knight")
    
    def modify_stat(self, card: "Card", stat_name: str, base_value: int,
                   game_state: "GameState") -> int:
        """Beary protection doesn't modify stats."""
        return base_value
    
    def is_protected_from(self, effect: "BaseEffect", game_state: "GameState") -> bool:
        """Check if Beary is protected from Knight's effects."""
        return effect.source_card.name == "Knight"


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


# Register all continuous effects
EffectRegistry.register_effect("Ka", KaEffect)
EffectRegistry.register_effect("Wizard", WizardEffect)
EffectRegistry.register_effect("Demideca", DemidecaEffect)
EffectRegistry.register_effect("Raggy", RaggyEffect)
EffectRegistry.register_effect("Knight", KnightProtectionEffect)
EffectRegistry.register_effect("Knight", KnightWinConditionEffect)
EffectRegistry.register_effect("Beary", BearyProtectionEffect)
EffectRegistry.register_effect("Archer", ArcherRestrictionEffect)
EffectRegistry.register_effect("Dream", DreamCostEffect)
EffectRegistry.register_effect("Ballaber", BallaberCostEffect)
