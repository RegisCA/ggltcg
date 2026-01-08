"""
SQLAlchemy ORM models for database persistence.

Defines the database schema using SQLAlchemy declarative models.
"""

from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, DateTime, Text, CheckConstraint, Index, ForeignKey, JSON
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import uuid

Base = declarative_base()

# Use JSON type for cross-database compatibility
# JSON works in both PostgreSQL and SQLite (JSONB is PostgreSQL-only)
# For production PostgreSQL, we could use JSONB for better performance,
# but JSON is sufficient and allows tests to run with SQLite
JSONType = JSON


class UserModel(Base):
    """
    Database model for authenticated users.
    
    Stores user information from Google OAuth for authentication and display.
    """
    __tablename__ = "users"
    
    # Primary key - Google ID (subject identifier from Google OAuth)
    google_id = Column(String(255), primary_key=True)
    
    # User profile information
    first_name = Column(String(255), nullable=False)
    custom_display_name = Column(String(255), nullable=True)
    
    # Favorite decks - array of 3 decks (each deck is array of 6 card names)
    # Stored as JSON for cross-database compatibility (SQLite + PostgreSQL)
    favorite_decks = Column(JSONType, nullable=True)
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # Indexes for efficient lookups
    __table_args__ = (
        Index('idx_users_display_name', 'custom_display_name'),
    )
    
    def __repr__(self):
        return f"<User(google_id={self.google_id}, name={self.display_name})>"
    
    @property
    def display_name(self) -> str:
        """Return custom display name if set, otherwise first name."""
        return self.custom_display_name or self.first_name


class GameModel(Base):
    """
    Database model for game sessions.
    
    Stores complete game state as JSONB for flexibility and minimal refactoring.
    Includes denormalized fields for efficient queries.
    """
    __tablename__ = "games"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # Player information (for queries and matchmaking)
    player1_id = Column(String(255), nullable=False, index=True)
    player1_name = Column(String(255), nullable=False)
    player2_id = Column(String(255), nullable=True, index=True)  # Nullable until P2 joins
    player2_name = Column(String(255), nullable=True)  # Nullable until P2 joins
    
    # Game code for lobby (6-character code for joining)
    game_code = Column(String(6), nullable=True, unique=True, index=True)
    
    # Game status
    status = Column(
        String(50),
        nullable=False,
        default="active",
        index=True
    )
    
    winner_id = Column(String(255), nullable=True)
    
    # Current turn info (denormalized for queries)
    turn_number = Column(Integer, nullable=False, default=1)
    active_player_id = Column(String(255), nullable=False)
    phase = Column(String(50), nullable=False, default="Start")
    
    # Full game state (JSONB for PostgreSQL, JSON for SQLite)
    game_state = Column(JSONType, nullable=False)
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "status IN ('waiting_for_player', 'deck_selection', 'active', 'completed', 'abandoned')",
            name="games_status_check"
        ),
        # Combined index for finding player's active games
        Index(
            'idx_games_player_active',
            'player1_id', 'player2_id', 'status'
        ),
        # Index for active player lookups
        Index(
            'idx_games_active_player',
            'active_player_id',
            postgresql_where=Column('status') == 'active'
        ),
    )
    
    def __repr__(self):
        return f"<Game(id={self.id}, status={self.status}, turn={self.turn_number})>"


class GameActionModel(Base):
    """
    Database model for individual game actions.
    
    Stores each action taken during a game for analytics and debugging.
    This table is optional for Phase 1 but included for future use.
    """
    __tablename__ = "game_actions"
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign key to game (using UUID type)
    game_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True
    )
    
    # Action metadata
    turn_number = Column(Integer, nullable=False)
    player_id = Column(String(255), nullable=False, index=True)
    action_type = Column(String(50), nullable=False, index=True)
    
    # Action details (JSONB for PostgreSQL, JSON for SQLite)
    action_data = Column(JSONType, nullable=False)
    
    # Result of action
    result_description = Column(Text, nullable=True)
    
    # Timestamp
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    
    # Indexes
    __table_args__ = (
        Index('idx_game_actions_turn', 'game_id', 'turn_number'),
    )
    
    def __repr__(self):
        return f"<GameAction(id={self.id}, game_id={self.game_id}, type={self.action_type})>"


