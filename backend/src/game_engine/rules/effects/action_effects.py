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
# GENERIC ACTION EFFECTS (Data-Driven)
# ============================================================================

class GainCCEffect(PlayEffect):
    """
    Generic CC gain effect for data-driven cards.
    
    Can optionally restrict when the effect can be played (e.g., not on first turn).
    
    Examples:
    - Rush: GainCCEffect(source_card, amount=2, not_first_turn=True)
    """
    
    def __init__(self, source_card: "Card", amount: int, not_first_turn: bool = False):
        """
        Initialize CC gain effect.
        
        Args:
            source_card: The card providing this effect
            amount: How much CC to gain
            not_first_turn: If True, cannot be played on player's first turn
        """
        super().__init__(source_card)
        self.amount = amount
        self.not_first_turn = not_first_turn
    
    def can_apply(self, game_state: "GameState", **kwargs: Any) -> bool:
        """Check if effect can be applied (e.g., not on first turn restriction)."""
        if not self.not_first_turn:
            return True
        
        player: Optional["Player"] = kwargs.get("player")
        if not player:
            return False
        
        # Determine if this is the player's first turn
        player_id = None
        for pid, p in game_state.players.items():
            if p == player:
                player_id = pid
                break
        
        if not player_id:
            return False
        
        # First player's first turn is Turn 1
        # Second player's first turn is Turn 2
        is_first_player = (player_id == game_state.first_player_id)
        is_first_turn = (is_first_player and game_state.turn_number == 1) or \
                       (not is_first_player and game_state.turn_number == 2)
        
        return not is_first_turn
    
    def apply(self, game_state: "GameState", **kwargs: Any) -> None:
        """Grant CC to the player who played this card."""
        player: Optional["Player"] = kwargs.get("player")
        if player:
            player.gain_cc(self.amount)


class TurnStatBoostEffect(PlayEffect):
    """
    VeryVeryAppleJuice: "This turn, your cards have 1 more of each stat."
    
    Turn-scoped stat boost effect - boosts stats only for the current turn.
    The boost is applied to all of the player's toys currently in play.
    
    Unlike continuous effects (Ka, Demideca), this:
    - Is applied once when the action is played
    - Only lasts until end of turn
    - Does NOT affect cards played later in the turn
    
    Examples:
    - VeryVeryAppleJuice: TurnStatBoostEffect(source_card, "all", 1)
    """
    
    def __init__(self, source_card: "Card", stat_name: str = "all", amount: int = 1):
        """
        Initialize turn-scoped stat boost effect.
        
        Args:
            source_card: The card providing this effect
            stat_name: Stat to boost ("speed", "strength", "stamina", or "all")
            amount: Amount to boost (default 1)
        """
        super().__init__(source_card)
        self.stat_name = stat_name
        self.amount = amount
    
    def apply(self, game_state: "GameState", **kwargs: Any) -> None:
        """Apply turn-scoped stat boost to all player's toys in play."""
        player: Optional["Player"] = kwargs.get("player")
        if not player:
            return
        
        current_turn = game_state.turn_number
        
        # Apply to all toys currently in play for this player
        for card in player.in_play:
            if card.is_toy():
                card.add_turn_modification(current_turn, self.stat_name, self.amount)


class UnsleepEffect(PlayEffect):
    """
    Generic unsleep effect for data-driven cards.
    
    Returns N cards from player's Sleep Zone to their hand.
    Player chooses which cards to unsleep.
    Can optionally filter by card type (actions or toys only).
    
    Examples:
    - Wake: UnsleepEffect(source_card, count=1)
    - Sun: UnsleepEffect(source_card, count=2)
    - That was fun: UnsleepEffect(source_card, count=1, card_type_filter="actions")
    """
    
    def __init__(self, source_card: "Card", count: int, card_type_filter: Optional[str] = None):
        """
        Initialize unsleep effect.
        
        Args:
            source_card: The card providing this effect
            count: How many cards to unsleep
            card_type_filter: Optional filter - "actions" or "toys" (None = all cards)
        """
        super().__init__(source_card)
        self.count = count
        self.card_type_filter = card_type_filter
    
    def requires_targets(self) -> bool:
        """Unsleep effect requires choosing cards to unsleep."""
        return True
    
    def get_max_targets(self) -> int:
        """Return the maximum number of cards that can be unsleeped."""
        return self.count
    
    def get_min_targets(self) -> int:
        """Unsleep requires at least 0 targets (optional if no sleeping cards)."""
        return 0
    
    def get_valid_targets(self, game_state: "GameState", player: Optional["Player"] = None) -> List["Card"]:
        """Get cards in player's Sleep Zone, optionally filtered by card type."""
        if player is None:
            player = game_state.get_active_player()
        if not player:
            return []
        
        cards = list(player.sleep_zone)
        
        # Apply card type filter if specified
        if self.card_type_filter == "actions":
            cards = [c for c in cards if c.is_action()]
        elif self.card_type_filter == "toys":
            cards = [c for c in cards if c.is_toy()]
        
        return cards
    
    def apply(self, game_state: "GameState", **kwargs: Any) -> None:
        """Return target cards from Sleep Zone to hand."""
        targets: Optional[List["Card"]] = kwargs.get("targets")
        player: Optional["Player"] = kwargs.get("player")
        
        if not targets or not player:
            return
        
        # Unsleep each target (up to count)
        for target in targets[:self.count]:
            if target in player.sleep_zone:
                game_state.unsleep_card(target, player)


