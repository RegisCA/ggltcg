"""
Action card effects and activated abilities.

Action cards resolve their effect when played, then move to Sleep Zone.
Activated abilities can be used by paying a cost during the Main Phase.
"""

from typing import TYPE_CHECKING, Any, List, Optional
from .base_effect import PlayEffect, ActivatedEffect
from .effect_registry import EffectRegistry

if TYPE_CHECKING:
    from ...models.game_state import GameState
    from ...models.card import Card
    from ...models.player import Player


# ============================================================================
# ACTION CARDS
# ============================================================================

class CleanEffect(PlayEffect):
    """
    Clean: "Sleep all cards that are in play."
    
    Sleeps ALL Toys in play from both players.
    All sleeped cards trigger their "when sleeped" abilities if they have them.
    """
    
    def apply(self, game_state: "GameState", **kwargs: Any) -> None:
        """Sleep all cards currently in play."""
        # Get all cards in play from both players
        all_cards_in_play = game_state.get_all_cards_in_play()
        
        # Sleep each card
        for card in all_cards_in_play:
            game_state.sleep_card(card, was_in_play=True)


class RushEffect(PlayEffect):
    """
    Rush: "Gain 2 CC. This card may not be played on your first turn."
    
    Grants 2 CC to the player who played Rush.
    Restriction: Cannot be played on each player's first turn.
    - Player 1 (first player) cannot play on Turn 1
    - Player 2 (second player) cannot play on Turn 2
    """
    
    def can_apply(self, game_state: "GameState", **kwargs: Any) -> bool:
        """Rush cannot be played on a player's first turn."""
        player: Optional["Player"] = kwargs.get("player")
        if not player:
            return False
        
        # Determine player ID from the player's name ("human" or "ai")
        player_id = None
        for pid, p in game_state.players.items():
            if p == player:
                player_id = pid
                break
        
        if not player_id:
            return False
        
        # Check if this is the player's first turn
        # First player's first turn is Turn 1
        # Second player's first turn is Turn 2
        is_first_player = (player_id == game_state.first_player_id)
        is_first_turn = (is_first_player and game_state.turn_number == 1) or \
                       (not is_first_player and game_state.turn_number == 2)
        
        return not is_first_turn
    
    def apply(self, game_state: "GameState", **kwargs: Any) -> None:
        """Grant 2 CC to the player who played Rush."""
        player: Optional["Player"] = kwargs.get("player")
        if player:
            player.gain_cc(2)


class WakeEffect(PlayEffect):
    """
    Wake: "Unsleep 1 of your cards."
    
    Returns one card from your Sleep Zone to your hand.
    Player chooses which card to unsleep.
    """
    
    def requires_targets(self) -> bool:
        """Wake requires choosing a card to unsleep."""
        return True
    
    def get_min_targets(self) -> int:
        """Wake requires at least 0 targets (optional if no sleeping cards)."""
        return 0
    
    def get_valid_targets(self, game_state: "GameState") -> List["Card"]:
        """Get all cards in player's Sleep Zone."""
        player = game_state.get_active_player()
        if not player:
            return []
        return list(player.sleep_zone)
    
    def apply(self, game_state: "GameState", **kwargs: Any) -> None:
        """Return target card from Sleep Zone to hand."""
        target: Optional["Card"] = kwargs.get("target")
        player: Optional["Player"] = kwargs.get("player")
        
        if not target or not player:
            return
        
        # Verify target is in player's Sleep Zone
        if target not in player.sleep_zone:
            return
        
        # Unsleep the card (move to hand)
        game_state.unsleep_card(target, player)


class SunEffect(PlayEffect):
    """
    Sun: "Unsleep 2 of your cards."
    
    Returns up to 2 cards from your Sleep Zone to your hand.
    Player chooses which cards to unsleep.
    """
    
    def requires_targets(self) -> bool:
        """Sun requires choosing cards to unsleep."""
        return True
    
    def get_max_targets(self) -> int:
        """Sun can unsleep up to 2 cards."""
        return 2
    
    def get_min_targets(self) -> int:
        """Sun requires at least 0 targets (optional if no sleeping cards)."""
        return 0
    
    def get_valid_targets(self, game_state: "GameState") -> List["Card"]:
        """Get all cards in player's Sleep Zone."""
        player = game_state.get_active_player()
        if not player:
            return []
        return list(player.sleep_zone)
    
    def apply(self, game_state: "GameState", **kwargs: Any) -> None:
        """Return up to 2 target cards from Sleep Zone to hand."""
        targets: List["Card"] = kwargs.get("targets", [])
        player: Optional["Player"] = kwargs.get("player")
        
        if not player:
            return
        
        # Unsleep up to 2 cards
        for target in targets[:2]:  # Max 2
            if target in player.sleep_zone:
                game_state.unsleep_card(target, player)


class ToynadoEffect(PlayEffect):
    """
    Toynado: "Put all cards that are in play into their owner's hands."
    
    Returns ALL Toys in play to their owners' hands (not controllers').
    No "when sleeped" triggers occur (cards aren't sleeped, they're returned).
    """
    
    def apply(self, game_state: "GameState", **kwargs: Any) -> None:
        """Return all cards in play to their owners' hands."""
        all_cards_in_play = game_state.get_all_cards_in_play()
        
        for card in all_cards_in_play:
            # Return to owner's hand (not controller's)
            owner = game_state.get_card_owner(card)
            if owner:
                game_state.return_card_to_hand(card, owner)


