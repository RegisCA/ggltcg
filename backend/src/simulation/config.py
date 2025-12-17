"""Configuration dataclasses for the simulation system."""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

# Supported AI models for simulation
SUPPORTED_MODELS = [
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
]


class SimulationStatus(str, Enum):
    """Status of a simulation run."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class GameOutcome(str, Enum):
    """Outcome of a simulated game."""
    PLAYER1_WIN = "player1_win"
    PLAYER2_WIN = "player2_win"
    DRAW = "draw"  # Hit turn limit


@dataclass
class DeckConfig:
    """Configuration for a simulation deck."""
    name: str
    description: str
    cards: list[str]  # List of 6 card names
    
    def __post_init__(self) -> None:
        """Validate deck has exactly 6 cards."""
        if len(self.cards) != 6:
            raise ValueError(
                f"Deck '{self.name}' must have exactly 6 cards, got {len(self.cards)}"
            )


@dataclass
class TurnCC:
    """CC tracking for a single turn."""
    turn: int
    player_id: str
    cc_start: int  # CC at start of turn
    cc_gained: int  # CC gained during turn
    cc_spent: int  # CC spent during turn
    cc_end: int  # CC at end of turn
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "turn": self.turn,
            "player_id": self.player_id,
            "cc_start": self.cc_start,
            "cc_gained": self.cc_gained,
            "cc_spent": self.cc_spent,
            "cc_end": self.cc_end,
        }


@dataclass
class GameResult:
    """Result of a single simulated game."""
    game_number: int
    deck1_name: str
    deck2_name: str
    player1_model: str
    player2_model: str
    outcome: GameOutcome
    winner_deck: Optional[str]  # None for draw
    turn_count: int
    duration_ms: int
    cc_tracking: list[TurnCC]
    action_log: list[dict]
    error_message: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "game_number": self.game_number,
            "deck1_name": self.deck1_name,
            "deck2_name": self.deck2_name,
            "player1_model": self.player1_model,
            "player2_model": self.player2_model,
            "outcome": self.outcome.value,
            "winner_deck": self.winner_deck,
            "turn_count": self.turn_count,
            "duration_ms": self.duration_ms,
            "cc_tracking": [cc.to_dict() for cc in self.cc_tracking],
            "action_log": self.action_log,
            "error_message": self.error_message,
        }


@dataclass
class SimulationConfig:
    """Configuration for a simulation run."""
    deck_names: list[str]  # List of deck names to use (will run all combinations)
    player1_model: str = "gemini-2.0-flash"
    player2_model: str = "gemini-2.5-flash"
    iterations_per_matchup: int = 10  # Games per deck matchup
    max_turns: int = 40  # Turn limit before declaring draw
    
    def get_matchups(self) -> list[tuple[str, str]]:
        """
        Generate all deck matchups including mirrors.
        
        Returns:
            List of (deck1_name, deck2_name) tuples
        """
        matchups = []
        for i, deck1 in enumerate(self.deck_names):
            for deck2 in self.deck_names[i:]:  # Include mirror matches
                matchups.append((deck1, deck2))
        return matchups
    
    def total_games(self) -> int:
        """Calculate total number of games in this simulation."""
        return len(self.get_matchups()) * self.iterations_per_matchup
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "deck_names": self.deck_names,
            "player1_model": self.player1_model,
            "player2_model": self.player2_model,
            "iterations_per_matchup": self.iterations_per_matchup,
            "max_turns": self.max_turns,
        }


@dataclass
class MatchupStats:
    """Aggregated statistics for a single deck matchup."""
    deck1_name: str
    deck2_name: str
    games_played: int = 0
    deck1_wins: int = 0
    deck2_wins: int = 0
    draws: int = 0
    total_turns: int = 0
    total_duration_ms: int = 0
    
    @property
    def deck1_win_rate(self) -> float:
        """Win rate for deck1."""
        if self.games_played == 0:
            return 0.0
        return self.deck1_wins / self.games_played
    
    @property
    def deck2_win_rate(self) -> float:
        """Win rate for deck2."""
        if self.games_played == 0:
            return 0.0
        return self.deck2_wins / self.games_played
    
    @property
    def avg_turns(self) -> float:
        """Average turns per game."""
        if self.games_played == 0:
            return 0.0
        return self.total_turns / self.games_played
    
    @property
    def avg_duration_ms(self) -> float:
        """Average game duration in milliseconds."""
        if self.games_played == 0:
            return 0.0
        return self.total_duration_ms / self.games_played
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "deck1_name": self.deck1_name,
            "deck2_name": self.deck2_name,
            "games_played": self.games_played,
            "deck1_wins": self.deck1_wins,
            "deck2_wins": self.deck2_wins,
            "draws": self.draws,
            "deck1_win_rate": round(self.deck1_win_rate, 3),
            "deck2_win_rate": round(self.deck2_win_rate, 3),
            "avg_turns": round(self.avg_turns, 1),
            "avg_duration_ms": round(self.avg_duration_ms, 0),
        }


@dataclass
class SimulationResult:
    """Complete results from a simulation run."""
    run_id: int
    config: SimulationConfig
    status: SimulationStatus
    total_games: int
    completed_games: int
    matchup_stats: dict[str, MatchupStats] = field(default_factory=dict)  # key: "deck1_vs_deck2"
    game_results: list[GameResult] = field(default_factory=list)
    error_message: Optional[str] = None
    
    def add_game_result(self, result: GameResult) -> None:
        """Add a game result and update matchup stats."""
        self.game_results.append(result)
        self.completed_games += 1
        
        # Update matchup stats
        matchup_key = f"{result.deck1_name}_vs_{result.deck2_name}"
        if matchup_key not in self.matchup_stats:
            self.matchup_stats[matchup_key] = MatchupStats(
                deck1_name=result.deck1_name,
                deck2_name=result.deck2_name
            )
        
        stats = self.matchup_stats[matchup_key]
        stats.games_played += 1
        stats.total_turns += result.turn_count
        stats.total_duration_ms += result.duration_ms
        
        if result.outcome == GameOutcome.PLAYER1_WIN:
            stats.deck1_wins += 1
        elif result.outcome == GameOutcome.PLAYER2_WIN:
            stats.deck2_wins += 1
        else:
            stats.draws += 1
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "run_id": self.run_id,
            "config": self.config.to_dict(),
            "status": self.status.value,
            "total_games": self.total_games,
            "completed_games": self.completed_games,
            "matchup_stats": {k: v.to_dict() for k, v in self.matchup_stats.items()},
            "game_results": [g.to_dict() for g in self.game_results],
            "error_message": self.error_message,
        }
