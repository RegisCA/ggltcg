"""
SQLAlchemy ORM models for database persistence.

Defines the database schema using SQLAlchemy declarative models.
"""

from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, DateTime, Text, CheckConstraint, Index
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import uuid

Base = declarative_base()


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
    
    # Full game state (JSONB)
    game_state = Column(JSONB, nullable=False)
    
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
    
    # Action details (JSONB for flexibility)
    action_data = Column(JSONB, nullable=False)
    
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
