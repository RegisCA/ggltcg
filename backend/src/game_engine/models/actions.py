"""
Game action data structures.

This module defines structured types for all game actions, replacing the previous
approach of using loose kwargs. These types provide:
- Clear documentation of required vs optional fields
- Type checking at compile time
- Self-documenting code
- Consistent use of card IDs throughout

All actions inherit from GameAction base class and use card IDs (not names or objects)
for referencing cards.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class ActionType(Enum):
    """Types of actions that can be performed in the game."""
    PLAY_CARD = "play_card"
    TUSSLE = "tussle"
    END_TURN = "end_turn"
    ACTIVATE_ABILITY = "activate_ability"


@dataclass
class GameAction:
    """
    Base class for all game actions.
    
    All game actions include the player performing the action and the type of action.
    Subclasses add additional fields specific to that action type.
    """
    player_id: str
    action_type: ActionType


@dataclass
class PlayCardAction(GameAction):
    """
    Action to play a card from hand.
    
    Attributes:
        player_id: ID of player playing the card
        card_id: Unique ID of the card being played
        target_ids: List of target card IDs (for cards like Twist, Wake, Copy, Sun)
        alternative_cost_card_id: Card ID to use for alternative cost (e.g., Ballaber)
        
    Examples:
        # Play a simple card with no targets
        action = PlayCardAction(player_id="alice", card_id="card-123")
        
        # Play Twist targeting opponent's Ka
        action = PlayCardAction(
            player_id="alice",
            card_id="twist-456",
            target_ids=["ka-789"]
        )
        
        # Play Ballaber with alternative cost
        action = PlayCardAction(
            player_id="alice",
            card_id="ballaber-123",
            alternative_cost_card_id="snuggles-456"
        )
    """
    card_id: str
    target_ids: List[str] = field(default_factory=list)
    alternative_cost_card_id: Optional[str] = None
    
    def __post_init__(self):
        self.action_type = ActionType.PLAY_CARD


@dataclass
class TussleAction(GameAction):
    """
    Action to initiate a tussle between two Toys.
    
    Attributes:
        player_id: ID of player initiating the tussle
        attacker_id: Unique ID of the attacking Toy
        defender_id: Unique ID of the defending Toy
        
    Example:
        action = TussleAction(
            player_id="alice",
            attacker_id="knight-123",
            defender_id="ka-456"
        )
    """
    attacker_id: str
    defender_id: str
    
    def __post_init__(self):
        self.action_type = ActionType.TUSSLE


@dataclass
class EndTurnAction(GameAction):
    """
    Action to end the current player's turn.
    
    Attributes:
        player_id: ID of player ending their turn
        
    Example:
        action = EndTurnAction(player_id="alice")
    """
    
    def __post_init__(self):
        self.action_type = ActionType.END_TURN


@dataclass
class ActivateAbilityAction(GameAction):
    """
    Action to activate a card's ability (e.g., Archer's sleep ability).
    
    Attributes:
        player_id: ID of player activating the ability
        card_id: Unique ID of the card with the ability
        target_ids: List of target card IDs (if ability requires targets)
        
    Example:
        # Archer ability to sleep a target Toy
        action = ActivateAbilityAction(
            player_id="alice",
            card_id="archer-123",
            target_ids=["knight-456"]
        )
    """
    card_id: str
    target_ids: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        self.action_type = ActionType.ACTIVATE_ABILITY