class GameStatsModel(Base):
    """
    Database model for game statistics.
    
    Aggregated statistics for completed games, used for leaderboards.
    This table is optional for Phase 1 but included for future use.
    """
    __tablename__ = "game_stats"
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign key to game (unique - one stats record per game)
    game_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        unique=True
    )
    
    # Game outcome
    winner_id = Column(String(255), nullable=False, index=True)
    loser_id = Column(String(255), nullable=False, index=True)
    
    # Game metrics
    total_turns = Column(Integer, nullable=False)
    duration_seconds = Column(Integer, nullable=True)
    
    # Winner stats
    winner_cards_played = Column(Integer, nullable=True)
    winner_tussles_initiated = Column(Integer, nullable=True)
    winner_direct_attacks = Column(Integer, nullable=True)
    
    # Loser stats
    loser_cards_played = Column(Integer, nullable=True)
    loser_tussles_initiated = Column(Integer, nullable=True)
    loser_direct_attacks = Column(Integer, nullable=True)
    
    # Timestamp
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True
    )
    
    def __repr__(self):
        return f"<GameStats(id={self.id}, game_id={self.game_id}, winner={self.winner_id})>"


class AIDecisionLogModel(Base):
    """
    Database model for AI decision logs.
    
    Stores Gemini prompts and responses for debugging AI behavior.
    Retention: 6 hours (cleaned up by scheduled task).
    
    v3 additions (Issue #260):
    - ai_version: Which AI version (2 or 3)
    - turn_plan: Full TurnPlan JSON for v3 (stored with each action log entry)
    - plan_execution_status: "complete" or "fallback"
    - fallback_reason: Why fallback occurred (if any)
    - planned_action_index: Which action in the plan this log represents
    """
    __tablename__ = "ai_decision_logs"
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Game context
    game_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    turn_number = Column(Integer, nullable=False)
    player_id = Column(String(255), nullable=True)  # AI player ID in game
    
    # AI model info for tracking improvements
    model_name = Column(String(100), nullable=False)  # e.g., "gemini-2.0-flash"
    prompts_version = Column(String(20), nullable=False)  # e.g., "1.0"
    
    # Request/response data
    prompt = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    
    # Parsed action (for quick analysis)
    action_number = Column(Integer, nullable=True)
    reasoning = Column(Text, nullable=True)
    
    # v3 Turn Planning fields (Issue #260)
    ai_version = Column(Integer, nullable=True, default=2)  # 2 or 3
    turn_plan = Column(JSONType, nullable=True)  # Full TurnPlan JSON for v3
    plan_execution_status = Column(String(20), nullable=True)  # "complete" or "fallback"
    fallback_reason = Column(Text, nullable=True)  # Why fallback occurred
    planned_action_index = Column(Integer, nullable=True)  # Which action in the plan (0-based)
    
    # Timestamp for retention cleanup
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True  # Index for cleanup queries
    )
    
    def __repr__(self):
        return f"<AIDecisionLog(id={self.id}, game_id={self.game_id}, turn={self.turn_number}, v={self.ai_version})>"


class GamePlaybackModel(Base):
    """
    Database model for game playback data.
    
    Stores completed game summaries with starting decks and play-by-play.
    Retention: 24 hours (cleaned up by scheduled task).
    """
    __tablename__ = "game_playback"
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Game reference
    game_id = Column(UUID(as_uuid=True), nullable=False, unique=True, index=True)
    
    # Player info
    player1_id = Column(String(255), nullable=False)
    player1_name = Column(String(255), nullable=False)
    player2_id = Column(String(255), nullable=False)
    player2_name = Column(String(255), nullable=False)
    winner_id = Column(String(255), nullable=True, index=True)
    
    # Starting state (for reproduction)
    starting_deck_p1 = Column(JSONType, nullable=False)  # List of card names
    starting_deck_p2 = Column(JSONType, nullable=False)  # List of card names
    first_player_id = Column(String(255), nullable=False)
    
    # Game progression
    play_by_play = Column(JSONType, nullable=False)  # List of action entries
    turn_count = Column(Integer, nullable=False)
    
    # CC tracking per turn (Issue #252)
    # List of {turn, player_id, cc_start, cc_gained, cc_spent, cc_end}
    cc_tracking = Column(JSONType, nullable=True)
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True  # Index for cleanup queries
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self):
        return f"<GamePlayback(id={self.id}, game_id={self.game_id}, turns={self.turn_count})>"


