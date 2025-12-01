"""
Lobby routes for multiplayer game matchmaking.

Handles game creation, joining, and status checking for human vs human games.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional
import logging

from api.game_service import get_game_service
from api.game_codes import find_game_by_code, is_game_code_valid

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/games/lobby", tags=["lobby"])


# Request/Response Models

class CreateLobbyRequest(BaseModel):
    """Request to create a new lobby (waiting for player 2)."""
    player1_id: str = Field(..., min_length=1, max_length=255, description="Player 1's Google ID")
    player1_name: str = Field(..., min_length=1, max_length=50, description="Player 1's display name")


class CreateLobbyResponse(BaseModel):
    """Response after creating a lobby."""
    game_id: str
    game_code: str = Field(..., description="6-character code to share with player 2")
    player1_id: str
    player1_name: str
    status: str = Field(..., description="Game status (waiting_for_player)")


class JoinLobbyRequest(BaseModel):
    """Request to join an existing lobby."""
    player2_id: str = Field(..., min_length=1, max_length=255, description="Player 2's Google ID")
    player2_name: str = Field(..., min_length=1, max_length=50, description="Player 2's display name")


class JoinLobbyResponse(BaseModel):
    """Response after joining a lobby."""
    game_id: str
    game_code: str
    player1_id: str
    player1_name: str
    player2_id: str
    player2_name: str
    status: str = Field(..., description="Game status (deck_selection)")


class LobbyStatusResponse(BaseModel):
    """Current status of a lobby."""
    game_id: str
    game_code: str
    player1_id: str
    player1_name: str
    player2_id: Optional[str] = None
    player2_name: Optional[str] = None
    status: str
    ready_to_start: bool = Field(..., description="True if both players joined and selected decks")


class StartGameRequest(BaseModel):
    """Request to start a game (both players have selected decks)."""
    player_id: str = Field(..., description="Player ID (player1_id or player2_id)")
    deck: list[str] = Field(..., min_length=6, max_length=6, description="6 card names")


class StartGameResponse(BaseModel):
    """Response after starting a game."""
    game_id: str
    status: str = Field(..., description="Game status (active)")
    first_player_id: str
    game_state: dict


# Endpoints

@router.post("/create", response_model=CreateLobbyResponse)
def create_lobby(request: CreateLobbyRequest):
    """
    Create a new game lobby (Player 1 creates and waits for Player 2).
    
    Returns a 6-character game code that Player 2 can use to join.
    """
    service = get_game_service()
    
    try:
        # Create lobby game
        game_id, game_code = service.create_lobby(
            player1_id=request.player1_id,
            player1_name=request.player1_name
        )
        
        logger.info(f"Lobby created: {game_id}, code: {game_code}, player: {request.player1_name} ({request.player1_id})")
        
        return CreateLobbyResponse(
            game_id=game_id,
            game_code=game_code,
            player1_id=request.player1_id,
            player1_name=request.player1_name,
            status="waiting_for_player"
        )
    except Exception as e:
        logger.error(f"Failed to create lobby: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create lobby: {str(e)}")


@router.post("/{game_code}/join", response_model=JoinLobbyResponse)
def join_lobby(game_code: str, request: JoinLobbyRequest):
    """
    Join an existing game lobby (Player 2 joins using game code).
    
    After joining, both players proceed to deck selection.
    """
    # Validate code format
    if not is_game_code_valid(game_code):
        raise HTTPException(status_code=400, detail="Invalid game code format")
    
    service = get_game_service()
    
    try:
        # Join the lobby
        game_id, player1_id, player1_name = service.join_lobby(
            game_code=game_code.upper(),
            player2_id=request.player2_id,
            player2_name=request.player2_name
        )
        
        logger.info(f"Player joined lobby: {game_id}, code: {game_code}, player: {request.player2_name} ({request.player2_id})")
        
        return JoinLobbyResponse(
            game_id=game_id,
            game_code=game_code.upper(),
            player1_id=player1_id,
            player1_name=player1_name,
            player2_id=request.player2_id,
            player2_name=request.player2_name,
            status="deck_selection"
        )
    except ValueError as e:
        # Game not found or already full
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to join lobby: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to join lobby: {str(e)}")


@router.get("/{game_code}/status", response_model=LobbyStatusResponse)
def get_lobby_status(game_code: str):
    """
    Get the current status of a lobby.
    
    Use this to check if player 2 has joined.
    """
    # Validate code format
    if not is_game_code_valid(game_code):
        raise HTTPException(status_code=400, detail="Invalid game code format")
    
    service = get_game_service()
    
    try:
        status = service.get_lobby_status(game_code.upper())
        
        if not status:
            raise HTTPException(status_code=404, detail="Lobby not found")
        
        return LobbyStatusResponse(**status)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get lobby status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get lobby status: {str(e)}")


@router.post("/{game_code}/start", response_model=StartGameResponse)
def start_game(game_code: str, request: StartGameRequest):
    """
    Start a game after both players have selected their decks.
    
    This should be called twice - once by each player with their deck.
    The game starts when both players have submitted their decks.
    """
    # Validate code format
    if not is_game_code_valid(game_code):
        raise HTTPException(status_code=400, detail="Invalid game code format")
    
    service = get_game_service()
    
    try:
        result = service.start_lobby_game(
            game_code=game_code.upper(),
            player_id=request.player_id,
            deck=request.deck
        )
        
        logger.info(f"Game start requested: {game_code}, player: {request.player_id}, ready: {result['ready']}")
        
        if result['ready']:
            # Game is now active
            return StartGameResponse(
                game_id=result['game_id'],
                status="active",
                first_player_id=result['first_player_id'],
                game_state=result['game_state']
            )
        else:
            # Waiting for other player
            return StartGameResponse(
                game_id=result['game_id'],
                status="deck_selection",
                first_player_id="",
                game_state={}
            )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to start game: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start game: {str(e)}")
