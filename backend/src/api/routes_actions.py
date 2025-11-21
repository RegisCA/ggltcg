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
from game_engine.validation import ActionValidator, ActionExecutor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/games", tags=["actions"])


# ============================================================================
# Game Action Endpoints
# ============================================================================
# All action execution logic has been moved to ActionExecutor for consistency
# between human and AI player paths.


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
    
    # Use ActionExecutor to execute the play
    executor = ActionExecutor(engine)
    
    try:
        result = executor.execute_play_card(
            player_id=request.player_id,
            card_id=request.card_id,
            target_card_id=request.target_card_id,
            target_card_ids=request.target_card_ids,
            alternative_cost_card_id=request.alternative_cost_card_id
        )
        
        if not result.success:
            return ActionResponse(
                success=False,
                message=result.message
            )
        
        # Log to play-by-play BEFORE victory check (so action appears first)
        game_state.add_play_by_play(
            player_name=player.name,
            action_type="play_card",
            description=result.description,
        )
        
        # Check for victory
        if result.winner:
            # Add victory message to play-by-play AFTER the winning action
            winner_name = game_state.players[result.winner].name
            game_state.add_play_by_play(
                player_name=winner_name,
                action_type="victory",
                description=f"{winner_name} wins! All opponent's cards are sleeped."
            )
            return ActionResponse(
                success=True,
                message=f"Card played! {game_state.players[result.winner].name} wins the game!",
                game_state={"winner": result.winner, "is_game_over": True}
            )
        
        return ActionResponse(
            success=True,
            message=result.message,
            game_state={"turn": game_state.turn_number, "phase": game_state.phase.value}
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
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
            
            # Use ActionExecutor to execute the play
            executor = ActionExecutor(engine)
            
            try:
                result = executor.execute_play_card(
                    player_id=player_id,
                    card_id=card_id,
                    target_card_id=action_details.get("target_id"),
                    alternative_cost_card_id=action_details.get("alternative_cost_card_id")
                )
                
                if not result.success:
                    raise HTTPException(status_code=500, detail=result.message)
                
                # Log to play-by-play
                game_state.add_play_by_play(
                    player_name=player.name,
                    action_type="play_card",
                    description=result.description,
                    reasoning=reasoning,
                    ai_endpoint=ai_endpoint_name,
                )
                
                # Check for victory
                if result.winner:
                    winner_name = game_state.players[result.winner].name
                    game_state.add_play_by_play(
                        player_name=winner_name,
                        action_type="victory",
                        description=f"{winner_name} wins! All opponent's cards are sleeped."
                    )
                    return ActionResponse(
                        success=True,
                        message=f"AI card played! {winner_name} wins the game!",
                        game_state={"winner": result.winner, "is_game_over": True},
                        ai_turn_summary=turn_summary
                    )
                
                return ActionResponse(
                    success=True,
                    message=result.message,
                    game_state={"turn": game_state.turn_number},
                    ai_turn_summary=turn_summary
                )
                
            except ValueError as e:
                # AI-specific error handling - likely LLM hallucination
                error_msg = str(e)
                if "not found" in error_msg.lower():
                    logger.error(
                        f"🤖 LLM HALLUCINATION DETECTED - AI play_card failed:\n"
                        f"  Card ID: {card_id}\n"
                        f"  Target ID: {action_details.get('target_id')}\n"
                        f"  Alt Cost ID: {action_details.get('alternative_cost_card_id')}\n"
                        f"  Error: {error_msg}\n"
                        f"  Game: {game_id}, Turn: {game_state.turn_number}"
                    )
                    error_detail = f"AI selected invalid card/target ID (likely LLM hallucination): {error_msg}"
                else:
                    error_detail = f"AI action execution failed: {error_msg}"
                raise HTTPException(status_code=500, detail=error_detail)
        
        elif action_details["action_type"] == "tussle":
            # Use ActionExecutor to execute the tussle
            executor = ActionExecutor(engine)
            
            try:
                result = executor.execute_tussle(
                    player_id=player_id,
                    attacker_id=action_details["attacker_id"],
                    defender_id=action_details.get("defender_id")
                )
                
                if not result.success:
                    raise HTTPException(status_code=500, detail=result.message)
                
                # Log to play-by-play
                game_state.add_play_by_play(
                    player_name=player.name,
                    action_type="tussle",
                    description=result.description,
                    reasoning=reasoning,
                    ai_endpoint=ai_endpoint_name,
                )
                
                # Check for victory
                if result.winner:
                    winner_name = game_state.players[result.winner].name
                    game_state.add_play_by_play(
                        player_name=winner_name,
                        action_type="victory",
                        description=f"{winner_name} wins! All opponent's cards are sleeped."
                    )
                    return ActionResponse(
                        success=True,
                        message=f"AI tussle successful! {winner_name} wins!",
                        game_state={"winner": result.winner, "is_game_over": True},
                        ai_turn_summary=turn_summary
                    )
                
                return ActionResponse(
                    success=True,
                    message=result.message,
                    game_state={"turn": game_state.turn_number},
                    ai_turn_summary=turn_summary
                )
                
            except ValueError as e:
                # AI-specific error handling - likely LLM hallucination
                error_msg = str(e)
                if "not found" in error_msg.lower():
                    logger.error(
                        f"🤖 LLM HALLUCINATION DETECTED - AI tussle failed:\n"
                        f"  Attacker ID: {action_details['attacker_id']}\n"
                        f"  Defender ID: {action_details.get('defender_id')}\n"
                        f"  Error: {error_msg}\n"
                        f"  Game: {game_id}, Turn: {game_state.turn_number}"
                    )
                    error_detail = f"AI selected invalid attacker/defender ID (likely LLM hallucination): {error_msg}"
                else:
                    error_detail = f"AI tussle execution failed: {error_msg}"
                raise HTTPException(status_code=500, detail=error_detail)
        
        else:
            logger.error(f"Unknown action type from AI: {action_details['action_type']}")
            raise HTTPException(status_code=500, detail=f"Unknown action type: {action_details['action_type']}")
    
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        logger.exception(f"AI turn failed with exception: {e}")
        raise HTTPException(status_code=500, detail=f"AI turn failed: {str(e)}")