class SleepAllEffect(PlayEffect):
    """
    Generic sleep all cards effect for data-driven cards.
    
    Sleeps ALL toys in play from both players.
    All sleeped cards trigger their "when sleeped" abilities if they have them.
    
    Examples:
    - Clean: SleepAllEffect(source_card)
    """
    
    def __init__(self, source_card: "Card"):
        """
        Initialize sleep all effect.
        
        Args:
            source_card: The card providing this effect
        """
        super().__init__(source_card)
    
    def apply(self, game_state: "GameState", **kwargs: Any) -> None:
        """Sleep all cards currently in play (except protected ones)."""
        # Get game_engine reference to properly trigger effects
        game_engine = kwargs.get("game_engine")
        if not game_engine:
            # Fallback: just move cards without triggering effects
            # This shouldn't happen in normal play but allows for testing
            all_cards_in_play = game_state.get_all_cards_in_play()
            for card in all_cards_in_play:
                # FIX (Issue #70): Check if card is protected from this effect
                if not game_state.is_protected_from_effect(card, self):
                    game_state.sleep_card(card, was_in_play=True)
            return
        
        # Get all cards in play from both players
        all_cards_in_play = game_state.get_all_cards_in_play()
        
        # Sleep each card through game engine (triggers effects)
        for card in all_cards_in_play:
            # FIX (Issue #70): Check if card is protected from this effect
            if game_state.is_protected_from_effect(card, self):
                continue  # Skip protected cards
            
            owner = game_state.get_card_owner(card)
            if owner:
                game_engine._sleep_card(card, owner, was_in_play=True)


class SleepTargetEffect(PlayEffect):
    """
    Drop: "Sleep a card that is in play."
    
    Targeted sleep effect - player chooses one card from either player's
    in-play zone to sleep. Triggers "when sleeped" effects.
    Respects protection effects (e.g., Beary, Sock Sorcerer).
    """
    
    def __init__(self, source_card: "Card", count: int = 1):
        """
        Initialize targeted sleep effect.
        
        Args:
            source_card: The card providing this effect
            count: Number of targets to sleep (default 1)
        """
        super().__init__(source_card)
        self.count = count
    
    def requires_targets(self) -> bool:
        """Sleep target effect requires choosing cards to sleep."""
        return True
    
    def get_max_targets(self) -> int:
        """Return the maximum number of cards that can be targeted."""
        return self.count
    
    def get_min_targets(self) -> int:
        """At least 1 target required if any valid targets exist."""
        return 1
    
    def get_valid_targets(self, game_state: "GameState", player: Optional["Player"] = None) -> List["Card"]:
        """Get all cards in play from both players (except protected ones)."""
        all_cards = game_state.get_all_cards_in_play()
        return [c for c in all_cards if not game_state.is_protected_from_effect(c, self)]
    
    def apply(self, game_state: "GameState", **kwargs: Any) -> None:
        """Sleep target cards."""
        targets: Optional[List["Card"]] = kwargs.get("targets")
        game_engine = kwargs.get("game_engine")
        
        if not targets:
            return
        
        for target in targets[:self.count]:
            # Double-check protection (in case state changed)
            if game_state.is_protected_from_effect(target, self):
                continue
            
            owner = game_state.get_card_owner(target)
            if owner:
                if game_engine:
                    game_engine._sleep_card(target, owner, was_in_play=True)
                else:
                    game_state.sleep_card(target, was_in_play=True)


