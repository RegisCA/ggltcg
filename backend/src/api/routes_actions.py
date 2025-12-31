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
from api.stats_service import get_stats_service
from game_engine.models.card import CardType
from game_engine.ai.llm_player import get_ai_player
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
    - **card_id**: ID of card to play
    - **target_card_id**: Optional target for single-target effects
    - **target_card_ids**: Optional multiple targets (e.g., Sun)
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
            # Save updated game state to database
            service.update_game(game_id, engine)
            return ActionResponse(
                success=True,
                message=f"Card played! {game_state.players[result.winner].name} wins the game!",
                game_state={"winner": result.winner, "is_game_over": True}
            )
        
        # Save updated game state to database
        service.update_game(game_id, engine)
        
        return ActionResponse(
            success=True,
            message=result.description,  # Use detailed description for better UX
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
        
        success, sleeped_from_hand = engine.initiate_tussle(attacker, defender, player)
        
        if not success:
            return ActionResponse(
                success=False,
                message="Failed to initiate tussle (insufficient CC, invalid target, or card restrictions)"
            )
        
        # Check state-based actions
        engine.check_state_based_actions()
        
        # Log to play-by-play with cost BEFORE victory check (so action appears first)
        if defender:
            target_desc = defender.name
        elif sleeped_from_hand:
            target_desc = f"{sleeped_from_hand} (from hand)"
        else:
            target_desc = "opponent directly"
        description = f"Spent {cost} CC for {attacker.name} to tussle {target_desc}"
        game_state.add_play_by_play(
            player_name=player.name,
            action_type="tussle",
            description=description,
        )
        
        # Save updated game state to database
        service.update_game(game_id, engine)
        
        # Check for victory
        winner = game_state.winner_id
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
                message=f"Tussle successful! {winner_name} wins the game!",
                game_state={"winner": winner}
            )
        
        return ActionResponse(
            success=True,
            message=description,
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
        
        # Save updated game state to database
        service.update_game(game_id, engine)
        
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


@router.post("/{game_id}/activate-ability", response_model=ActionResponse)
async def activate_ability(game_id: str, request: ActivateAbilityRequest) -> ActionResponse:
    """
    Activate a card's ability.
    
    - **game_id**: The game ID
    - **player_id**: ID of player activating the ability
    - **card_id**: ID of the card with the ability
    - **target_id**: Optional target card ID for the ability
    - **amount**: Amount parameter (e.g., for Archer to remove stamina)
    """
    service = get_game_service()
    engine = service.get_game(game_id)
    
    if engine is None:
        raise HTTPException(status_code=404, detail=f"Game {game_id} not found")
    
    game_state = engine.game_state
    
    # Verify it's the player's turn
    if game_state.active_player_id != request.player_id:
        raise HTTPException(status_code=400, detail="It's not your turn")
    
    player = game_state.players.get(request.player_id)
    if player is None:
        raise HTTPException(status_code=404, detail=f"Player {request.player_id} not found")
    
    # Find the card with the ability by ID
    source_card = None
    for card in player.in_play:
        if card.id == request.card_id:
            source_card = card
            break
    
    if source_card is None:
        raise HTTPException(
            status_code=404,
            detail=f"Card with ID {request.card_id} not found in play"
        )
    
    # Get the activated effect
    from game_engine.rules.effects import EffectRegistry
    from game_engine.rules.effects.base_effect import ActivatedEffect
    
    effects = EffectRegistry.get_effects(source_card)
    activated_effect = None
    for effect in effects:
        if isinstance(effect, ActivatedEffect):
            activated_effect = effect
            break
    
    if activated_effect is None:
        raise HTTPException(
            status_code=400,
            detail=f"Card {source_card.name} has no activated ability"
        )
    
    # Calculate cost (for Archer, it's the amount)
    amount = request.amount or 1
    cost = activated_effect.cost_cc * amount
    
    # Check if player can afford it
    if player.cc < cost:
        raise HTTPException(
            status_code=400,
            detail=f"Not enough CC (need {cost}, have {player.cc})"
        )
    
    # Get target if specified
    target_card = None
    if request.target_id:
        # Find target by ID in all cards in play
        all_cards = game_state.get_all_cards_in_play()
        for card in all_cards:
            if card.id == request.target_id:
                target_card = card
                break
        
        if target_card is None:
            raise HTTPException(
                status_code=404,
                detail=f"Target card with ID {request.target_id} not found in play"
            )
    
    try:
        # Pay the cost
        player.spend_cc(cost)
        
        # Apply the ability
        activated_effect.apply(
            game_state,
            target=target_card,
            amount=amount,
            game_engine=engine
        )
        
        # Log to play-by-play
        description = f"Activated {source_card.name}'s ability"
        if target_card:
            description += f" targeting {target_card.name}"
        if amount > 1:
            description += f" (amount: {amount})"
        
        game_state.add_play_by_play(
            player_name=player.name,
            action_type="activate_ability",
            description=description
        )
        
        # Save updated game state to database
        service.update_game(game_id, engine)
        
        # Check for victory
        winner = game_state.winner_id
        if winner:
            winner_name = game_state.players[winner].name
            game_state.add_play_by_play(
                player_name=winner_name,
                action_type="victory",
                description=f"{winner_name} wins! All opponent's cards are sleeped."
            )
            return ActionResponse(
                success=True,
                message=f"Ability activated! {winner} wins the game!",
                game_state={"winner": winner}
            )
        
        return ActionResponse(
            success=True,
            message=description,
            game_state={"turn": game_state.turn_number}
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
    
    # Get AI player first to determine version
    ai_player = get_ai_player()
    
    # Use ActionValidator for single source of truth
    # V2: Enable AI filtering to remove strategically bad moves (losing tussles)
    # V3: Disable filtering - v3 does strategic planning and may need tactical sacrifices
    is_v3 = ai_player.__class__.__name__ == 'LLMPlayerV3'
    filter_for_ai = not is_v3  # False for v3, True for v2
    
    validator = ActionValidator(engine)
    valid_actions = validator.get_valid_actions(player_id, filter_for_ai=filter_for_ai)
    
    # Log available actions for debugging
    logger.debug(f"Available actions (filtered={filter_for_ai}): {[a.description for a in valid_actions]}")
    
    # Get AI player and have it select an action
    try:
        logger.info(f"🤖 AI turn starting for player {player_id} in game {game_id} (v{'3' if is_v3 else '2'})")
        logger.debug(f"Available actions: {[a.description for a in valid_actions]}")
        result = ai_player.select_action(game_state, player_id, valid_actions, engine)
        
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
            
            # Save updated game state to database
            service.update_game(game_id, engine)
            
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
        
        # Log AI decision to database for debugging
        try:
            decision_info = ai_player.get_last_decision_info()
            stats_service = get_stats_service()
            
            # Extract v3 plan info if available
            v3_plan = decision_info.get("v3_plan")
            ai_version = 3 if v3_plan else 2
            
            # Determine execution status from reasoning prefix
            plan_execution_status = None
            fallback_reason = None
            if reasoning:
                if "[v3 Fallback]" in reasoning:
                    plan_execution_status = "fallback"
                    # Extract fallback reason (only if "Plan failed:" marker exists)
                    if "Plan failed:" in reasoning:
                        fallback_reason = reasoning.split("Plan failed:", 1)[-1].strip()
                elif "[v3 Plan]" in reasoning:
                    plan_execution_status = "complete"
            
            stats_service.log_ai_decision(
                game_id=game_id,
                turn_number=game_state.turn_number,
                player_id=player_id,
                model_name=decision_info["model_name"],
                prompts_version=decision_info["prompts_version"],
                prompt=decision_info["prompt"] or "",
                response=decision_info["response"] or "",
                action_number=decision_info["action_number"],
                reasoning=decision_info["reasoning"],
                # v3 fields
                ai_version=ai_version,
                turn_plan=v3_plan,  # Will be dict with strategy, actions, etc.
                plan_execution_status=plan_execution_status,
                fallback_reason=fallback_reason,
                planned_action_index=v3_plan.get("current_action") if v3_plan else None,
            )
        except Exception as e:
            # Don't fail the action if logging fails
            logger.warning(f"Failed to log AI decision: {e}")
        
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
            # Note: AI reasoning is stored in AI logs, not play-by-play (keeps it factual)
            game_state.add_play_by_play(
                player_name=player.name,
                action_type="end_turn",
                description="Ended turn",
                ai_endpoint=ai_endpoint_name,
            )
            
            engine.end_turn()
            
            # Save updated game state to database
            service.update_game(game_id, engine)
            
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
                # v2.0: Support both target_ids (array, new) and target_id (legacy)
                target_ids = action_details.get("target_ids")
                target_id_legacy = action_details.get("target_id")
                
                # Normalize to target_card_ids array
                if target_ids:
                    target_card_ids = target_ids if isinstance(target_ids, list) else [target_ids]
                elif target_id_legacy:
                    target_card_ids = [target_id_legacy]
                else:
                    target_card_ids = None
                
                result = executor.execute_play_card(
                    player_id=player_id,
                    card_id=card_id,
                    target_card_ids=target_card_ids,
                    alternative_cost_card_id=action_details.get("alternative_cost_card_id")
                )
                
                if not result.success:
                    raise HTTPException(status_code=500, detail=result.message)
                
                # Record successful execution for v3 tracking
                if hasattr(ai_player, 'record_execution_result'):
                    ai_player.record_execution_result(success=True)
                
                # Log to play-by-play
                # Note: AI reasoning is stored in AI logs, not play-by-play (keeps it factual)
                game_state.add_play_by_play(
                    player_name=player.name,
                    action_type="play_card",
                    description=result.description,
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
                    # Save updated game state to database
                    service.update_game(game_id, engine)
                    return ActionResponse(
                        success=True,
                        message=f"AI card played! {winner_name} wins the game!",
                        game_state={"winner": result.winner, "is_game_over": True},
                        ai_turn_summary=turn_summary
                    )
                
                # Save updated game state to database
                service.update_game(game_id, engine)
                
                return ActionResponse(
                    success=True,
                    message=result.description,  # Use detailed description for better UX
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
                        f"  Target IDs: {action_details.get('target_ids') or action_details.get('target_id')}\n"
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
                
                # Record successful execution for v3 tracking
                if hasattr(ai_player, 'record_execution_result'):
                    ai_player.record_execution_result(success=True)
                
                # Log to play-by-play
                # Note: AI reasoning is stored in AI logs, not play-by-play (keeps it factual)
                game_state.add_play_by_play(
                    player_name=player.name,
                    action_type="tussle",
                    description=result.description,
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
                    # Save updated game state to database
                    service.update_game(game_id, engine)
                    return ActionResponse(
                        success=True,
                        message=f"AI tussle successful! {winner_name} wins!",
                        game_state={"winner": result.winner, "is_game_over": True},
                        ai_turn_summary=turn_summary
                    )
                
                # Save updated game state to database
                service.update_game(game_id, engine)
                
                return ActionResponse(
                    success=True,
                    message=result.description,  # Use detailed description for better UX
                    game_state={"turn": game_state.turn_number},
                    ai_turn_summary=turn_summary
                )
                
            except ValueError as e:
                # Record execution failure for v3 tracking
                if hasattr(ai_player, 'record_execution_result'):
                    ai_player.record_execution_result(success=False, error_message=str(e))
                
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
        
        elif action_details["action_type"] == "activate_ability":
            # Execute activated ability (e.g., Archer)
            card_id = action_details["card_id"]
            target_id = action_details.get("target_id")
            amount = action_details.get("amount", 1)
            
            # Find the card with the ability
            source_card = None
            for card in player.in_play:
                if card.id == card_id:
                    source_card = card
                    break
            
            if source_card is None:
                raise HTTPException(
                    status_code=500,
                    detail=f"AI selected card with ID {card_id} not found in play"
                )
            
            # Get the activated effect
            from game_engine.rules.effects import EffectRegistry
            from game_engine.rules.effects.base_effect import ActivatedEffect
            
            effects = EffectRegistry.get_effects(source_card)
            activated_effect = None
            for effect in effects:
                if isinstance(effect, ActivatedEffect):
                    activated_effect = effect
                    break
            
            if activated_effect is None:
                raise HTTPException(
                    status_code=500,
                    detail=f"Card {source_card.name} has no activated ability"
                )
            
            # Calculate cost
            cost = activated_effect.cost_cc * amount
            
            # Check if player can afford it
            if player.cc < cost:
                raise HTTPException(
                    status_code=500,
                    detail=f"AI tried to activate ability without enough CC (need {cost}, have {player.cc})"
                )
            
            # Get target if specified
            target_card = None
            if target_id:
                all_cards = game_state.get_all_cards_in_play()
                for card in all_cards:
                    if card.id == target_id:
                        target_card = card
                        break
                
                if target_card is None:
                    logger.error(
                        f"🤖 LLM HALLUCINATION DETECTED - AI activate_ability target not found:\n"
                        f"  Card ID: {card_id}\n"
                        f"  Target ID: {target_id}\n"
                        f"  Game: {game_id}, Turn: {game_state.turn_number}"
                    )
                    raise HTTPException(
                        status_code=500,
                        detail=f"AI selected invalid target ID (likely LLM hallucination): {target_id}"
                    )
            
            try:
                # Pay the cost
                player.spend_cc(cost)
                
                # Apply the ability
                activated_effect.apply(
                    game_state,
                    target=target_card,
                    amount=amount,
                    game_engine=engine
                )
                
                # Record successful execution for v3 tracking
                if hasattr(ai_player, 'record_execution_result'):
                    ai_player.record_execution_result(success=True)
                
                # Log to play-by-play
                description = f"Activated {source_card.name}'s ability"
                if target_card:
                    description += f" targeting {target_card.name}"
                if amount > 1:
                    description += f" (amount: {amount})"
                
                # Note: AI reasoning is stored in AI logs, not play-by-play (keeps it factual)
                game_state.add_play_by_play(
                    player_name=player.name,
                    action_type="activate_ability",
                    description=description,
                    ai_endpoint=ai_endpoint_name,
                )
                
                # Check for victory
                winner = game_state.winner_id
                if winner:
                    winner_name = game_state.players[winner].name
                    game_state.add_play_by_play(
                        player_name=winner_name,
                        action_type="victory",
                        description=f"{winner_name} wins! All opponent's cards are sleeped."
                    )
                    # Save updated game state to database
                    service.update_game(game_id, engine)
                    return ActionResponse(
                        success=True,
                        message=f"AI ability activated! {winner_name} wins!",
                        game_state={"winner": winner, "is_game_over": True},
                        ai_turn_summary=turn_summary
                    )
                
                # Save updated game state to database
                service.update_game(game_id, engine)
                
                return ActionResponse(
                    success=True,
                    message=description,
                    game_state={"turn": game_state.turn_number},
                    ai_turn_summary=turn_summary
                )
                
            except Exception as e:
                # Record execution failure for v3 tracking
                if hasattr(ai_player, 'record_execution_result'):
                    ai_player.record_execution_result(success=False, error_message=str(e))
                raise HTTPException(status_code=500, detail=f"AI activate_ability failed: {str(e)}")
        
        else:
            logger.error(f"Unknown action type from AI: {action_details['action_type']}")
            raise HTTPException(status_code=500, detail=f"Unknown action type: {action_details['action_type']}")
    
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        logger.exception(f"AI turn failed with exception: {e}")
        raise HTTPException(status_code=500, detail=f"AI turn failed: {str(e)}")