class TwistEffect(PlayEffect):
    """
    Twist: "Put a card your opponent has in play in play, but under your control."
    
    Takes control of an opponent's Toy. The card switches to your side.
    Ownership doesn't change - if it leaves play, it goes to owner's zones.
    """
    
    def requires_targets(self) -> bool:
        """Twist requires choosing an opponent's card."""
        return True
    
    def get_valid_targets(self, game_state: "GameState") -> List["Card"]:
        """Get all opponent's cards in play."""
        player = game_state.get_active_player()
        if not player:
            return []
        
        opponent = game_state.get_opponent(player)
        if not opponent:
            return []
        
        return game_state.get_cards_in_play(opponent)
    
    def apply(self, game_state: "GameState", **kwargs: Any) -> None:
        """Take control of target opponent's card."""
        target: Optional["Card"] = kwargs.get("target")
        player: Optional["Player"] = kwargs.get("player")
        
        if not target or not player:
            return
        
        # Verify target is opponent's card
        opponent = game_state.get_opponent(player)
        if not opponent:
            return
        
        target_controller = game_state.get_card_controller(target)
        if target_controller != opponent:
            return
        
        # Transfer control to player
        game_state.change_control(target, player)


class CopyEffect(PlayEffect):
    """
    Copy: "This card acts as an exact copy of a card you have in play."
    
    Copy's cost equals the printed cost of the chosen Toy.
    Copy becomes an exact duplicate of the chosen Toy while in play.
    If Copy leaves play, it reverts to being "Copy" with cost "?".
    """
    
    def requires_targets(self) -> bool:
        """Copy requires choosing a Toy to copy."""
        return True
    
    def get_valid_targets(self, game_state: "GameState") -> List["Card"]:
        """Get all Toys the player controls in play."""
        player = game_state.get_active_player()
        if not player:
            return []
        
        cards_in_play = game_state.get_cards_in_play(player)
        # Only Toys can be copied (not Actions)
        return [card for card in cards_in_play if card.is_toy()]
    
    def get_copy_cost(self, target: "Card") -> int:
        """
        Calculate Copy's cost based on target.
        
        Copy costs the same as the printed cost of the card being copied.
        """
        return target.cost if target.cost >= 0 else 0
    
    def apply(self, game_state: "GameState", **kwargs: Any) -> None:
        """
        Transform Copy into an exact duplicate of the target.
        
        Copy gains:
        - Same name as target
        - Same stats (speed, strength, stamina)
        - Same abilities/effects
        - Everything about the target
        """
        target: Optional["Card"] = kwargs.get("target")
        
        if not target:
            return
        
        # Transform Copy into the target
        # This will be handled by the game engine
        # For now, we mark what Copy is copying
        self.source_card.copying = target


# ============================================================================
# ACTIVATED ABILITIES
# ============================================================================

class ArcherActivatedAbility(ActivatedEffect):
    """
    Archer: "You may spend CC to remove Stamina from cards."
    
    Costs 1 CC per 1 Stamina removed.
    Can target any Toy in play (yours or opponent's).
    Stamina removal is direct (not damage), so it doesn't trigger combat effects.
    If a Toy reaches 0 or fewer Stamina, it's sleeped immediately.
    """
    
    def __init__(self, source_card: "Card"):
        super().__init__(source_card, cost_cc=1)  # 1 CC per activation
    
    def requires_targets(self) -> bool:
        """Archer's ability requires choosing a card to affect."""
        return True
    
    def get_valid_targets(self, game_state: "GameState") -> List["Card"]:
        """Get all Toys in play (from both players)."""
        return game_state.get_all_cards_in_play()
    
    def apply(self, game_state: "GameState", **kwargs: Any) -> None:
        """
        Remove 1 Stamina from target card.
        
        Requires 'target' and 'amount' in kwargs.
        Amount defaults to 1 but can be higher if player pays more CC.
        """
        target: Optional["Card"] = kwargs.get("target")
        amount: int = kwargs.get("amount", 1)
        
        if not target:
            return
        
        # Verify target is a Toy with stamina
        if not hasattr(target, "stamina"):
            return
        
        # Remove stamina
        target.stamina -= amount
        
        # Check if card should be sleeped
        if target.stamina <= 0:
            game_state.sleep_card(target, was_in_play=True)


# Register all action effects
EffectRegistry.register_effect("Clean", CleanEffect)
EffectRegistry.register_effect("Rush", RushEffect)
EffectRegistry.register_effect("Wake", WakeEffect)
EffectRegistry.register_effect("Sun", SunEffect)
EffectRegistry.register_effect("Toynado", ToynadoEffect)
EffectRegistry.register_effect("Twist", TwistEffect)
EffectRegistry.register_effect("Copy", CopyEffect)

# Register activated abilities
EffectRegistry.register_effect("Archer", ArcherActivatedAbility)
