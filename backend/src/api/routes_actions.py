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

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/games", tags=["actions"])


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
    
    # Find card in hand
    card = next((c for c in player.hand if c.name == request.card_name), None)
    if card is None:
        raise HTTPException(
            status_code=400,
            detail=f"Card '{request.card_name}' not found in hand"
        )
    
    # Prepare kwargs for effect
    kwargs: Dict[str, Any] = {}
    
    # Add target if specified
    if request.target_card_name:
        target = game_state.find_card_by_name(request.target_card_name)
        if target is None:
            raise HTTPException(
                status_code=400,
                detail=f"Target card '{request.target_card_name}' not found"
            )
        kwargs["target"] = target
        kwargs["target_name"] = request.target_card_name  # For Copy card
    
    # Add multiple targets if specified
    if request.target_card_names:
        targets = []
        for name in request.target_card_names:
            target = game_state.find_card_by_name(name)
            if target is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"Target card '{name}' not found"
                )
            targets.append(target)
        kwargs["targets"] = targets
    
    # Play the card
    try:
        # Calculate cost before playing
        cost = engine.calculate_card_cost(card, player)
        
        success = engine.play_card(player, card, **kwargs)
        
        if not success:
            return ActionResponse(
                success=False,
                message="Failed to play card (insufficient CC or invalid target)"
            )
        
        # Check state-based actions
        engine.check_state_based_actions()
        
        # Build description with card effect for Action cards
        description = f"Spent {cost} CC to play {request.card_name}"
        if card.is_action():
            description += f" ({card.effect_text})"
        
        # Log to play-by-play
        game_state.add_play_by_play(
            player_name=player.name,
            action_type="play_card",
            description=description,
        )
        
        return ActionResponse(
            success=True,
            message=f"Successfully played {request.card_name}",
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
    
    # Find attacker
    attacker = next((c for c in player.in_play if c.name == request.attacker_name), None)
    if attacker is None:
        raise HTTPException(
            status_code=400,
            detail=f"Attacker '{request.attacker_name}' not found in play"
        )
    
    # Find defender (if specified)
    defender = None
    if request.defender_name:
        # Search for defender specifically in opponent's play area
        opponent = game_state.get_opponent(player.player_id)
        defender = next((c for c in opponent.in_play if c.name == request.defender_name), None)
        if defender is None:
            raise HTTPException(
                status_code=400,
                detail=f"Defender '{request.defender_name}' not found in opponent's play area"
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
        
        # Log to play-by-play with cost
        target_desc = request.defender_name if request.defender_name else "opponent directly"
        game_state.add_play_by_play(
            player_name=player.name,
            action_type="tussle",
            description=f"Spent {cost} CC for {request.attacker_name} to tussle {target_desc}",
        )
        
        # Check for victory
        winner = game_state.check_victory()
        if winner:
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
    
    game_state = engine.game_state
    
    # Get player
    player = game_state.players.get(player_id)
    if player is None:
        raise HTTPException(status_code=404, detail="Player not found")
    
    valid_actions = []
    
    # Only generate actions if it's the player's turn
    if game_state.active_player_id == player_id:
        # Can always end turn
        valid_actions.append(
            ValidAction(
                action_type="end_turn",
                description="End your turn"
            )
        )
        
        # Check which cards can be played
        for card in player.hand:
            if engine.can_play_card(card, player)[0]:  # can_play_card returns (bool, str)
                cost = engine.calculate_card_cost(card, player)
                
                # Special handling for Copy - show available targets
                if card.name == "Copy" and player.in_play:
                    # List all cards in play as potential targets
                    target_options = [c.name for c in player.in_play]
                    valid_actions.append(
                        ValidAction(
                            action_type="play_card",
                            card_name=card.name,
                            cost_cc=cost,
                            target_options=target_options,
                            description=f"Play {card.name} (Cost varies by target: {', '.join(f'{t}={engine.calculate_card_cost(player.get_card_by_name(t), player)}' for t in target_options)})"
                        )
                    )
                else:
                    valid_actions.append(
                        ValidAction(
                            action_type="play_card",
                            card_name=card.name,
                            cost_cc=cost,
                            description=f"Play {card.name} (Cost: {cost} CC)"
                        )
                    )
        
        # Check which cards can tussle
        opponent = game_state.get_opponent(player_id)
        for card in player.in_play:
            if card.card_type == CardType.TOY:
                # Check direct attack eligibility:
                # Direct attacks are only allowed when opponent has NO cards in play
                if not opponent.has_cards_in_play() and engine.can_tussle(card, None, player)[0]:
                    # Can do direct attack
                    cost = engine.calculate_tussle_cost(card, player)
                    valid_actions.append(
                        ValidAction(
                            action_type="tussle",
                            card_name=card.name,
                            cost_cc=cost,
                            target_options=["direct_attack"],
                            description=f"{card.name} direct attack (Cost: {cost} CC)"
                        )
                    )
                
                # Check each potential defender
                if opponent:
                    for defender in opponent.in_play:
                        if engine.can_tussle(card, defender, player):
                            cost = engine.calculate_tussle_cost(card, player)
                            valid_actions.append(
                                ValidAction(
                                    action_type="tussle",
                                    card_name=card.name,
                                    cost_cc=cost,
                                    target_options=[defender.name],
                                    description=f"{card.name} tussle {defender.name} (Cost: {cost} CC)"
                                )
                            )
    
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
    
    # Get valid actions
    valid_actions = []
    
    # Can always end turn
    valid_actions.append(
        ValidAction(
            action_type="end_turn",
            description="End your turn"
        )
    )
    
    # Check which cards can be played
    for card in player.hand:
        if engine.can_play_card(card, player)[0]:  # can_play_card returns (bool, str)
            cost = engine.calculate_card_cost(card, player)
            valid_actions.append(
                ValidAction(
                    action_type="play_card",
                    card_name=card.name,
                    cost_cc=cost,
                    description=f"Play {card.name} (Cost: {cost} CC)"
                )
            )
    
    # Check which cards can tussle
    opponent = game_state.get_opponent(player_id)
    for card in player.in_play:
        if card.card_type == CardType.TOY:
            # Check direct attack eligibility:
            # Direct attacks are only allowed when opponent has NO cards in play
            if not opponent.has_cards_in_play() and engine.can_tussle(card, None, player)[0]:
                # Can do direct attack
                cost = engine.calculate_tussle_cost(card, player)
                valid_actions.append(
                    ValidAction(
                        action_type="tussle",
                        card_name=card.name,
                        cost_cc=cost,
                        target_options=["direct_attack"],
                        description=f"{card.name} direct attack (Cost: {cost} CC)"
                    )
                )
            
            # Check each potential defender
            if opponent:
                for defender in opponent.in_play:
                    if engine.can_tussle(card, defender, player)[0]:
                        # Predict outcome to filter out guaranteed losses for AI
                        predicted = TussleResolver.predict_winner(game_state, card, defender)
                        
                        # Log prediction for debugging
                        logger.debug(
                            f"Tussle prediction: {card.name} vs {defender.name} = {predicted} "
                            f"(attacker {card.speed}/{card.strength}/{card.stamina} vs "
                            f"defender {defender.speed}/{defender.strength}/{defender.stamina})"
                        )
                        
                        # Skip guaranteed-loss tussles for AI consideration
                        # (still valid in UI, but AI shouldn't choose them)
                        if predicted == "defender":
                            # Skip this tussle - AI would lose
                            logger.debug(f"  → Skipping losing tussle for AI")
                            continue
                        
                        cost = engine.calculate_tussle_cost(card, player)
                        valid_actions.append(
                            ValidAction(
                                action_type="tussle",
                                card_name=card.name,
                                cost_cc=cost,
                                target_options=[defender.name],
                                description=f"{card.name} tussle {defender.name} (Cost: {cost} CC)"
                            )
                        )
    
    # Prefer tussles when ranking options (so AI prioritizes combat)
    # Sort by: tussles first, then by cost (lowest first)
    valid_actions.sort(key=lambda a: (a.action_type != "tussle", a.cost_cc if a.cost_cc is not None else 999))
    
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
            "card": action_details.get("card_name") or action_details.get("attacker_name"),
            "target": action_details.get("defender_name"),
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
            card_name = action_details["card_name"]
            card = next((c for c in player.hand if c.name == card_name), None)
            
            if card is None:
                raise HTTPException(status_code=500, detail=f"AI selected invalid card: {card_name}")
            
            # Calculate cost before playing
            cost = engine.calculate_card_cost(card, player)
            
            success = engine.play_card(player, card)
            engine.check_state_based_actions()
            
            # Build description with card effect for Action cards
            description = f"Spent {cost} CC to play {card_name}"
            if card.is_action():
                description += f" ({card.effect_text})"
            
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
                message=f"AI played {card_name}",
                game_state={"turn": game_state.turn_number},
                ai_turn_summary=turn_summary
            )
        
        elif action_details["action_type"] == "tussle":
            attacker_name = action_details["attacker_name"]
            defender_name = action_details.get("defender_name")
            
            attacker = next((c for c in player.in_play if c.name == attacker_name), None)
            if attacker is None:
                raise HTTPException(status_code=500, detail=f"AI selected invalid attacker: {attacker_name}")
            
            defender = None
            if defender_name:
                defender = game_state.find_card_by_name(defender_name)
            
            # Calculate cost before tussle
            cost = engine.calculate_tussle_cost(attacker, player)
            
            success = engine.initiate_tussle(attacker, defender, player)
            engine.check_state_based_actions()
            
            # Log to play-by-play with cost
            target_desc = defender_name if defender_name else "opponent directly"
            game_state.add_play_by_play(
                player_name=player.name,
                action_type="tussle",
                description=f"Spent {cost} CC for {attacker_name} to tussle {target_desc}",
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
                message=f"AI initiated tussle: {attacker_name} vs {target_desc}",
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
