"""
Player action API routes.

Endpoints for playing cards, initiating tussles, ending turns, etc.
"""

import logging
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List

from api.schemas import (
    PlayCardRequest,
    TussleRequest,
    EndTurnRequest,
    ActivateAbilityRequest,
    ActionResponse,
    ValidActionsResponse,
    ValidAction,
)
from api.game_service import get_game_service
from game_engine.models.card import CardType
from game_engine.ai.llm_player import get_ai_player
from game_engine.rules.tussle_resolver import TussleResolver
from game_engine.validation import ActionValidator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/games", tags=["actions"])


# ============================================================================
# Helper Functions (DRY - Don't Repeat Yourself)
# ============================================================================
# These functions eliminate code duplication between human and AI player paths

def handle_alternative_cost(
    card: Any,
    alternative_cost_card_id: str | None,
    player: Any,
    game_state: Any,
    engine: Any
) -> tuple[Dict[str, Any], int]:
    """
    Handle alternative cost for cards like Ballaber.
    
    Returns:
        tuple: (kwargs dict with alternative cost info, effective cost)
    """
    kwargs = {}
    
    if alternative_cost_card_id and card.name == "Ballaber":
        # Find card to sleep (can be in hand or play, but not Ballaber itself)
        card_to_sleep = next(
            (c for c in (player.in_play + (player.hand or []))
             if c.id == alternative_cost_card_id and c.name != "Ballaber"),
            None
        )
        if card_to_sleep is None:
            raise HTTPException(
                status_code=400,
                detail=f"Alternative cost card with ID '{alternative_cost_card_id}' not found"
            )
        # Sleep the card and set cost to 0
        was_in_play = card_to_sleep in player.in_play
        game_state.sleep_card(card_to_sleep, was_in_play=was_in_play)
        kwargs["alternative_cost_paid"] = True
        kwargs["alternative_cost_card"] = card_to_sleep.name
        cost = 0
    else:
        # Calculate normal cost
        cost = engine.calculate_card_cost(card, player)
    
    return kwargs, cost


def handle_targets(
    target_card_id: str | None,
    target_card_ids: List[str] | None,
    game_state: Any
) -> Dict[str, Any]:
    """
    Find and validate target cards by their IDs.
    
    Returns:
        dict: kwargs with 'target', 'target_name', and/or 'targets'
    """
    kwargs = {}
    
    # Single target
    if target_card_id:
        target = game_state.find_card_by_id(target_card_id)
        if target is None:
            raise HTTPException(
                status_code=400,
                detail=f"Target card with ID '{target_card_id}' not found"
            )
        kwargs["target"] = target
        kwargs["target_name"] = target.name  # For Copy card
    
    # Multiple targets
    if target_card_ids:
        targets = []
        for card_id in target_card_ids:
            target = game_state.find_card_by_id(card_id)
            if target is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"Target card with ID '{card_id}' not found"
                )
            targets.append(target)
        kwargs["targets"] = targets
    
    return kwargs


