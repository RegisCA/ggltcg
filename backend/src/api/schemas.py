"""
Pydantic schemas for API request/response validation.

These schemas define the structure of data exchanged between client and server.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# ============================================================================
# GAME CREATION
# ============================================================================

class PlayerCreate(BaseModel):
    """Schema for creating a player."""
    player_id: str = Field(..., description="Unique identifier for the player")
    name: str = Field(..., description="Display name for the player")
    deck: List[str] = Field(..., description="List of card names in player's deck")


class GameCreate(BaseModel):
    """Schema for creating a new game."""
    player1: PlayerCreate
    player2: PlayerCreate
    first_player_id: Optional[str] = Field(None, description="ID of player who goes first (random if not specified)")


class GameCreated(BaseModel):
    """Response after creating a game."""
    game_id: str
    message: str = "Game created successfully"


# ============================================================================
# PLAYER ACTIONS
# ============================================================================

class PlayCardRequest(BaseModel):
    """Request to play a card from hand."""
    player_id: str = Field(..., description="ID of player playing the card")
    card_name: str = Field(..., description="Name of card to play")
    target_card_name: Optional[str] = Field(None, description="Target card name for effects that require targets")
    target_card_names: Optional[List[str]] = Field(None, description="Multiple target card names (e.g., Sun)")


class TussleRequest(BaseModel):
    """Request to initiate a tussle."""
    player_id: str = Field(..., description="ID of player initiating tussle")
    attacker_name: str = Field(..., description="Name of attacking card")
    defender_name: Optional[str] = Field(None, description="Name of defending card (None for direct attack)")


class EndTurnRequest(BaseModel):
    """Request to end the current turn."""
    player_id: str = Field(..., description="ID of player ending their turn")


class ActivateAbilityRequest(BaseModel):
    """Request to activate a card's ability."""
    player_id: str = Field(..., description="ID of player activating ability")
    card_name: str = Field(..., description="Name of card with ability")
    target_card_name: Optional[str] = Field(None, description="Target for the ability")
    amount: Optional[int] = Field(1, description="Amount parameter (e.g., for Archer)")


class ActionResponse(BaseModel):
    """Generic response for player actions."""
    success: bool
    message: str
    game_state: Optional[Dict[str, Any]] = None
    ai_turn_summary: Optional[Dict[str, Any]] = Field(
        None, 
        description="Summary of AI's turn actions (action type, card, target, cost, reasoning)"
    )


# ============================================================================
# GAME STATE
# ============================================================================

class CardState(BaseModel):
    """Current state of a card."""
    name: str
    card_type: str
    cost: int
    zone: str
    owner: str
    controller: str
    speed: Optional[int] = None
    strength: Optional[int] = None
    stamina: Optional[int] = None
    current_stamina: Optional[int] = None
    is_sleeped: bool = False
    primary_color: str = "#C74444"
    accent_color: str = "#C74444"


class PlayerState(BaseModel):
    """Current state of a player."""
    player_id: str
    name: str
    cc: int
    hand_count: int  # Don't reveal hand to opponent
    hand: Optional[List[CardState]] = None  # Only for the player themselves
    in_play: List[CardState]
    sleep_zone: List[CardState]
    direct_attacks_this_turn: int


class GameStateResponse(BaseModel):
    """Complete game state."""
    game_id: str
    turn_number: int
    phase: str
    active_player_id: str
    first_player_id: str
    players: Dict[str, PlayerState]
    winner: Optional[str] = None
    is_game_over: bool = False


class ValidAction(BaseModel):
    """Description of a valid action a player can take."""
    action_type: str  # "play_card", "tussle", "end_turn", "activate_ability"
    card_name: Optional[str] = None
    target_options: Optional[List[str]] = None
    cost_cc: Optional[int] = None
    description: str


class ValidActionsResponse(BaseModel):
    """List of valid actions for the active player."""
    game_id: str
    player_id: str
    valid_actions: List[ValidAction]


# ============================================================================
# ERROR RESPONSES
# ============================================================================

class ErrorResponse(BaseModel):
    """Error response."""
    error: str
    details: Optional[str] = None