class ReturnTargetToHandEffect(PlayEffect):
    """
    Jumpscare: "Put a card that is in play into their owner's hand."
    
    Targeted bounce effect - player chooses one card from either player's
    in-play zone to return to its OWNER's hand (not controller's).
    Does NOT trigger "when sleeped" effects (card is bounced, not sleeped).
    Respects protection effects.
    """
    
    def __init__(self, source_card: "Card", count: int = 1):
        """
        Initialize targeted return-to-hand effect.
        
        Args:
            source_card: The card providing this effect
            count: Number of targets to bounce (default 1)
        """
        super().__init__(source_card)
        self.count = count
    
    def requires_targets(self) -> bool:
        """Return target effect requires choosing cards to bounce."""
        return True
    
    def get_max_targets(self) -> int:
        """Return the maximum number of cards that can be targeted."""
        return self.count
    
    def get_min_targets(self) -> int:
        """At least 1 target required if any valid targets exist."""
        return 1
    
    def get_valid_targets(self, game_state: "GameState", player: Optional["Player"] = None) -> List["Card"]:
        """Get all cards in play from both players (except protected ones)."""
        all_cards = game_state.get_all_cards_in_play()
        return [c for c in all_cards if not game_state.is_protected_from_effect(c, self)]
    
    def apply(self, game_state: "GameState", **kwargs: Any) -> None:
        """Return target cards to their owners' hands."""
        targets: Optional[List["Card"]] = kwargs.get("targets")
        
        if not targets:
            return
        
        for target in targets[:self.count]:
            # Double-check protection
            if game_state.is_protected_from_effect(target, self):
                continue
            
            owner = game_state.get_card_owner(target)
            if not owner:
                continue
            
            # Remove from current controller's in_play
            for p in game_state.players.values():
                if target in p.in_play:
                    p.in_play.remove(target)
                    break
            
            # Return to owner's hand (not controller's)
            game_state.return_card_to_hand(target, owner)


# ============================================================================
# CUSTOM CARD-SPECIFIC ACTION EFFECTS
# These cards have complex mechanics that cannot be easily parameterized
# in the data-driven system, so they remain as custom effect classes.
# ============================================================================

