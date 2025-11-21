"""
Action validation for GGLTCG.

This module provides the ActionValidator class which serves as the single
source of truth for determining what actions are valid in any game state.

This eliminates the code duplication that previously existed between:
- GET /valid-actions endpoint
- POST /ai-turn endpoint
- Manual action validation in routes

Key responsibilities:
1. Determine which cards can be played
2. Find valid targets for card effects
3. Check alternative cost availability
4. Validate tussle actions
5. Build ValidAction objects with all necessary metadata
"""

import logging
from typing import List, Optional, Tuple
from dataclasses import dataclass

from game_engine.models.card import CardType
from game_engine.models.game_state import GameState
from game_engine.models.player import Player
from game_engine.rules.effects import EffectRegistry
from game_engine.rules.effects.base_effect import PlayEffect
from game_engine.rules.tussle_resolver import TussleResolver

logger = logging.getLogger(__name__)


@dataclass
class ValidAction:
    """
    Represents a valid action a player can take.
    
    This is returned by ActionValidator and used by both the API
    (for human players to choose from) and the AI (to select the best action).
    """
    action_type: str  # "play_card", "tussle", "end_turn"
    description: str  # Human-readable description
    card_id: Optional[str] = None  # Card being played/tussled with
    card_name: Optional[str] = None  # For display
    cost_cc: Optional[int] = None  # CC cost
    target_options: Optional[List[str]] = None  # Valid target card IDs
    max_targets: int = 1  # Maximum targets to select
    min_targets: int = 1  # Minimum targets required
    alternative_cost_available: bool = False  # Can use alternative cost?
    alternative_cost_options: Optional[List[str]] = None  # Cards that can be used for alt cost


