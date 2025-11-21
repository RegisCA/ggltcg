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


class RandomDeckRequest(BaseModel):
    """Request to generate a random deck."""
    num_toys: int = Field(..., ge=0, le=6, description="Number of Toy cards (0-6)")
    num_actions: int = Field(..., ge=0, le=6, description="Number of Action cards (0-6)")


class RandomDeckResponse(BaseModel):
    """Response with randomly generated deck."""
    deck: list[str] = Field(..., description="List of card names")
    num_toys: int = Field(..., description="Number of Toy cards in deck")
    num_actions: int = Field(..., description="Number of Action cards in deck")


class NarrativeRequest(BaseModel):
    """Request to generate narrative play-by-play."""
    play_by_play: List[Dict[str, Any]] = Field(..., description="Play-by-play entries from the game")


class NarrativeResponse(BaseModel):
    """Response with narrative story."""
    narrative: str = Field(..., description="Bedtime story narrative of the game")


class CardDataResponse(BaseModel):
    """Response with card information from CSV."""
    name: str
    card_type: str  # "Toy" or "Action"
    cost: int  # -1 for variable cost (Copy)
    effect: str
    speed: Optional[int] = None
    strength: Optional[int] = None
    stamina: Optional[int] = None
    primary_color: str
    accent_color: str


# ============================================================================
# PLAYER ACTIONS
# ============================================================================

class PlayCardRequest(BaseModel):
    """Request to play a card from hand."""
    player_id: str = Field(..., description="ID of player playing the card")
    card_id: str = Field(..., description="ID of card to play")
    target_card_id: Optional[str] = Field(None, description="Target card ID for effects that require targets")
    target_card_ids: Optional[List[str]] = Field(None, description="Multiple target card IDs (e.g., Sun)")
    alternative_cost_card_id: Optional[str] = Field(None, description="Card ID to sleep for alternative cost (e.g., Ballaber)")


class TussleRequest(BaseModel):
    """Request to initiate a tussle."""
    player_id: str = Field(..., description="ID of player initiating tussle")
    attacker_id: str = Field(..., description="ID of attacking card")
    defender_id: Optional[str] = Field(None, description="ID of defending card (None for direct attack)")


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
    id: str  # Unique card instance ID
    name: str
    card_type: str
    cost: int
    zone: str
    owner: str
    controller: str
    speed: Optional[int] = None  # Current effective speed (with buffs)
    strength: Optional[int] = None  # Current effective strength (with buffs)
    stamina: Optional[int] = None  # Current effective max stamina (with buffs)
    current_stamina: Optional[int] = None  # Current stamina (can be damaged)
    base_speed: Optional[int] = None  # Original speed from card definition
    base_strength: Optional[int] = None  # Original strength from card definition
    base_stamina: Optional[int] = None  # Original stamina from card definition
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
    play_by_play: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Complete play-by-play history of all actions taken in the game"
    )


class ValidAction(BaseModel):
    """Description of a valid action a player can take."""
    action_type: str  # "play_card", "tussle", "end_turn", "activate_ability"
    card_id: Optional[str] = None  # Unique ID of the card for this action
    card_name: Optional[str] = None  # Display name (for UI convenience)
    target_options: Optional[List[str]] = Field(None, description="List of valid target card IDs")
    max_targets: Optional[int] = Field(None, description="Maximum number of targets to select (e.g., 2 for Sun)")
    min_targets: Optional[int] = Field(None, description="Minimum number of targets to select (e.g., 0 for optional targeting)")
    cost_cc: Optional[int] = None
    alternative_cost_available: Optional[bool] = Field(None, description="Whether an alternative cost is available (e.g., Ballaber)")
    alternative_cost_options: Optional[List[str]] = Field(None, description="Card IDs that can be slept for alternative cost")
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
