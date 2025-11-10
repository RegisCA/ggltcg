"""
Player action API routes.

Endpoints for playing cards, initiating tussles, ending turns, etc.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any

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
        success = engine.play_card(player, card, **kwargs)
        
        if not success:
            return ActionResponse(
                success=False,
                message="Failed to play card (insufficient CC or invalid target)"
            )
        
        # Check state-based actions
        engine.check_state_based_actions()
        
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
        defender = game_state.find_card_by_name(request.defender_name)
        if defender is None:
            raise HTTPException(
                status_code=400,
                detail=f"Defender '{request.defender_name}' not found"
            )
    
    # Initiate tussle
    try:
        success = engine.initiate_tussle(attacker, defender, player)
        
        if not success:
            return ActionResponse(
                success=False,
                message="Failed to initiate tussle (insufficient CC, invalid target, or card restrictions)"
            )
        
        # Check state-based actions
        engine.check_state_based_actions()
        
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
    
    # End turn
    try:
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
                # Check if can tussle
                if engine.can_tussle(card, None, player):
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
        if card.card_type.value == "TOY":
            # Check if can tussle
            if engine.can_tussle(card, None, player):
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
    
    # Get AI player and have it select an action
    try:
        ai_player = get_ai_player()
        action_index = ai_player.select_action(game_state, player_id, valid_actions)
        
        if action_index is None:
            # AI failed to select - default to end turn
            engine.end_turn()
            return ActionResponse(
                success=True,
                message="AI failed to select action, ended turn",
                game_state={
                    "turn": game_state.turn_number,
                    "active_player": game_state.active_player_id
                }
            )
        
        selected_action = valid_actions[action_index]
        action_details = ai_player.get_action_details(selected_action)
        
        # Execute the selected action
        if action_details["action_type"] == "end_turn":
            engine.end_turn()
            return ActionResponse(
                success=True,
                message=f"AI ended turn",
                game_state={
                    "turn": game_state.turn_number,
                    "active_player": game_state.active_player_id
                }
            )
        
        elif action_details["action_type"] == "play_card":
            card_name = action_details["card_name"]
            card = next((c for c in player.hand if c.name == card_name), None)
            
            if card is None:
                raise HTTPException(status_code=500, detail=f"AI selected invalid card: {card_name}")
            
            success = engine.play_card(player, card)
            engine.check_state_based_actions()
            
            return ActionResponse(
                success=success,
                message=f"AI played {card_name}",
                game_state={"turn": game_state.turn_number}
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
            
            success = engine.initiate_tussle(attacker, defender, player)
            engine.check_state_based_actions()
            
            # Check for victory
            winner = game_state.check_victory()
            if winner:
                return ActionResponse(
                    success=True,
                    message=f"AI tussle successful! {winner} wins!",
                    game_state={"winner": winner}
                )
            
            target_desc = defender_name if defender_name else "direct attack"
            return ActionResponse(
                success=success,
                message=f"AI initiated tussle: {attacker_name} vs {target_desc}",
                game_state={"turn": game_state.turn_number}
            )
        
        else:
            raise HTTPException(status_code=500, detail=f"Unknown action type: {action_details['action_type']}")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI turn failed: {str(e)}")