class ActionValidator:
    """
    Validates game actions and provides lists of valid actions.
    
    This class consolidates all action validation logic that was previously
    duplicated across multiple endpoints. It serves as the single source of
    truth for what actions are valid.
    
    Usage:
        validator = ActionValidator(game_engine)
        valid_actions = validator.get_valid_actions(player_id)
        
        # For AI with defensive filtering
        valid_actions = validator.get_valid_actions(player_id, filter_for_ai=True)
    """
    
    def __init__(self, game_engine):
        """
        Initialize the validator.
        
        Args:
            game_engine: The GameEngine instance to validate against
        """
        self.engine = game_engine
        self.game_state = game_engine.game_state
    
    def get_valid_actions(
        self,
        player_id: str,
        filter_for_ai: bool = False
    ) -> List[ValidAction]:
        """
        Get all valid actions for a player.
        
        Args:
            player_id: The player to get actions for
            filter_for_ai: If True, filter out actions that are strategically
                          bad (e.g., guaranteed-loss tussles). Used for AI.
        
        Returns:
            List of ValidAction objects representing all actions the player
            can currently take
        """
        player = self.game_state.players.get(player_id)
        if player is None:
            return []
        
        valid_actions = []
        
        # Only generate actions if it's the player's turn
        if self.game_state.active_player_id != player_id:
            return []
        
        # Can always end turn
        valid_actions.append(
            ValidAction(
                action_type="end_turn",
                description="End your turn"
            )
        )
        
        # Get valid card plays
        valid_actions.extend(self._get_valid_card_plays(player))
        
        # Get valid tussles
        valid_actions.extend(self._get_valid_tussles(player, filter_for_ai))
        
        # Sort actions to prioritize certain types
        if filter_for_ai:
            # For AI: prioritize tussles, then by cost (lowest first)
            valid_actions.sort(
                key=lambda a: (
                    a.action_type != "tussle",
                    a.cost_cc if a.cost_cc is not None else 999
                )
            )
        
        return valid_actions
    
    def _get_valid_card_plays(self, player: Player) -> List[ValidAction]:
        """
        Get all valid card play actions for a player.
        
        Args:
            player: The player to check
        
        Returns:
            List of ValidAction objects for playing cards
        """
        valid_actions = []
        
        for card in player.hand:
            can_play, reason = self.engine.can_play_card(card, player)
            cost = self.engine.calculate_card_cost(card, player)
            
            # Check for alternative cost
            alternative_cost_available = False
            alternative_cost_options = None
            
            if card.name == "Ballaber":
                # Can sleep any card in hand or in play except Ballaber itself
                alt_cards = [
                    c for c in (player.in_play + (player.hand or []))
                    if c.name != "Ballaber"
                ]
                if alt_cards:
                    alternative_cost_available = True
                    alternative_cost_options = [c.id for c in alt_cards]
            
            # Allow card if it can be played normally OR if alternate cost is available
            if not can_play and not alternative_cost_available:
                continue
            
            # Check if card's effect requires targets
            target_info = self._get_target_info(card, player)
            
            # Build description
            desc = f"Play {card.name} (Cost: {cost} CC"
            if alternative_cost_available:
                desc += " or sleep a card"
            
            # Special handling for Copy - cost varies by target
            if card.name == "Copy" and target_info["target_options"]:
                valid_actions.append(
                    ValidAction(
                        action_type="play_card",
                        card_id=card.id,
                        card_name=card.name,
                        cost_cc=cost,
                        target_options=target_info["target_options"],
                        max_targets=target_info["max_targets"],
                        min_targets=target_info["min_targets"],
                        description=f"Play {card.name} (select target - cost varies)"
                    )
                )
            elif target_info["requires_targets"] and target_info["target_options"]:
                # Card requires target selection and targets are available
                target_desc = (
                    f"select up to {target_info['max_targets']} targets"
                    if target_info['max_targets'] > 1
                    else "select target"
                )
                desc += f", {target_desc}"
                valid_actions.append(
                    ValidAction(
                        action_type="play_card",
                        card_id=card.id,
                        card_name=card.name,
                        cost_cc=cost,
                        target_options=target_info["target_options"],
                        max_targets=target_info["max_targets"],
                        min_targets=target_info["min_targets"],
                        alternative_cost_available=alternative_cost_available,
                        alternative_cost_options=alternative_cost_options,
                        description=desc + ")"
                    )
                )
            elif target_info["requires_targets"] and not target_info["target_options"]:
                # Card requires targets but none available
                if target_info["min_targets"] == 0:
                    # Can still play without targets
                    desc += ", no targets available)"
                    valid_actions.append(
                        ValidAction(
                            action_type="play_card",
                            card_id=card.id,
                            card_name=card.name,
                            cost_cc=cost,
                            alternative_cost_available=alternative_cost_available,
                            alternative_cost_options=alternative_cost_options,
                            description=desc
                        )
                    )
                # Otherwise skip - can't play without required targets
            else:
                # No targets required
                desc += ")"
                valid_actions.append(
                    ValidAction(
                        action_type="play_card",
                        card_id=card.id,
                        card_name=card.name,
                        cost_cc=cost,
                        alternative_cost_available=alternative_cost_available,
                        alternative_cost_options=alternative_cost_options,
                        description=desc
                    )
                )
        
        return valid_actions
    
    def _get_target_info(self, card, player: Player) -> dict:
        """
        Get target information for a card's effect.
        
        Args:
            card: The card to check
            player: The player who owns the card
        
        Returns:
            Dictionary with keys:
            - requires_targets: bool
            - target_options: List[str] or None (card IDs)
            - max_targets: int
            - min_targets: int
        """
        target_options = None
        requires_targets = False
        max_targets = 1
        min_targets = 1
        
        # Get all effects for this card
        effects = EffectRegistry.get_effects(card)
        logger.debug(f"Card {card.name}: Found {len(effects)} effects")
        
        for effect in effects:
            logger.debug(f"  Effect: {type(effect).__name__}, is PlayEffect: {isinstance(effect, PlayEffect)}")
            if isinstance(effect, PlayEffect):
                logger.debug(f"  requires_targets: {effect.requires_targets()}")
                
            if isinstance(effect, PlayEffect) and effect.requires_targets():
                max_targets = effect.get_max_targets()
                min_targets = effect.get_min_targets()
                valid_targets = effect.get_valid_targets(self.game_state, player)
                
                logger.debug(
                    f"Card {card.name}: requires_targets={effect.requires_targets()}, "
                    f"valid_targets={[t.name for t in valid_targets] if valid_targets else 'None'}"
                )
                
                if valid_targets:
                    target_options = [t.id for t in valid_targets]
                    logger.debug(f"Card {card.name}: target_options set to {len(target_options)} IDs")
                
                # Mark as requiring targets only if valid targets exist or min_targets == 0
                requires_targets = bool(valid_targets) or min_targets == 0
                break
        
        return {
            "requires_targets": requires_targets,
            "target_options": target_options,
            "max_targets": max_targets,
            "min_targets": min_targets
        }
    
    def _get_valid_tussles(
        self,
        player: Player,
        filter_for_ai: bool = False
    ) -> List[ValidAction]:
        """
        Get all valid tussle actions for a player.
        
        Args:
            player: The player to check
            filter_for_ai: If True, filter out guaranteed-loss tussles
        
        Returns:
            List of ValidAction objects for tussles
        """
        valid_actions = []
        opponent = self.game_state.get_opponent(player.player_id)
        
        for card in player.in_play:
            if card.card_type != CardType.TOY:
                continue
            
            # Check direct attack (only when opponent has no cards in play)
            if not opponent.has_cards_in_play():
                can_attack, _ = self.engine.can_tussle(card, None, player)
                if can_attack:
                    cost = self.engine.calculate_tussle_cost(card, player)
                    valid_actions.append(
                        ValidAction(
                            action_type="tussle",
                            card_id=card.id,
                            card_name=card.name,
                            cost_cc=cost,
                            target_options=["direct_attack"],
                            description=f"{card.name} direct attack (Cost: {cost} CC)"
                        )
                    )
            
            # Check each potential defender
            if opponent:
                for defender in opponent.in_play:
                    can_tussle, _ = self.engine.can_tussle(card, defender, player)
                    if not can_tussle:
                        continue
                    
                    # For AI, filter out guaranteed losses
                    if filter_for_ai:
                        predicted = TussleResolver.predict_winner(
                            self.game_state, card, defender
                        )
                        
                        logger.debug(
                            f"Tussle prediction: {card.name} vs {defender.name} = {predicted} "
                            f"(attacker {card.speed}/{card.strength}/{card.stamina} vs "
                            f"defender {defender.speed}/{defender.strength}/{defender.stamina})"
                        )
                        
                        if predicted == "defender":
                            logger.debug(f"  → Skipping losing tussle for AI")
                            continue
                    
                    cost = self.engine.calculate_tussle_cost(card, player)
                    valid_actions.append(
                        ValidAction(
                            action_type="tussle",
                            card_id=card.id,
                            card_name=card.name,
                            cost_cc=cost,
                            target_options=[defender.id],
                            description=f"{card.name} tussle {defender.name} (Cost: {cost} CC)"
                        )
                    )
        
        return valid_actions