class PlayerStatsModel(Base):
    """
    Database model for player statistics.
    
    Aggregated player statistics for leaderboards and analytics.
    Retention: Permanent.
    """
    __tablename__ = "player_stats"
    
    # Primary key - links to users table for authenticated users
    # For AI players, uses their generated ID (e.g., "ai-player-123")
    player_id = Column(String(255), primary_key=True)
    
    # Display name (cached for leaderboard display)
    display_name = Column(String(255), nullable=False)
    
    # Overall stats
    games_played = Column(Integer, nullable=False, default=0)
    games_won = Column(Integer, nullable=False, default=0)
    
    # Tussle stats
    total_tussles = Column(Integer, nullable=False, default=0)
    tussles_won = Column(Integer, nullable=False, default=0)
    
    # Game duration stats (for calculating averages)
    total_turns = Column(Integer, nullable=False, default=0)
    total_game_duration_seconds = Column(Integer, nullable=False, default=0)
    
    # Card-specific stats (JSONB for flexibility)
    # Structure: {
    #   "Ka": {"games_played": 50, "games_won": 28, "tussles_initiated": 30, "tussles_won": 22},
    #   "Knight": {"games_played": 45, "games_won": 25, ...}
    # }
    card_stats = Column(JSONType, nullable=False, default={})
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # Indexes for leaderboards
    __table_args__ = (
        Index('idx_player_stats_games_won', 'games_won'),
        Index('idx_player_stats_games_played', 'games_played'),
    )
    
    def __repr__(self):
        return f"<PlayerStats(player_id={self.player_id}, wins={self.games_won}/{self.games_played})>"
    
    @property
    def win_rate(self) -> float:
        """Calculate win rate as percentage."""
        if self.games_played == 0:
            return 0.0
        return (self.games_won / self.games_played) * 100
    
    @property
    def avg_turns(self) -> float:
        """Calculate average turns per game."""
        if self.games_played == 0:
            return 0.0
        return self.total_turns / self.games_played
    
    @property
    def avg_game_duration_seconds(self) -> float:
        """Calculate average game duration in seconds."""
        if self.games_played == 0:
            return 0.0
        return self.total_game_duration_seconds / self.games_played


class SimulationRunModel(Base):
    """
    Database model for simulation runs.
    
    Stores configuration and progress for AI vs AI simulation batches.
    Retention: 7 days (cleaned up by scheduled task).
    """
    __tablename__ = "simulation_runs"
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Status tracking
    status = Column(
        String(50),
        nullable=False,
        default="pending",
        index=True
    )  # pending, running, completed, failed, cancelled
    
    # Configuration (JSON for flexibility)
    # Structure: {
    #   "deck_names": ["Aggro_Rush", "Control_Ka", ...],
    #   "player1_model": "gemini-2.0-flash",
    #   "player2_model": "gemini-2.5-flash",
    #   "iterations_per_matchup": 10,
    #   "max_turns": 20
    # }
    config = Column(JSONType, nullable=False)
    
    # Progress tracking
    total_games = Column(Integer, nullable=False)
    completed_games = Column(Integer, nullable=False, default=0)
    
    # Aggregated results (populated after completion)
    # Structure: {
    #   "matchup_stats": {"Deck1_vs_Deck2": {...}, ...},
    #   "overall_stats": {...}
    # }
    results = Column(JSONType, nullable=True)
    
    # Error tracking
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True  # Index for cleanup queries (7-day retention)
    )
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed', 'cancelled')",
            name="simulation_runs_status_check"
        ),
    )
    
    def __repr__(self):
        return f"<SimulationRun(id={self.id}, status={self.status}, progress={self.completed_games}/{self.total_games})>"


class SimulationGameModel(Base):
    """
    Database model for individual simulation game results.
    
    Stores per-game results including CC tracking for analysis.
    Retention: 7 days (cascades with parent simulation run).
    """
    __tablename__ = "simulation_games"
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign key to simulation run
    run_id = Column(
        Integer,
        ForeignKey("simulation_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Game metadata
    game_number = Column(Integer, nullable=False)  # 1-indexed within run
    deck1_name = Column(String(255), nullable=False, index=True)
    deck2_name = Column(String(255), nullable=False, index=True)
    player1_model = Column(String(100), nullable=False)
    player2_model = Column(String(100), nullable=False)
    
    # Outcome
    outcome = Column(
        String(50),
        nullable=False
    )  # player1_win, player2_win, draw
    winner_deck = Column(String(255), nullable=True)  # None for draw
    
    # Game metrics
    turn_count = Column(Integer, nullable=False)
    duration_ms = Column(Integer, nullable=False)
    
    # CC tracking per turn (JSON array)
    # Structure: [
    #   {"turn": 1, "player_id": "player1", "cc_start": 0, "cc_gained": 2, "cc_spent": 1, "cc_end": 1},
    #   {"turn": 1, "player_id": "player2", "cc_start": 0, "cc_gained": 2, "cc_spent": 0, "cc_end": 2},
    #   ...
    # ]
    cc_tracking = Column(JSONType, nullable=False)
    
    # Full action log for replay
    action_log = Column(JSONType, nullable=False)
    
    # Error tracking (if game failed)
    error_message = Column(Text, nullable=True)
    
    # Timestamp
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    
    __table_args__ = (
        CheckConstraint(
            "outcome IN ('player1_win', 'player2_win', 'draw')",
            name="simulation_games_outcome_check"
        ),
        Index('idx_simulation_games_matchup', 'deck1_name', 'deck2_name'),
    )
    
    def __repr__(self):
        return f"<SimulationGame(id={self.id}, run_id={self.run_id}, {self.deck1_name} vs {self.deck2_name})>"