class ToynadoEffect(PlayEffect):
    """
    Toynado: "Put all cards that are in play into their owner's hands."
    
    Returns ALL Toys in play to their owners' hands (not controllers').
    No "when sleeped" triggers occur (cards aren't sleeped, they're returned).
    """
    
    def apply(self, game_state: "GameState", **kwargs: Any) -> None:
        """Return all cards in play to their owners' hands (except protected ones)."""
        # Collect all cards from in-play zones first
        all_cards_in_play = []
        for player in game_state.players.values():
            all_cards_in_play.extend(player.in_play[:])  # Create a copy to avoid modification during iteration
        
        # Now process each card and add to owner's hand
        for card in all_cards_in_play:
            # Check if card is protected from this effect
            if game_state.is_protected_from_effect(card, self):
                continue  # Skip protected cards - they stay in play
            
            owner = game_state.get_card_owner(card)
            if owner:
                # Remove from current player's in_play
                for player in game_state.players.values():
                    if card in player.in_play:
                        player.in_play.remove(card)
                        break
                # Add to owner's hand
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
    
    def get_valid_targets(self, game_state: "GameState", player: Optional["Player"] = None) -> List["Card"]:
        """Get all opponent's cards in play that aren't protected from this effect."""
        if player is None:
            player = game_state.get_active_player()
        
        if not player:
            return []
        
        opponent = game_state.get_opponent(player.player_id)
        if not opponent:
            return []
        
        # Filter out cards protected from this effect (e.g., Beary with opponent_immunity)
        all_cards = game_state.get_cards_in_play(opponent)
        return [card for card in all_cards if not game_state.is_protected_from_effect(card, self)]
    
    def apply(self, game_state: "GameState", **kwargs: Any) -> None:
        """Take control of target opponent's card (unless protected)."""
        target: Optional["Card"] = kwargs.get("target")
        player: Optional["Player"] = kwargs.get("player")
        
        if not target or not player:
            return
        
        # Check if target is protected from this effect
        if game_state.is_protected_from_effect(target, self):
            return  # Cannot twist protected cards
        
        # Verify target is opponent's card
        opponent = game_state.get_opponent(player.player_id)
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
    
    Copy's cost equals the printed cost of the chosen card.
    Copy transforms into a copy of the chosen card while in play.
    If Copy leaves play, it reverts to being "Copy" with cost "?".
    """
    
    def requires_targets(self) -> bool:
        """Copy requires choosing a card to copy."""
        return True
    
    def get_valid_targets(self, game_state: "GameState", player: Optional["Player"] = None) -> List["Card"]:
        """Get all cards the player controls in play (any type)."""
        if player is None:
            player = game_state.get_active_player()
        if not player:
            return []
        
        # Can copy any card in play, not just Toys
        return game_state.get_cards_in_play(player)
    
    def get_copy_cost(self, target: "Card") -> int:
        """
        Calculate Copy's cost based on target.
        
        Copy costs the same as the printed cost of the card being copied.
        """
        return target.cost if target.cost >= 0 else 0
    
    def apply(self, game_state: "GameState", **kwargs: Any) -> None:
        """
        Transform the Copy card into a copy of the target.
        
        The Copy card itself is transformed (not a new card created):
        - name becomes "Copy of [Target]"
        - card_type, stats, effects copied from target
        - owner and controller remain unchanged
        - zone remains IN_PLAY
        - Original Copy card is preserved (no new cards created)
        """
        target: Optional["Card"] = kwargs.get("target")
        copy_card = self.source_card
        
        if not target or not copy_card:
            return
        
        # Mark card as transformed (used by reset_modifications to know to reset)
        copy_card._is_transformed = True
        
        # Transform Copy card properties to match target
        copy_card.name = f"Copy of {target.name}"
        copy_card.card_type = target.card_type
        copy_card.cost = target.cost
        copy_card.effect_text = target.effect_text
        copy_card.effect_definitions = target.effect_definitions
        
        # Copy stats if target has them (Toys)
        if hasattr(target, 'speed'):
            copy_card.speed = target.speed
        if hasattr(target, 'strength'):
            copy_card.strength = target.strength
        if hasattr(target, 'stamina'):
            copy_card.stamina = target.stamina
            copy_card.current_stamina = target.stamina  # Full health
        
        # Copy visual properties
        if hasattr(target, 'primary_color'):
            copy_card.primary_color = target.primary_color
        if hasattr(target, 'accent_color'):
            copy_card.accent_color = target.accent_color
        
        # CRITICAL: Re-parse and attach the target's effects to the Copy card
        # This makes Copy's effects actually work (e.g., Ka's +2 strength)
        from .effect_registry import EffectFactory
        if (copy_card.effect_definitions and 
            isinstance(copy_card.effect_definitions, str) and 
            copy_card.effect_definitions.strip()):
            copy_card._copied_effects = EffectFactory.parse_effects(
                copy_card.effect_definitions, 
                copy_card
            )
        
        game_state.log_event(f"Copy transformed into {copy_card.name}")


# ============================================================================
# ACTIVATED ABILITIES
# ============================================================================

class ArcherActivatedAbility(ActivatedEffect):
    """
    Archer: "You may spend CC to remove Stamina from cards."
    
    Costs 1 CC per 1 Stamina removed.
    Can only target opponent's Toys in play.
    Stamina removal is direct (not damage), so it doesn't trigger combat effects.
    If a Toy reaches 0 or fewer Stamina, it's sleeped immediately.
    """
    
    def __init__(self, source_card: "Card"):
        super().__init__(source_card, cost_cc=1)  # 1 CC per activation
    
    def requires_targets(self) -> bool:
        """Archer's ability requires choosing a card to affect."""
        return True
    
    def get_valid_targets(self, game_state: "GameState") -> List["Card"]:
        """Get all opponent's Toys in play (except protected ones like Beary)."""
        active_player = game_state.get_active_player()
        opponent = game_state.get_opponent(active_player.player_id)
        # Filter out cards protected from this effect (e.g., Beary with opponent_immunity)
        return [card for card in opponent.in_play if not game_state.is_protected_from_effect(card, self)]
    
    def apply(self, game_state: "GameState", **kwargs: Any) -> None:
        """
        Remove 1 Stamina from target card.
        
        Requires 'target' and 'amount' in kwargs.
        Amount defaults to 1 but can be higher if player pays more CC.
        """
        target: Optional["Card"] = kwargs.get("target")
        amount: int = kwargs.get("amount", 1)
        game_engine = kwargs.get("game_engine")
        
        if not target:
            return
        
        # Verify target is a Toy with stamina
        if not hasattr(target, "current_stamina"):
            return
        
        # Apply damage (updates current_stamina, not base stamina)
        target.apply_damage(amount)
        
        # Check if card should be sleeped using proper effective stamina calculation
        # Use game_engine.is_card_defeated() for consistency with tussle resolution
        if game_engine and game_engine.is_card_defeated(target):
            # Sleep via game engine to trigger when-sleeped effects
            owner = game_state.get_card_owner(target)
            game_engine._sleep_card(target, owner, was_in_play=True)
        elif not game_engine and target.current_stamina <= 0:
            # Fallback for tests without game_engine - simple check
            game_state.sleep_card(target, was_in_play=True)


# Register legacy effects (cards not yet migrated to data-driven system)
# Note: All action cards now use data-driven effect_definitions from CSV!
