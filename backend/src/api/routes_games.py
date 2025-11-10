"""
Game management API routes.

Endpoints for creating, retrieving, and deleting games.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from api.schemas import (
    GameCreate,
    GameCreated,
    GameStateResponse,
    PlayerState,
    CardState,
    ErrorResponse,
)
from api.game_service import get_game_service
from game_engine.models.card import Zone

router = APIRouter(prefix="/games", tags=["games"])


@router.post("", response_model=GameCreated, status_code=201)
async def create_game(game_data: GameCreate) -> GameCreated:
    """
    Create a new game with two players.
    
    - **player1**: First player configuration (id, name, deck)
    - **player2**: Second player configuration (id, name, deck)
    - **first_player_id**: Optional - which player goes first (random if not specified)
    
    Returns the created game ID.
    """
    service = get_game_service()
    
    try:
        game_id, engine = service.create_game(
            player1_id=game_data.player1.player_id,
            player1_name=game_data.player1.name,
            player1_deck=game_data.player1.deck,
            player2_id=game_data.player2.player_id,
            player2_name=game_data.player2.name,
            player2_deck=game_data.player2.deck,
            first_player_id=game_data.first_player_id,
        )
        
        return GameCreated(game_id=game_id)
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create game: {str(e)}")


@router.get("/{game_id}", response_model=GameStateResponse)
async def get_game_state(game_id: str, player_id: str = None) -> GameStateResponse:
    """
    Get the current state of a game.
    
    - **game_id**: The game ID
    - **player_id**: Optional - if provided, includes that player's hand
    
    Returns complete game state including player info, cards in play, etc.
    """
    service = get_game_service()
    engine = service.get_game(game_id)
    
    if engine is None:
        raise HTTPException(status_code=404, detail=f"Game {game_id} not found")
    
    game_state = engine.game_state
    
    # Convert to response format
    players_state = {}
    for pid, player in game_state.players.items():
        # Convert cards to CardState
        in_play_cards = [_card_to_state(c, engine) for c in player.in_play]
        sleep_cards = [_card_to_state(c, engine) for c in player.sleep_zone]
        
        # Only include hand if player_id matches
        hand_cards = None
        if player_id == pid:
            hand_cards = [_card_to_state(c, engine) for c in player.hand]
        
        players_state[pid] = PlayerState(
            player_id=pid,
            name=player.name,
            cc=player.cc,
            hand_count=len(player.hand),
            hand=hand_cards,
            in_play=in_play_cards,
            sleep_zone=sleep_cards,
            direct_attacks_this_turn=player.direct_attacks_this_turn,
        )
    
    # Check if game is over
    winner = game_state.check_victory()
    
    return GameStateResponse(
        game_id=game_id,
        turn_number=game_state.turn_number,
        phase=game_state.phase.value,
        active_player_id=game_state.active_player_id,
        first_player_id=game_state.first_player_id,
        players=players_state,
        winner=winner,
        is_game_over=winner is not None,
    )


@router.delete("/{game_id}")
async def delete_game(game_id: str) -> Dict[str, str]:
    """
    Delete a game.
    
    - **game_id**: The game ID to delete
    
    Returns success message.
    """
    service = get_game_service()
    
    if not service.delete_game(game_id):
        raise HTTPException(status_code=404, detail=f"Game {game_id} not found")
    
    return {"message": f"Game {game_id} deleted successfully"}


def _card_to_state(card, engine) -> CardState:
    """Convert a Card to CardState with current stats."""
    # Get modified stats if applicable
    current_speed = None
    current_strength = None
    current_stamina = None
    
    if card.card_type == "TOY":
        current_speed = engine.get_card_stat(card, "speed")
        current_strength = engine.get_card_stat(card, "strength")
        current_stamina = card.current_stamina
    
    return CardState(
        name=card.name,
        card_type=card.card_type,
        cost=card.cost,
        zone=card.zone.value,
        owner=card.owner,
        controller=card.controller,
        speed=current_speed,
        strength=current_strength,
        stamina=card.stamina if card.card_type == "TOY" else None,
        current_stamina=current_stamina,
        is_sleeped=(card.zone == Zone.SLEEP),
    )
