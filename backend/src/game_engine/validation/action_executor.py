"""
Action execution logic for GGLTCG.

This module provides the ActionExecutor class which consolidates all action
execution logic in a single place, eliminating duplication between human and
AI player paths.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from game_engine.models.card import CardType, Zone
from game_engine.models.game_state import GameState
from game_engine.models.player import Player
from game_engine.models.card import Card
from game_engine.rules.effects.continuous_effects import BallaberCostEffect

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Result of executing an action."""
    success: bool
    message: str
    description: str  # Play-by-play description
    cost: int = 0
    winner: Optional[str] = None
    target_info: str = ""  # Additional target info for response message


class ActionExecutor:
    """
    Executes validated game actions.
    
    This class consolidates execution logic that was previously duplicated
    between the human player (play_card endpoint) and AI player (ai_take_turn
    endpoint) code paths.
    
    All action execution goes through this class to ensure consistent behavior.
    """
    
    def __init__(self, game_engine: Any):
        """
        Initialize the ActionExecutor.
        
        Args:
            game_engine: The GameEngine instance for this game
        """
        self.engine = game_engine
        self.game_state: GameState = game_engine.game_state
    
    def execute_play_card(
        self,
        player_id: str,
        card_id: str,
        target_card_id: Optional[str] = None,
        target_card_ids: Optional[List[str]] = None,
        alternative_cost_card_id: Optional[str] = None
    ) -> ExecutionResult:
        """
        Execute a play card action.
        
        Args:
            player_id: ID of player playing the card
            card_id: ID of card to play
            target_card_id: Optional single target card ID
            target_card_ids: Optional multiple target card IDs
            alternative_cost_card_id: Optional card ID to use for alternative cost
            
        Returns:
            ExecutionResult with success status, message, and description
            
        Raises:
            ValueError: If player/card not found or invalid targets
        """
        # Get player
        player = self.game_state.players.get(player_id)
        if player is None:
            raise ValueError(f"Player {player_id} not found")
        
        # Find card in hand
        card = next((c for c in player.hand if c.id == card_id), None)
        if card is None:
            raise ValueError(f"Card with ID '{card_id}' not found in hand")
        
        # Handle alternative cost and calculate cost
        alt_cost_kwargs, cost = self._handle_alternative_cost(
            card, alternative_cost_card_id, player
        )
        
        # Handle targets
        target_kwargs = self._handle_targets(target_card_id, target_card_ids)
        
        # Merge kwargs
        kwargs = {**alt_cost_kwargs, **target_kwargs}
        
        # Log target selection for debugging
        if kwargs.get("target"):
            logger.info(f"Playing {card.name} with target: {kwargs['target'].name} (ID: {target_card_id})")
        
        # Execute the play
        success = False
        if kwargs.get("alternative_cost_paid"):
            # Alternative cost path: manually handle card play
            success = self._execute_alternative_cost_play(player, card, kwargs)
        else:
            # Normal play_card flow
            success = self.engine.play_card(player, card, **kwargs)
        
        if not success:
            return ExecutionResult(
                success=False,
                message="Failed to play card (insufficient CC or invalid target)",
                description="",
                cost=cost
            )
        
        # Check state-based actions
        self.engine.check_state_based_actions()
        
        # Build description
        description = self._build_play_card_description(card, cost, kwargs)
        
        # Build target info for response message
        target_info = self._build_target_info(card, kwargs)
        
        # Check for victory
        winner = self.game_state.check_victory()
        
        return ExecutionResult(
            success=True,
            message=f"Successfully played {card.name}{target_info}",
            description=description,
            cost=cost,
            winner=winner,
            target_info=target_info
        )
    
    def execute_tussle(
        self,
        player_id: str,
        attacker_id: str,
        defender_id: Optional[str] = None
    ) -> ExecutionResult:
        """
        Execute a tussle action.
        
        Args:
            player_id: ID of player initiating tussle
            attacker_id: ID of attacking card
            defender_id: Optional ID of defending card (None for direct attack)
            
        Returns:
            ExecutionResult with success status, message, and description
            
        Raises:
            ValueError: If player/cards not found
        """
        # Get player
        player = self.game_state.players.get(player_id)
        if player is None:
            raise ValueError(f"Player {player_id} not found")
        
        # Find attacker in player's in_play zone
        attacker = next((c for c in player.in_play if c.id == attacker_id), None)
        if attacker is None:
            raise ValueError(f"Attacker card with ID '{attacker_id}' not found in play")
        
        # Find defender if specified
        defender = None
        if defender_id:
            defender = self.game_state.find_card_by_id(defender_id)
            if defender is None:
                # Provide detailed diagnostic information
                opponent = self.game_state.get_opponent(player.player_id)
                opponent_card_ids = [c.id for c in (opponent.hand + opponent.in_play + opponent.sleep_zone)]
                player_card_ids = [c.id for c in (player.hand + player.in_play + player.sleep_zone)]
                
                logger.error(
                    f"Defender card lookup failed:\n"
                    f"  Requested ID: {defender_id}\n"
                    f"  Opponent's cards ({len(opponent_card_ids)}): {opponent_card_ids}\n"
                    f"  Player's cards ({len(player_card_ids)}): {player_card_ids}\n"
                    f"  Game state: turn={self.game_state.turn_number}, phase={self.game_state.phase.value}"
                )
                
                raise ValueError(
                    f"Defender card with ID '{defender_id}' not found. "
                    f"Card may have been moved or removed from play."
                )
        
        # Calculate cost before tussle
        cost = self.engine.calculate_tussle_cost(attacker, player)
        
        # Execute tussle
        success = self.engine.initiate_tussle(attacker, defender, player)
        
        if not success:
            return ExecutionResult(
                success=False,
                message="Failed to initiate tussle",
                description="",
                cost=cost
            )
        
        # Check state-based actions
        self.engine.check_state_based_actions()
        
        # Build description
        target_desc = defender.name if defender else "opponent directly"
        description = f"Spent {cost} CC for {attacker.name} to tussle {target_desc}"
        
        # Check for victory
        winner = self.game_state.check_victory()
        
        return ExecutionResult(
            success=True,
            message=f"Tussle: {attacker.name} vs {target_desc}",
            description=description,
            cost=cost,
            winner=winner
        )
    
    # ========================================================================
    # Private Helper Methods
    # ========================================================================
    
    def _handle_alternative_cost(
        self,
        card: Card,
        alternative_cost_card_id: Optional[str],
        player: Player
    ) -> tuple[Dict[str, Any], int]:
        """
        Handle alternative cost for cards like Ballaber.
        
        Returns:
            tuple: (kwargs dict with alternative cost info, effective cost)
        """
        kwargs = {}
        
        if alternative_cost_card_id and card.has_effect_type(BallaberCostEffect):
            # Find card to sleep (can be in hand or play)
            card_to_sleep = next(
                (c for c in (player.in_play + (player.hand or []))
                 if c.id == alternative_cost_card_id),
                None
            )
            if card_to_sleep is None:
                raise ValueError(
                    f"Alternative cost card with ID '{alternative_cost_card_id}' not found"
                )
            # Sleep the card via game engine to trigger effects
            was_in_play = card_to_sleep in player.in_play
            owner = self.game_state.get_card_owner(card_to_sleep)
            self.engine._sleep_card(card_to_sleep, owner, was_in_play=was_in_play)
            kwargs["alternative_cost_paid"] = True
            kwargs["alternative_cost_card"] = card_to_sleep.name
            cost = 0
        else:
            # Calculate normal cost
            cost = self.engine.calculate_card_cost(card, player)
        
        return kwargs, cost
    
    def _handle_targets(
        self,
        target_card_id: Optional[str],
        target_card_ids: Optional[List[str]]
    ) -> Dict[str, Any]:
        """
        Find and validate target cards by their IDs.
        
        Returns:
            dict: kwargs with 'target', 'target_name', and/or 'targets'
        """
        kwargs = {}
        
        # Single target
        if target_card_id:
            target = self.game_state.find_card_by_id(target_card_id)
            if target is None:
                # Provide detailed diagnostic information for card lookup failures
                all_card_ids = []
                for p in self.game_state.players.values():
                    all_card_ids.extend([c.id for c in (p.hand + p.in_play + p.sleep_zone)])
                
                logger.error(
                    f"Target card lookup failed:\n"
                    f"  Requested ID: {target_card_id}\n"
                    f"  All card IDs in game ({len(all_card_ids)}): {all_card_ids}\n"
                    f"  Game state: turn={self.game_state.turn_number}, phase={self.game_state.phase.value}"
                )
                
                raise ValueError(
                    f"Target card with ID '{target_card_id}' not found. "
                    f"Card may have been moved or removed."
                )
            kwargs["target"] = target
            kwargs["target_name"] = target.name  # For Copy card
            # Also provide as single-element list for effects that expect 'targets'
            kwargs["targets"] = [target]
        
        # Multiple targets
        if target_card_ids:
            targets = []
            for card_id in target_card_ids:
                target = self.game_state.find_card_by_id(card_id)
                if target is None:
                    # Provide detailed diagnostic information
                    all_card_ids = []
                    for p in self.game_state.players.values():
                        all_card_ids.extend([c.id for c in (p.hand + p.in_play + p.sleep_zone)])
                    
                    logger.error(
                        f"Multi-target card lookup failed:\n"
                        f"  Requested ID: {card_id}\n"
                        f"  All card IDs in game ({len(all_card_ids)}): {all_card_ids}\n"
                        f"  Game state: turn={self.game_state.turn_number}, phase={self.game_state.phase.value}"
                    )
                    
                    raise ValueError(
                        f"Target card with ID '{card_id}' not found. "
                        f"Card may have been moved or removed."
                    )
                targets.append(target)
            kwargs["targets"] = targets
        
        return kwargs
    
    def _execute_alternative_cost_play(
        self,
        player: Player,
        card: Card,
        kwargs: Dict[str, Any]
    ) -> bool:
        """
        Execute card play with alternative cost.
        
        Alternative cost was already paid (card already slept), so we just need
        to pay 0 CC and move the card to the appropriate zone.
        
        Returns:
            bool: True if successful
        """
        # Pay 0 CC (should always succeed)
        if not player.spend_cc(0):
            return False
        
        # Remove from hand
        player.hand.remove(card)
        
        # Toys go to in play
        if card.card_type == CardType.TOY:
            card.zone = Zone.IN_PLAY
            player.in_play.append(card)
        elif card.card_type == CardType.ACTION:
            # Actions resolve and go to sleep zone
            self.engine._resolve_action_card(card, player, **kwargs)
            card.zone = Zone.SLEEP
            player.sleep_zone.append(card)
        
        return True
    
    def _build_play_card_description(
        self,
        card: Card,
        cost: int,
        kwargs: Dict[str, Any]
    ) -> str:
        """
        Build a detailed description of playing a card.
        
        Includes cost, effect text, and target-specific details.
        """
        # Base description
        if kwargs.get("alternative_cost_paid"):
            description = f"Played {card.name} by sleeping {kwargs['alternative_cost_card']}"
        else:
            description = f"Spent {cost} CC to play {card.name}"
        
        # Add effect text for Action cards
        if card.is_action():
            description += f" ({card.effect_text})"
            
            # Add target-specific details
            from ..rules.effects.action_effects import UnsleepEffect
            if card.has_effect_type(UnsleepEffect) and kwargs.get("target") and card.has_effect_type(UnsleepEffect):
                target_card = kwargs["target"]
                description += f". Unslept {target_card.name}"
            elif card.has_effect_type(UnsleepEffect) and kwargs.get("targets"):
                target_names = [t.name for t in kwargs["targets"]]
                description += f". Unslept {', '.join(target_names)}"
            from ..rules.effects.action_effects import CopyEffect
            elif card.has_effect_type(CopyEffect) and kwargs.get("target"):
                target_card = kwargs["target"]
                description += f". Copied {target_card.name}"
            from ..rules.effects.action_effects import TwistEffect
            elif card.has_effect_type(TwistEffect) and kwargs.get("target"):
                target_card = kwargs["target"]
                description += f". Took control of {target_card.name}"
        
        # For cards with alternative cost (e.g., Ballaber)
        if card.has_effect_type(BallaberCostEffect) and kwargs.get("alternative_cost_paid"):
            alt_card = kwargs["alternative_cost_card"]
            description += f". Slept {alt_card} for alternative cost"
        
        return description
    
    def _build_target_info(
        self,
        card: Card,
        kwargs: Dict[str, Any]
    ) -> str:
        """
        Build target info string for response message.
        
        Returns:
            str: Target info like " (unslept Knight)" or ""
        """
        from ..rules.effects.action_effects import UnsleepEffect
        if card.has_effect_type(UnsleepEffect) and kwargs.get("target"):
            return f" (unslept {kwargs['target'].name})"
        elif card.has_effect_type(UnsleepEffect) and kwargs.get("targets"):
            target_names = [t.name for t in kwargs["targets"]]
            return f" (unslept {', '.join(target_names)})"
        from ..rules.effects.action_effects import CopyEffect
        elif card.has_effect_type(CopyEffect) and kwargs.get("target"):
            return f" (copied {kwargs['target'].name})"
        from ..rules.effects.action_effects import TwistEffect
        elif card.has_effect_type(TwistEffect) and kwargs.get("target"):
            return f" (took control of {kwargs['target'].name})"
        return ""
