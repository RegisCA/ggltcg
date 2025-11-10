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
    kwargs: Dict[str, Any] = {"player": player}
    
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
            if engine.can_play_card(player, card):
                cost = engine.calculate_card_cost(player, card)
                valid_actions.append(
                    ValidAction(
                        action_type="play_card",
                        card_name=card.name,
                        cost_cc=cost,
                        description=f"Play {card.name} (Cost: {cost} CC)"
                    )
                )
        
        # Check which cards can tussle
        opponent = game_state.get_opponent(player)
        for card in player.in_play:
            if card.card_type == "TOY":
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