def build_play_card_description(
    card: Any,
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
        if card.name == "Wake" and kwargs.get("target"):
            target_card = kwargs["target"]
            description += f". Unslept {target_card.name}"
        elif card.name == "Sun" and kwargs.get("targets"):
            target_names = [t.name for t in kwargs["targets"]]
            description += f". Sleeped {', '.join(target_names)}"
        elif card.name == "Copy" and kwargs.get("target"):
            target_card = kwargs["target"]
            description += f". Copied {target_card.name}"
        elif card.name == "Twist" and kwargs.get("target"):
            target_card = kwargs["target"]
            description += f". Took control of {target_card.name}"
    
    # For Ballaber (Toy with alternative cost)
    if card.name == "Ballaber" and kwargs.get("alternative_cost_paid"):
        alt_card = kwargs["alternative_cost_card"]
        description += f". Slept {alt_card} for alternative cost"
    
    return description


@router.post("/{game_id}/play-card", response_model=ActionResponse)
async def play_card(game_id: str, request: PlayCardRequest) -> ActionResponse:
    """
    Play a card from hand.
    
    - **game_id**: The game ID
    - **player_id**: ID of player playing the card
    - **card_name**: Name of card to play
    - **target_card_name**: Optional target for effects
    - **target_card_names**: Optional multiple targets (e.g., Sun)
    """
    service = get_game_service()
    engine = service.get_game(game_id)
    
    if engine is None:
        raise HTTPException(status_code=404, detail=f"Game {game_id} not found")
    
    game_state = engine.game_state
    
    # Verify it's the player's turn
    if game_state.active_player_id != request.player_id:
        raise HTTPException(
            status_code=400,
            detail="It's not your turn"
        )
    
    # Get player
    player = game_state.players.get(request.player_id)
    if player is None:
        raise HTTPException(status_code=404, detail="Player not found")
    
    # Find card in hand by ID
    card = next((c for c in player.hand if c.id == request.card_id), None)
    if card is None:
        raise HTTPException(
            status_code=400,
            detail=f"Card with ID '{request.card_id}' not found in hand"
        )
    
    # Handle alternative cost (Ballaber) and calculate cost
    alt_cost_kwargs, cost = handle_alternative_cost(
        card, request.alternative_cost_card_id, player, game_state, engine
    )
    
    # Handle targets
    target_kwargs = handle_targets(
        request.target_card_id, request.target_card_ids, game_state
    )
    
    # Merge kwargs
    kwargs = {**alt_cost_kwargs, **target_kwargs}
    
    # Play the card
    try:
        effect_outcome = None
        # If alternative cost was paid, we already slept the card, so override cost to 0
        if kwargs.get("alternative_cost_paid"):
            # Manually pay 0 CC and play the card
            if not player.spend_cc(0):  # This should always succeed
                return ActionResponse(
                    success=False,
                    message="Failed to play card"
                )
            # Remove from hand
            player.hand.remove(card)
            # Toys go to in play
            from game_engine.models.card import CardType, Zone
            if card.card_type == CardType.TOY:
                card.zone = Zone.IN_PLAY
                player.in_play.append(card)
            elif card.card_type == CardType.ACTION:
                # Actions resolve and go to sleep zone
                engine._resolve_action_card(card, player, **kwargs)
                card.zone = Zone.SLEEP
                player.sleep_zone.append(card)
            success = True
        else:
            # Normal play_card flow
            success = engine.play_card(player, card, **kwargs)
        if not success:
            return ActionResponse(
                success=False,
                message="Failed to play card (insufficient CC or invalid target)"
            )
        # Check state-based actions
        engine.check_state_based_actions()
        
        # Build description
        description = build_play_card_description(card, cost, kwargs)
        
        # Extract target info for response message
        target_info = ""
        if card.name == "Wake" and kwargs.get("target"):
            target_info = f" (unslept {kwargs['target'].name})"
        elif card.name == "Sun" and kwargs.get("targets"):
            target_names = [t.name for t in kwargs["targets"]]
            target_info = f" (sleeped {', '.join(target_names)})"
        elif card.name == "Copy" and kwargs.get("target"):
            target_info = f" (copied {kwargs['target'].name})"
        elif card.name == "Twist" and kwargs.get("target"):
            target_info = f" (took control of {kwargs['target'].name})"
        
        # Log to play-by-play BEFORE victory check (so action appears first)
        game_state.add_play_by_play(
            player_name=player.name,
            action_type="play_card",
            description=description,
        )
        # Check for victory (some cards like action cards might cause instant victory)
        winner = game_state.check_victory()
        if winner:
            # Add victory message to play-by-play AFTER the winning action
            winner_name = game_state.players[winner].name
            game_state.add_play_by_play(
                player_name=winner_name,
                action_type="victory",
                description=f"{winner_name} wins! All opponent's cards are sleeped."
            )
            return ActionResponse(
                success=True,
                message=f"Card played! {game_state.players[winner].name} wins the game!",
                game_state={"winner": winner, "is_game_over": True}
            )
        return ActionResponse(
            success=True,
            message=f"Successfully played {card.name}{target_info}",
            game_state={"turn": game_state.turn_number, "phase": game_state.phase.value}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{game_id}/tussle", response_model=ActionResponse)
async def initiate_tussle(game_id: str, request: TussleRequest) -> ActionResponse:
    """
    Initiate a tussle between two cards.
    
    - **game_id**: The game ID
    - **player_id**: ID of player initiating tussle
    - **attacker_name**: Name of attacking card
    - **defender_name**: Optional name of defending card (None for direct attack)
    """
    service = get_game_service()
    engine = service.get_game(game_id)
    
    if engine is None:
        raise HTTPException(status_code=404, detail=f"Game {game_id} not found")
    
    game_state = engine.game_state
    
    # Verify it's the player's turn
    if game_state.active_player_id != request.player_id:
        raise HTTPException(status_code=400, detail="It's not your turn")
    
    # Get player
    player = game_state.players.get(request.player_id)
    if player is None:
        raise HTTPException(status_code=404, detail="Player not found")
    
    # Find attacker by ID
    attacker = next((c for c in player.in_play if c.id == request.attacker_id), None)
    if attacker is None:
        raise HTTPException(
            status_code=400,
            detail=f"Attacker with ID '{request.attacker_id}' not found in play"
        )
    
    # Find defender (if specified)
    defender = None
    if request.defender_id:
        # Find defender by ID (no need to restrict search - ID is globally unique)
        defender = game_state.find_card_by_id(request.defender_id)
        if defender is None:
            raise HTTPException(
                status_code=400,
                detail=f"Defender with ID '{request.defender_id}' not found"
            )
    
    # Initiate tussle
    try:
        # Calculate cost before tussle
        cost = engine.calculate_tussle_cost(attacker, player)
        
        success = engine.initiate_tussle(attacker, defender, player)
        
        if not success:
            return ActionResponse(
                success=False,
                message="Failed to initiate tussle (insufficient CC, invalid target, or card restrictions)"
            )
        
        # Check state-based actions
        engine.check_state_based_actions()
        
        # Log to play-by-play with cost BEFORE victory check (so action appears first)
        target_desc = defender.name if defender else "opponent directly"
        game_state.add_play_by_play(
            player_name=player.name,
            action_type="tussle",
            description=f"Spent {cost} CC for {attacker.name} to tussle {target_desc}",
        )
        
        # Check for victory
        winner = game_state.check_victory()
        if winner:
            # Add victory message to play-by-play AFTER the winning action
            winner_name = game_state.players[winner].name
            game_state.add_play_by_play(
                player_name=winner_name,
                action_type="victory",
                description=f"{winner_name} wins! All opponent's cards are sleeped."
            )
            return ActionResponse(
                success=True,
                message=f"Tussle successful! {winner} wins the game!",
                game_state={"winner": winner}
            )
        
        return ActionResponse(
            success=True,
            message=f"Tussle initiated successfully",
            game_state={"turn": game_state.turn_number}
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{game_id}/end-turn", response_model=ActionResponse)
async def end_turn(game_id: str, request: EndTurnRequest) -> ActionResponse:
    """
    End the current player's turn.
    
    - **game_id**: The game ID
    - **player_id**: ID of player ending their turn
    """
    service = get_game_service()
    engine = service.get_game(game_id)
    
    if engine is None:
        raise HTTPException(status_code=404, detail=f"Game {game_id} not found")
    
    game_state = engine.game_state
    
    # Verify it's the player's turn
    if game_state.active_player_id != request.player_id:
        raise HTTPException(status_code=400, detail="It's not your turn")
    
    # Get player for logging
    player = game_state.players.get(request.player_id)
    
    # End turn
    try:
        # Log to play-by-play BEFORE ending turn (so turn number is correct)
        if player:
            game_state.add_play_by_play(
                player_name=player.name,
                action_type="end_turn",
                description="Ended turn",
            )
        
        engine.end_turn()
        
        return ActionResponse(
            success=True,
            message=f"Turn ended. It's now {game_state.active_player_id}'s turn",
            game_state={
                "turn": game_state.turn_number,
                "active_player": game_state.active_player_id,
                "phase": game_state.phase.value
            }
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{game_id}/valid-actions", response_model=ValidActionsResponse)
async def get_valid_actions(game_id: str, player_id: str) -> ValidActionsResponse:
    """
    Get list of valid actions for a player.
    
    - **game_id**: The game ID
    - **player_id**: ID of player to get actions for
    
    Returns list of actions the player can currently take.
    """
    service = get_game_service()
    engine = service.get_game(game_id)
    
    if engine is None:
        raise HTTPException(status_code=404, detail=f"Game {game_id} not found")
    
    # Use ActionValidator for single source of truth
    validator = ActionValidator(engine)
    valid_actions = validator.get_valid_actions(player_id, filter_for_ai=False)
    
    return ValidActionsResponse(
        game_id=game_id,
        player_id=player_id,
        valid_actions=valid_actions
    )


@router.post("/{game_id}/ai-turn", response_model=ActionResponse)
async def ai_take_turn(game_id: str, player_id: str) -> ActionResponse:
    """
    Have the AI select and execute an action for the specified player.
    
    - **game_id**: The game ID
    - **player_id**: ID of the AI player
    
    The AI will:
    1. Analyze the current game state
    2. Get all valid actions
    3. Use Claude to select the best action
    4. Execute that action
    
    Returns the result of the action.
    """
    service = get_game_service()
    engine = service.get_game(game_id)
    
    if engine is None:
        raise HTTPException(status_code=404, detail=f"Game {game_id} not found")
    
    game_state = engine.game_state
    
    # Verify it's the AI player's turn
    if game_state.active_player_id != player_id:
        logger.warning(
            f"AI turn request rejected: player_id={player_id}, "
            f"active_player_id={game_state.active_player_id}, "
            f"turn={game_state.turn_number}"
        )
        raise HTTPException(
            status_code=400,
            detail=f"It's not {player_id}'s turn (active player: {game_state.active_player_id})"
        )
    
    # Get player
    player = game_state.players.get(player_id)
    if player is None:
        raise HTTPException(status_code=404, detail="Player not found")
    
    # Use ActionValidator for single source of truth
    # Enable AI filtering to remove strategically bad moves
    validator = ActionValidator(engine)
    valid_actions = validator.get_valid_actions(player_id, filter_for_ai=True)
    
    # Log available actions for debugging
    logger.debug(f"Available actions after filtering/prioritizing: {[a.description for a in valid_actions]}")
    
    # Get AI player and have it select an action
    try:
        logger.info(f"🤖 AI turn starting for player {player_id} in game {game_id}")
        logger.debug(f"Available actions: {[a.description for a in valid_actions]}")
        
        ai_player = get_ai_player()
        result = ai_player.select_action(game_state, player_id, valid_actions)
        
        if result is None:
            # AI failed to select - default to end turn
            logger.warning("AI failed to select action, defaulting to end turn")
            engine.end_turn()
            
            # Log to play-by-play
            game_state.add_play_by_play(
                player_name=player.name,
                action_type="pass",
                description="AI failed to select action, ended turn",
                ai_endpoint=ai_player.get_endpoint_name(),
            )
            
            return ActionResponse(
                success=True,
                message="AI failed to select action, ended turn",
                game_state={
                    "turn": game_state.turn_number,
                    "active_player": game_state.active_player_id
                },
                ai_turn_summary={
                    "action": "pass",
                    "available_actions_count": len(valid_actions),
                    "ai_endpoint": ai_player.get_endpoint_name(),
                }
            )
        
        action_index, reasoning = result
        selected_action = valid_actions[action_index]
        action_details = ai_player.get_action_details(selected_action)
        ai_endpoint_name = ai_player.get_endpoint_name()
        
        # Build turn summary for response
        turn_summary = {
            "action": action_details["action_type"],
            "card": action_details.get("card_id") or action_details.get("attacker_id"),
            "target": action_details.get("defender_id"),
            "cost_cc": selected_action.cost_cc,
            "description": selected_action.description,
            "reasoning": reasoning,
            "ai_endpoint": ai_endpoint_name,
        }
        
        # Execute the selected action
        if action_details["action_type"] == "end_turn":
            # Log to play-by-play BEFORE ending turn
            game_state.add_play_by_play(
                player_name=player.name,
                action_type="end_turn",
                description="Ended turn",
                reasoning=reasoning,
                ai_endpoint=ai_endpoint_name,
            )
            
            engine.end_turn()
            
            return ActionResponse(
                success=True,
                message=f"AI ended turn",
                game_state={
                    "turn": game_state.turn_number,
                    "active_player": game_state.active_player_id
                },
                ai_turn_summary=turn_summary
            )
        
        elif action_details["action_type"] == "play_card":
            card_id = action_details["card_id"]
            card = next((c for c in player.hand if c.id == card_id), None)
            
            if card is None:
                raise HTTPException(status_code=500, detail=f"AI selected invalid card ID: {card_id}")
            
            # Handle alternative cost and calculate cost
            alt_cost_kwargs, cost = handle_alternative_cost(
                card, action_details.get("alternative_cost_card_id"), player, game_state, engine
            )
            
            # Handle targets
            target_kwargs = handle_targets(
                action_details.get("target_id"), None, game_state
            )
            
            # Merge kwargs
            kwargs = {**alt_cost_kwargs, **target_kwargs}
            
            # Log target selection for debugging
            if kwargs.get("target"):
                logger.info(f"AI playing {card.name} with target: {kwargs['target'].name} (ID: {action_details.get('target_id')})")
            
            success = engine.play_card(player, card, **kwargs)
            engine.check_state_based_actions()
            
            # Build description
            description = build_play_card_description(card, cost, kwargs)
            
            # Log to play-by-play
            game_state.add_play_by_play(
                player_name=player.name,
                action_type="play_card",
                description=description,
                reasoning=reasoning,
                ai_endpoint=ai_endpoint_name,
            )
            
            return ActionResponse(
                success=success,
                message=f"AI played {card.name}",
                game_state={"turn": game_state.turn_number},
                ai_turn_summary=turn_summary
            )
        
        elif action_details["action_type"] == "tussle":
            attacker_id = action_details["attacker_id"]
            defender_id = action_details.get("defender_id")
            
            attacker = next((c for c in player.in_play if c.id == attacker_id), None)
            if attacker is None:
                raise HTTPException(status_code=500, detail=f"AI selected invalid attacker ID: {attacker_id}")
            
            defender = None
            if defender_id:
                defender = game_state.find_card_by_id(defender_id)
            
            # Calculate cost before tussle
            cost = engine.calculate_tussle_cost(attacker, player)
            
            success = engine.initiate_tussle(attacker, defender, player)
            engine.check_state_based_actions()
            
            # Log to play-by-play with cost
            target_desc = defender.name if defender else "opponent directly"
            game_state.add_play_by_play(
                player_name=player.name,
                action_type="tussle",
                description=f"Spent {cost} CC for {attacker.name} to tussle {target_desc}",
                reasoning=reasoning,
                ai_endpoint=ai_endpoint_name,
            )
            
            # Check for victory
            winner = game_state.check_victory()
            if winner:
                return ActionResponse(
                    success=True,
                    message=f"AI tussle successful! {winner} wins!",
                    game_state={"winner": winner},
                    ai_turn_summary=turn_summary
                )
            
            return ActionResponse(
                success=success,
                message=f"AI initiated tussle: {attacker.name} vs {target_desc}",
                game_state={"turn": game_state.turn_number},
                ai_turn_summary=turn_summary
            )
        
        else:
            logger.error(f"Unknown action type from AI: {action_details['action_type']}")
            raise HTTPException(status_code=500, detail=f"Unknown action type: {action_details['action_type']}")
    
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        logger.exception(f"AI turn failed with exception: {e}")
        raise HTTPException(status_code=500, detail=f"AI turn failed: {str(e)}")
