"""
Main game engine for GGLTCG.

The GameEngine class orchestrates all game actions, validates moves,
applies effects, and manages game state.
"""

import logging
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum
import random

from .models.game_state import GameState, Phase
from .models.player import Player
from .models.card import Card, CardType, Zone
from .rules.effects import EffectRegistry, EffectType, TriggerTiming
from .rules.effects.base_effect import (
    ContinuousEffect, TriggeredEffect, PlayEffect, 
    ActivatedEffect, CostModificationEffect
)

logger = logging.getLogger(__name__)

class ActionType(Enum):
    """Types of actions a player can take."""
    PLAY_CARD = "play_card"
    TUSSLE = "tussle"
    ACTIVATE_ABILITY = "activate_ability"
    END_TURN = "end_turn"


class GameEngine:
    """
    Main game engine that manages game state and executes actions.
    
    Responsibilities:
    - Validate player actions
    - Apply card effects using the effect system
    - Manage turn phases and progression
    - Handle tussles and combat resolution
    - Check state-based actions (sleep defeated cards, check victory)
    - Execute special card mechanics (Copy transformation, etc.)
    """
    
    def __init__(self, game_state: GameState):
        """
        Initialize the game engine.
        
        Args:
            game_state: The game state to manage
        """
        self.game_state = game_state
    
    # ========================================================================
    # TURN MANAGEMENT
    # ========================================================================
    
    def start_turn(self) -> None:
        """
        Start a new turn.
        
        Phase 1 - Start of Turn:
        1. Gain 4 CC (or 2 CC on Turn 1 for starting player)
        2. Resolve "at start of turn" effects (none in current card set)
        """
        player = self.game_state.get_active_player()
        self.game_state.phase = Phase.START
        
        # Reset turn counters
        player.reset_turn_counters()
        
        # Determine CC gain
        # Only turn 1 gets 2 CC, all other turns get 4 CC
        cc_gain = 2 if self.game_state.turn_number == 1 else 4
        
        # Gain CC (respects 7 CC cap)
        player.gain_cc(cc_gain)
        
        self.game_state.log_event(
            f"{player.name} gains {cc_gain} CC (now has {player.cc} CC)"
        )
        
        # Move to main phase
        self.game_state.phase = Phase.MAIN
    
    def end_turn(self) -> None:
        """
        End the current turn.
        
        Phase 3 - End of Turn:
        1. Resolve "at end of turn" effects
        2. Pass turn to opponent
        3. Increment turn number
        """
        player = self.game_state.get_active_player()
        self.game_state.phase = Phase.END
        
        self.game_state.log_event(f"{player.name} ends their turn")
        
        # Switch to opponent
        opponent = self.game_state.get_opponent_of_active()
        self.game_state.active_player_id = opponent.player_id
        self.game_state.turn_number += 1
        
        # Start next turn
        self.start_turn()
    
    # ========================================================================
    # CARD PLAYING
    # ========================================================================
    
    def can_play_card(self, card: Card, player: Player, **kwargs: Any) -> Tuple[bool, str]:
        """
        Check if a card can be played.
        
        Args:
            card: Card to play
            player: Player attempting to play
            **kwargs: Additional context (targets, etc.)
            
        Returns:
            Tuple of (can_play, reason)
        """
        # Must be in hand
        if card not in player.hand:
            return False, "Card not in hand"
        
        # Must be player's turn (except for Beary interrupt)
        if player != self.game_state.get_active_player():
            if card.name != "Beary":
                return False, "Not your turn"
        
        # Must be in Main phase (except for Beary)
        if self.game_state.phase != Phase.MAIN and card.name != "Beary":
            return False, "Can only play cards during Main phase"
        
        # Calculate cost (pass target_name for Copy if available)
        target_name = kwargs.get("target_name")
        cost = self.calculate_card_cost(card, player, target_name=target_name)
        
        # Check if player has enough CC
        if not player.has_cc(cost):
            return False, f"Not enough CC (need {cost}, have {player.cc})"
        
        # Check card-specific restrictions
        effects = EffectRegistry.get_effects(card)
        for effect in effects:
            if isinstance(effect, PlayEffect):
                if not effect.can_apply(self.game_state, player=player, **kwargs):
                    return False, f"{card.name} cannot be played now"
        
        return True, ""
    
    def calculate_card_cost(self, card: Card, player: Player, target_name: Optional[str] = None) -> int:
        """
        Calculate the actual cost to play a card after modifications.
        
        Args:
            card: Card being played
            player: Player playing the card
            target_name: Optional target card name (for Copy)
            
        Returns:
            Final cost in CC
        """
        from .rules.effects.action_effects import CopyEffect
        base_cost = card.cost
        
        # Special handling for cards with variable cost based on target (e.g., Copy)
        if card.has_effect_type(CopyEffect):
            # For Copy, the cost equals the cost of the card being copied
            target_card = None
            
            # If a specific target is named, use that
            if target_name:
                target_card = next((c for c in player.in_play if c.name == target_name), None)
            
            # Otherwise, use the lowest cost card in play (most conservative estimate)
            if target_card is None and player.in_play:
                target_card = min(player.in_play, key=lambda c: c.cost)
            
            if target_card:
                base_cost = target_card.cost
            else:
                base_cost = 0  # No valid targets, effect will fizzle
        
        # Apply cost modifications from continuous effects
        final_cost = base_cost
        
        # Check all cards in play for cost modification effects
        for card_in_play in self.game_state.get_all_cards_in_play():
            effects = EffectRegistry.get_effects(card_in_play)
            for effect in effects:
                if isinstance(effect, CostModificationEffect):
                    final_cost = effect.modify_card_cost(
                        card, final_cost, self.game_state, player
                    )
        
        # Also check the card itself for self-cost modifications (e.g., Dream)
        # This allows cards in hand to modify their own cost
        card_effects = EffectRegistry.get_effects(card)
        for effect in card_effects:
            if isinstance(effect, CostModificationEffect):
                final_cost = effect.modify_card_cost(
                    card, final_cost, self.game_state, player
                )
        
        return max(0, final_cost)  # Cost can't go below 0
    
    def play_card(self, player: Player, card: Card, **kwargs: Any) -> bool:
        """
        Play a card from hand.
        
        Args:
            player: Player playing the card
            card: Card to play
            **kwargs: Additional context (targets for effects, etc.)
            
        Returns:
            True if successful
        """
        # Validate
        can_play, reason = self.can_play_card(card, player, **kwargs)
        if not can_play:
            self.game_state.log_event(f"Cannot play {card.name}: {reason}")
            return False
        
        # Check if alternative cost was paid (handled by action_executor)
        alternative_cost_paid = kwargs.get("alternative_cost_paid", False)
        alternative_cost_card_name = kwargs.get("alternative_cost_card", None)
        
        if alternative_cost_paid and alternative_cost_card_name:
            # Alternative cost already paid by action_executor
            self.game_state.log_event(
                f"{player.name} plays {card.name} by sleeping {alternative_cost_card_name} (alternative cost)"
            )
        else:
            # Calculate and pay normal cost
            target_name = kwargs.get("target_name")
            cost = self.calculate_card_cost(card, player, target_name=target_name)
            if not player.spend_cc(cost):
                return False
            
            self.game_state.log_event(
                f"{player.name} plays {card.name} (cost: {cost} CC)"
            )
        
        # Remove from hand
        player.hand.remove(card)
        
        # Handle based on card type
        if card.card_type == CardType.TOY:
            # Toys go to in play
            card.zone = Zone.IN_PLAY
            card.controller = player.player_id  # Set controller when entering play
            player.in_play.append(card)
            
            # Trigger "when played" effects
            self._trigger_when_played_effects(card, player, **kwargs)
            
        elif card.card_type == CardType.ACTION:
            # Resolve the Action card's effect
            self._resolve_action_card(card, player, **kwargs)
            
            # Special handling for Copy - it transforms and stays in play
            if hasattr(card, '_is_transformed') and card._is_transformed:
                # Copy transformed into another card - stays IN_PLAY
                card.zone = Zone.IN_PLAY
                card.controller = player.player_id
                player.in_play.append(card)
            else:
                # Normal Actions go to sleep zone
                card.zone = Zone.SLEEP
                player.sleep_zone.append(card)
        
        # Check state-based actions
        self.check_state_based_actions()
        
        return True
    
    def _trigger_when_played_effects(self, card: Card, player: Player, **kwargs: Any) -> None:
        """Trigger effects that activate when a card is played."""
        effects = EffectRegistry.get_effects(card)
        for effect in effects:
            if isinstance(effect, TriggeredEffect):
                if effect.trigger == TriggerTiming.WHEN_PLAYED:
                    if effect.should_trigger(self.game_state, played_card=card):
                        effect.apply(self.game_state, player=player, **kwargs)
    
    def _resolve_action_card(self, card: Card, player: Player, **kwargs: Any) -> None:
        """Resolve an Action card's effect."""
        # Get and apply effects for all action cards (including Copy)
        effects = EffectRegistry.get_effects(card)
        for effect in effects:
            if isinstance(effect, PlayEffect):
                # Pass game_engine reference so effects can trigger other effects properly
                effect.apply(self.game_state, player=player, game_engine=self, **kwargs)
        
        self.game_state.log_event(f"{card.name} effect resolved")
    
    # ========================================================================
    # STAT CALCULATION (with continuous effects)
    # ========================================================================
    
    def get_card_stat(self, card: Card, stat_name: str) -> int:
        """
        Get a card's current stat value after applying all continuous effects.
        
        Args:
            card: Card to get stat for
            stat_name: Name of stat ("speed", "strength", "stamina")
            
        Returns:
            Modified stat value
        """
        # Get base value
        base_value = getattr(card, stat_name, 0)
        modified_value = base_value
        
        # Apply all continuous effects from cards in play
        for card_in_play in self.game_state.get_all_cards_in_play():
            effects = EffectRegistry.get_effects(card_in_play)
            for effect in effects:
                if isinstance(effect, ContinuousEffect):
                    modified_value = effect.modify_stat(
                        card, stat_name, modified_value, self.game_state
                    )
        
        return modified_value
    
    # ========================================================================
    # TUSSLE SYSTEM
    # ========================================================================
    
    def can_tussle(self, attacker: Card, defender: Optional[Card], player: Player) -> Tuple[bool, str]:
        """
        Check if a tussle can be initiated.
        
        Args:
            attacker: Attacking card
            defender: Defending card (None for direct attack)
            player: Player initiating tussle
            
        Returns:
            Tuple of (can_tussle, reason)
        """
        # Must be player's turn
        if player != self.game_state.get_active_player():
            return False, "Not your turn"
        
        # Must be in Main phase
        if self.game_state.phase != Phase.MAIN:
            return False, "Can only tussle during Main phase"
        
        # Attacker must be in play and controlled by player
        if attacker not in player.in_play:
            return False, "Attacker not in play"
        
        # Check if attacker can tussle (e.g., Archer can't, Raggy can't on Turn 1)
        effects = EffectRegistry.get_effects(attacker)
        for effect in effects:
            if hasattr(effect, 'can_tussle'):
                if not effect.can_tussle(self.game_state):
                    return False, f"{attacker.name} cannot tussle"
        
        # Calculate tussle cost
        cost = self.calculate_tussle_cost(attacker, player)
        if not player.has_cc(cost):
            return False, f"Not enough CC for tussle (need {cost}, have {player.cc})"
        
        # If direct attack
        if defender is None:
            opponent = self.game_state.get_opponent(player.player_id)
            
            # Opponent must have no cards in play
            if opponent.has_cards_in_play():
                return False, "Opponent has cards in play - must target one"
            
            # Opponent must have cards in hand
            if len(opponent.hand) == 0:
                return False, "Opponent has no cards in hand"
            
            # Max 2 direct attacks per turn
            if player.direct_attacks_this_turn >= 2:
                return False, "Already made 2 direct attacks this turn"
        else:
            # Defender must be opponent's card in play
            opponent = self.game_state.get_opponent(player.player_id)
            if defender not in opponent.in_play:
                return False, "Defender not in opponent's play area"
        
        return True, ""
    
    def calculate_tussle_cost(self, attacker: Card, player: Player) -> int:
        """
        Calculate the cost to initiate a tussle.
        
        Base cost is 2 CC, modified by:
        - Wizard: Tussles cost 1
        - Raggy: This card's tussles cost 0
        
        Args:
            attacker: Card initiating tussle
            player: Player controlling the attacker
            
        Returns:
            Final tussle cost
        """
        base_cost = 2
        costs = [base_cost]
        
        # Apply cost modifications
        for card_in_play in player.in_play:
            effects = EffectRegistry.get_effects(card_in_play)
            for effect in effects:
                if isinstance(effect, CostModificationEffect):
                    # Check if this is the attacker for Raggy
                    if card_in_play == attacker:
                        modified_cost = effect.modify_tussle_cost(
                            base_cost, self.game_state, player
                        )
                        costs.append(modified_cost)
                    # Wizard affects all tussles
                    elif card_in_play.name == "Wizard":
                        modified_cost = effect.modify_tussle_cost(
                            base_cost, self.game_state, player
                        )
                        costs.append(modified_cost)
        
        # Use lowest cost (per rules: modifiers don't stack beyond lowest)
        return min(costs)
    
    def initiate_tussle(self, attacker: Card, defender: Optional[Card], 
                       player: Player) -> tuple[bool, Optional[str]]:
        """
        Initiate a tussle.
        
        Args:
            attacker: Attacking card
            defender: Defending card (None for direct attack)
            player: Player initiating tussle
            
        Returns:
            Tuple of (success, sleeped_from_hand_name)
            - success: True if tussle completed successfully
            - sleeped_from_hand_name: Name of card sleeped from hand (direct attack only)
        """
        # Validate
        can_tussle, reason = self.can_tussle(attacker, defender, player)
        if not can_tussle:
            self.game_state.log_event(f"Cannot tussle: {reason}")
            return (False, None)
        
        # Calculate and pay cost
        cost = self.calculate_tussle_cost(attacker, player)
        if not player.spend_cc(cost):
            return (False, None)
        
        # Check for Beary interrupt
        opponent = self.game_state.get_opponent(player.player_id)
        cancelled = self._check_beary_cancel(opponent)
        
        if cancelled:
            self.game_state.log_event("Tussle cancelled by Beary!")
            # Cost is NOT refunded
            return (False, None)
        
        # Execute tussle
        sleeped_from_hand = None
        if defender is None:
            sleeped_from_hand = self._execute_direct_attack(attacker, player, opponent)
        else:
            self._execute_tussle(attacker, defender, player, opponent)
        
        # Check state-based actions
        self.check_state_based_actions()
        
        return (True, sleeped_from_hand)
    
    def _check_beary_cancel(self, opponent: Player) -> bool:
        """
        Check if opponent can play Beary to cancel the tussle.
        
        In a real implementation, this would prompt the opponent.
        For now, we'll return False (no cancel).
        
        Args:
            opponent: Opponent who might have Beary
            
        Returns:
            True if tussle was cancelled
        """
        # This would require user interaction
        # For automated testing, return False
        # TODO: Implement player choice mechanism
        return False
    
    def _execute_direct_attack(self, attacker: Card, player: Player, 
                               opponent: Player) -> Optional[str]:
        """
        Execute a direct attack (sleep random card from opponent's hand).
        
        Args:
            attacker: Attacking card
            player: Attacking player
            opponent: Defending player
            
        Returns:
            Name of the card sleeped from hand, or None if no card was sleeped
        """
        player.direct_attacks_this_turn += 1
        
        # Sleep random card from opponent's hand
        if opponent.hand:
            target = random.choice(opponent.hand)
            # FIX (Issue #107): Sleep to owner's zone, not controller's zone
            target_owner = self.game_state.players[target.owner]
            target_owner.sleep_card(target)
            
            self.game_state.log_event(
                f"{player.name}'s {attacker.name} direct attack! "
                f"Sleeped {target.name} from {opponent.name}'s hand "
                f"(direct attack {player.direct_attacks_this_turn}/2)"
            )
            
            # Cards sleeped from hand do NOT trigger "when sleeped" effects
            return target.name
        
        return None
    
    def _execute_tussle(self, attacker: Card, defender: Card, 
                       attacker_player: Player, defender_player: Player) -> None:
        """
        Execute a tussle between two cards.
        
        Args:
            attacker: Attacking card
            defender: Defending card
            attacker_player: Player controlling attacker
            defender_player: Player controlling defender
        """
        self.game_state.log_event(
            f"{attacker_player.name}'s {attacker.name} tussles "
            f"{defender_player.name}'s {defender.name}"
        )
        
        # Check for Knight auto-win
        attacker_effects = EffectRegistry.get_effects(attacker)
        for effect in attacker_effects:
            if hasattr(effect, 'wins_tussle'):
                if effect.wins_tussle(self.game_state, defender):
                    self.game_state.log_event(
                        f"{attacker.name} auto-wins! {defender.name} is sleeped."
                    )
                    # Sleep to owner's zone (not controller's)
                    defender_owner = self.game_state.players[defender.owner]
                    self._sleep_card(defender, defender_owner, was_in_play=True)
                    return
        
        # Calculate speeds (with turn bonus for attacker)
        attacker_speed = self.get_card_stat(attacker, "speed") + 1  # Turn bonus
        defender_speed = self.get_card_stat(defender, "speed")
        
        # Calculate strengths
        attacker_strength = self.get_card_stat(attacker, "strength")
        defender_strength = self.get_card_stat(defender, "strength")
        
        self.game_state.log_event(
            f"Speed: {attacker.name} {attacker_speed} vs {defender.name} {defender_speed}"
        )
        self.game_state.log_event(
            f"Strength: {attacker.name} {attacker_strength} vs {defender.name} {defender_strength}"
        )
        
        # Determine strike order
        if attacker_speed > defender_speed:
            # Attacker strikes first
            defender.current_stamina -= attacker_strength
            self.game_state.log_event(
                f"{attacker.name} strikes first! {defender.name} takes {attacker_strength} damage "
                f"({defender.current_stamina}/{defender.stamina} stamina)"
            )
            
            if defender.current_stamina <= 0:
                self.game_state.log_event(f"{defender.name} is sleeped!")
                # Sleep to owner's zone (not controller's)
                defender_owner = self.game_state.players[defender.owner]
                self._sleep_card(defender, defender_owner, was_in_play=True)
            else:
                # Defender strikes back
                attacker.current_stamina -= defender_strength
                self.game_state.log_event(
                    f"{defender.name} strikes back! {attacker.name} takes {defender_strength} damage "
                    f"({attacker.current_stamina}/{attacker.stamina} stamina)"
                )
                
                if attacker.current_stamina <= 0:
                    self.game_state.log_event(f"{attacker.name} is sleeped!")
                    # Sleep to owner's zone (not controller's)
                    attacker_owner = self.game_state.players[attacker.owner]
                    self._sleep_card(attacker, attacker_owner, was_in_play=True)
        
        elif defender_speed > attacker_speed:
            # Defender strikes first
            attacker.current_stamina -= defender_strength
            self.game_state.log_event(
                f"{defender.name} strikes first! {attacker.name} takes {defender_strength} damage "
                f"({attacker.current_stamina}/{attacker.stamina} stamina)"
            )
            
            if attacker.current_stamina <= 0:
                self.game_state.log_event(f"{attacker.name} is sleeped!")
                # Sleep to owner's zone (not controller's)
                attacker_owner = self.game_state.players[attacker.owner]
                self._sleep_card(attacker, attacker_owner, was_in_play=True)
            else:
                # Attacker strikes back
                defender.current_stamina -= attacker_strength
                self.game_state.log_event(
                    f"{attacker.name} strikes back! {defender.name} takes {attacker_strength} damage "
                    f"({defender.current_stamina}/{defender.stamina} stamina)"
                )
                
                if defender.current_stamina <= 0:
                    self.game_state.log_event(f"{defender.name} is sleeped!")
                    # Sleep to owner's zone (not controller's)
                    defender_owner = self.game_state.players[defender.owner]
                    self._sleep_card(defender, defender_owner, was_in_play=True)
        
        else:
            # Tied speed - simultaneous strikes
            attacker.current_stamina -= defender_strength
            defender.current_stamina -= attacker_strength
            
            self.game_state.log_event(
                f"Simultaneous strikes! {attacker.name}: {attacker.current_stamina}/{attacker.stamina}, "
                f"{defender.name}: {defender.current_stamina}/{defender.stamina}"
            )
            
            if attacker.current_stamina <= 0:
                self.game_state.log_event(f"{attacker.name} is sleeped!")
                # Sleep to owner's zone (not controller's)
                attacker_owner = self.game_state.players[attacker.owner]
                self._sleep_card(attacker, attacker_owner, was_in_play=True)
            
            if defender.current_stamina <= 0:
                self.game_state.log_event(f"{defender.name} is sleeped!")
                # Sleep to owner's zone (not controller's)
                defender_owner = self.game_state.players[defender.owner]
                self._sleep_card(defender, defender_owner, was_in_play=True)
    
    def _sleep_card(self, card: Card, player: Player, was_in_play: bool) -> None:
        """
        Sleep a card and trigger "when sleeped" effects.
        
        Args:
            card: Card to sleep
            player: Player who owns the card
            was_in_play: Whether card was in play (vs sleeped from hand)
        """
        # Move to sleep zone
        player.sleep_card(card)
        
        # Trigger "when sleeped" effects (only if was in play)
        if was_in_play:
            effects = EffectRegistry.get_effects(card)
            for effect in effects:
                if isinstance(effect, TriggeredEffect):
                    if effect.trigger == TriggerTiming.WHEN_SLEEPED:
                        if effect.should_trigger(
                            self.game_state, 
                            sleeped_card=card,
                            was_in_play=was_in_play
                        ):
                            effect.apply(self.game_state, sleeped_card=card, game_engine=self)
    
    # ========================================================================
    # STATE-BASED ACTIONS
    # ========================================================================
    
    def check_state_based_actions(self) -> None:
        """
        Check and apply state-based actions.
        
        State-based actions:
        - Sleep any Toy with stamina <= 0
        - Check for victory condition
        """
        # Check for cards with 0 or less stamina
        for player in self.game_state.players.values():
            cards_to_sleep = []
            for card in player.in_play:
                if hasattr(card, 'current_stamina'):
                    if card.current_stamina <= 0:
                        cards_to_sleep.append(card)
            
            for card in cards_to_sleep:
                # Sleep to owner's zone (not controller's)
                owner = self.game_state.players[card.owner]
                self._sleep_card(card, owner, was_in_play=True)
        
        # Check victory
        self.game_state.check_victory()
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def get_card_controller(self, card: Card) -> Optional[Player]:
        """
        Get the player who controls a card.
        
        Args:
            card: Card to check
            
        Returns:
            Player controlling the card, or None
        """
        for player in self.game_state.players.values():
            if card in player.in_play:
                return player
        return None
    
    def get_card_owner(self, card: Card) -> Optional[Player]:
        """
        Get the player who owns a card (original deck).
        
        Args:
            card: Card to check
            
        Returns:
            Player who owns the card
        """
        for player in self.game_state.players.values():
            if card in player.hand or card in player.in_play or card in player.sleep_zone:
                return player
        return None
