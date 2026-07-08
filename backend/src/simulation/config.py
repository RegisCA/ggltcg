"""Configuration dataclasses for the simulation system."""

import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum

# Suggested AI models for simulation presets.
SUPPORTED_MODELS = [
    "gemini-flash-lite-latest",
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash",
    "llama-3.1-8b-instant",
    "llama-3.3-70b-versatile",
    "openai/gpt-oss-20b",
]


def is_valid_model_name(model_name: str) -> bool:
    """Validate a simulation model name without provider-specific allowlists."""
    return bool(model_name and model_name.strip())


def default_simulation_model() -> str:
    """The model simulations use when none is specified.

    Follows the same resolution as live games (GEMINI_MODEL env var, then the
    provider default) so benchmarking runs against the model players actually
    face, not a hardcoded snapshot.
    """
    from game_engine.ai.providers import DEFAULT_MODEL

    return os.getenv("GEMINI_MODEL") or DEFAULT_MODEL


class SimulationStatus(str, Enum):
    """Status of a simulation run."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"
    BUDGET_EXHAUSTED = "budget_exhausted"


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
class TurnCharge:
    """Charge tracking for a single turn."""
    turn: int
    player_id: str
    charge_start: int  # Charge at start of turn
    charge_gained: int  # Charge gained during turn
    charge_spent: int  # Charge spent during turn
    charge_end: int  # Charge at end of turn

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "turn": self.turn,
            "player_id": self.player_id,
            "charge_start": self.charge_start,
            "charge_gained": self.charge_gained,
            "charge_spent": self.charge_spent,
            "charge_end": self.charge_end,
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
    charge_tracking: list[TurnCharge]
    action_log: list[dict]
    error_message: Optional[str] = None
    # AI performance tracking
    total_charge_spent_by_winner: int = 0  # Charge efficiency metric
    no_sequences_count: int = 0  # Turns where the enumerator found no legal sequence

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
            "charge_tracking": [charge.to_dict() for charge in self.charge_tracking],
            "action_log": self.action_log,
            "error_message": self.error_message,
            "total_charge_spent_by_winner": self.total_charge_spent_by_winner,
            "no_sequences_count": self.no_sequences_count,
        }


@dataclass
class SimulationConfig:
    """Configuration for a simulation run."""
    deck_names: list[str]  # List of deck names to use (will run all combinations)
    player1_model: str = field(default_factory=default_simulation_model)
    player2_model: str = field(default_factory=default_simulation_model)
    iterations_per_matchup: int = 10  # Games per deck matchup
    max_turns: int = 20  # Turn limit before declaring draw
    parallel_games: int = 10  # Number of games to run concurrently
    rpm: Optional[int] = None  # Requests-per-minute limit forwarded to the rate limiter
    daily_request_budget: Optional[int] = None  # Daily API request budget (None = unlimited)

    def get_matchups(self) -> list[tuple[str, str]]:
        """
        Generate all deck matchups (n² total: all pairs including mirrors and both directions).
        
        Since Player 1 always goes first, A vs B is different from B vs A.
        This generates all n² matchups for a complete matrix.
        
        Returns:
            List of (deck1_name, deck2_name) tuples
        """
        matchups = []
        for deck1 in self.deck_names:
            for deck2 in self.deck_names:
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
            "parallel_games": self.parallel_games,
            "rpm": self.rpm,
            "daily_request_budget": self.daily_request_budget,
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
    resets_at: Optional[datetime] = None  # when a budget exhaustion resets (if paused for that reason)

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
            "resets_at": self.resets_at.isoformat() if self.resets_at else None,
        }
