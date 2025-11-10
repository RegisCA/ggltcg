"""Game state model for GGLTCG game engine."""
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum
from .player import Player
from .card import Card


class Phase(Enum):
    """Turn phases."""
    START = "Start"
    MAIN = "Main"
    END = "End"


@dataclass
class GameState:
    """
    Represents the complete state of a game.
    
    Attributes:
        game_id: Unique identifier for this game
        players: Dictionary mapping player_id to Player objects
        active_player_id: ID of the player whose turn it is
        turn_number: Current turn number (starts at 1)
        phase: Current phase of the turn
        first_player_id: ID of the player who went first
        winner_id: ID of the winning player (None if game ongoing)
        game_log: List of game events for history
    """
    game_id: str
    players: Dict[str, Player]
    active_player_id: str
    turn_number: int = 1
    phase: Phase = Phase.START
    first_player_id: str = ""
    winner_id: Optional[str] = None
    game_log: List[str] = field(default_factory=list)
    
    def get_active_player(self) -> Player:
        """Get the active player object."""
        return self.players[self.active_player_id]
    
    def get_opponent(self, player_id: str) -> Player:
        """
        Get the opponent of the specified player.
        
        Args:
            player_id: ID of the player
            
        Returns:
            The opponent Player object
        """
        for pid, player in self.players.items():
            if pid != player_id:
                return player
        raise ValueError("Could not find opponent")
    
    def get_opponent_of_active(self) -> Player:
        """Get the opponent of the active player."""
        return self.get_opponent(self.active_player_id)
    
    def is_first_turn(self) -> bool:
        """Check if this is the first turn of the game."""
        return self.turn_number == 1
    
    def is_active_player(self, player_id: str) -> bool:
        """Check if the specified player is the active player."""
        return player_id == self.active_player_id
    
    def log_event(self, message: str):
        """Add an event to the game log."""
        self.game_log.append(f"Turn {self.turn_number} ({self.phase.value}): {message}")
    
    def check_victory(self) -> Optional[str]:
        """
        Check if any player has won the game.
        
        Returns:
            Player ID of winner if game is won, None otherwise
        """
        for player_id, player in self.players.items():
            opponent = self.get_opponent(player_id)
            if opponent.all_cards_sleeped():
                self.winner_id = player_id
                self.log_event(f"{player.name} wins! All opponent's cards are sleeped.")
                return player_id
        return None
    
    def get_all_cards_in_play(self) -> List[Card]:
        """Get all cards currently in play across both players."""
        cards = []
        for player in self.players.values():
            cards.extend(player.in_play)
        return cards
    
    def find_card_by_name(self, name: str) -> Optional[Card]:
        """
        Find a card by name across all zones and players.
        
        Args:
            name: Card name to search for
            
        Returns:
            Card if found, None otherwise
        """
        for player in self.players.values():
            card = player.get_card_by_name(name)
            if card:
                return card
        return None
    
    def to_dict(self, requesting_player_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Serialize game state to dictionary for API responses.
        
        Args:
            requesting_player_id: If provided, reveal that player's hand
            
        Returns:
            Dictionary representation of game state
        """
        return {
            "game_id": self.game_id,
            "turn_number": self.turn_number,
            "phase": self.phase.value,
            "active_player_id": self.active_player_id,
            "first_player_id": self.first_player_id,
            "winner_id": self.winner_id,
            "players": {
                pid: player.to_dict(reveal_hand=(pid == requesting_player_id))
                for pid, player in self.players.items()
            },
            "game_log": self.game_log[-20:],  # Last 20 events only
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GameState':
        """Deserialize game state from dictionary."""
        return cls(
            game_id=data["game_id"],
            players={
                pid: Player.from_dict(pdata)
                for pid, pdata in data["players"].items()
            },
            active_player_id=data["active_player_id"],
            turn_number=data["turn_number"],
            phase=Phase(data["phase"]),
            first_player_id=data["first_player_id"],
            winner_id=data.get("winner_id"),
            game_log=data.get("game_log", []),
        )
