"""create stats and logging tables

Revision ID: 004
Revises: 003
Create Date: 2025-12-01 12:00:00.000000

This migration creates tables for:
- ai_decision_logs: Stores AI prompts/responses (6 hour retention)
- game_playback: Stores completed game summaries (24 hour retention)
- player_stats: Stores aggregate player statistics (permanent)

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create AI decision logs, game playback, and player stats tables."""
    
    # ========================================
    # AI Decision Logs (6 hour retention)
    # ========================================
    op.create_table(
        'ai_decision_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('game_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('turn_number', sa.Integer(), nullable=False),
        sa.Column('player_id', sa.String(length=255), nullable=True),
        sa.Column('model_name', sa.String(length=100), nullable=False),
        sa.Column('prompts_version', sa.String(length=20), nullable=False),
        sa.Column('prompt', sa.Text(), nullable=False),
        sa.Column('response', sa.Text(), nullable=False),
        sa.Column('action_number', sa.Integer(), nullable=True),
        sa.Column('reasoning', sa.Text(), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_ai_decision_logs'))
    )
    
    # Indexes for ai_decision_logs
    op.create_index(
        op.f('idx_ai_decision_logs_game_id'),
        'ai_decision_logs',
        ['game_id'],
        unique=False
    )
    op.create_index(
        op.f('idx_ai_decision_logs_created_at'),
        'ai_decision_logs',
        ['created_at'],
        unique=False
    )
    
    # ========================================
    # Game Playback (24 hour retention)
    # ========================================
    op.create_table(
        'game_playback',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('game_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('player1_id', sa.String(length=255), nullable=False),
        sa.Column('player1_name', sa.String(length=255), nullable=False),
        sa.Column('player2_id', sa.String(length=255), nullable=False),
        sa.Column('player2_name', sa.String(length=255), nullable=False),
        sa.Column('winner_id', sa.String(length=255), nullable=True),
        sa.Column('starting_deck_p1', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('starting_deck_p2', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('first_player_id', sa.String(length=255), nullable=False),
        sa.Column('play_by_play', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('turn_count', sa.Integer(), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False
        ),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_game_playback'))
    )
    
    # Indexes for game_playback
    op.create_index(
        op.f('idx_game_playback_game_id'),
        'game_playback',
        ['game_id'],
        unique=True
    )
    op.create_index(
        op.f('idx_game_playback_created_at'),
        'game_playback',
        ['created_at'],
        unique=False
    )
    op.create_index(
        op.f('idx_game_playback_winner_id'),
        'game_playback',
        ['winner_id'],
        unique=False
    )
    
    # ========================================
    # Player Stats (permanent)
    # ========================================
    op.create_table(
        'player_stats',
        sa.Column('player_id', sa.String(length=255), nullable=False),
        sa.Column('display_name', sa.String(length=255), nullable=False),
        sa.Column('games_played', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('games_won', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_tussles', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('tussles_won', sa.Integer(), nullable=False, server_default='0'),
        sa.Column(
            'card_stats',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default='{}'
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False
        ),
        sa.PrimaryKeyConstraint('player_id', name=op.f('pk_player_stats'))
    )
    
    # Indexes for player_stats (leaderboards)
    op.create_index(
        op.f('idx_player_stats_games_won'),
        'player_stats',
        ['games_won'],
        unique=False
    )
    op.create_index(
        op.f('idx_player_stats_games_played'),
        'player_stats',
        ['games_played'],
        unique=False
    )


def downgrade() -> None:
    """Drop stats and logging tables."""
    # Drop player_stats
    op.drop_index(op.f('idx_player_stats_games_played'), table_name='player_stats')
    op.drop_index(op.f('idx_player_stats_games_won'), table_name='player_stats')
    op.drop_table('player_stats')
    
    # Drop game_playback
    op.drop_index(op.f('idx_game_playback_winner_id'), table_name='game_playback')
    op.drop_index(op.f('idx_game_playback_created_at'), table_name='game_playback')
    op.drop_index(op.f('idx_game_playback_game_id'), table_name='game_playback')
    op.drop_table('game_playback')
    
    # Drop ai_decision_logs
    op.drop_index(op.f('idx_ai_decision_logs_created_at'), table_name='ai_decision_logs')
    op.drop_index(op.f('idx_ai_decision_logs_game_id'), table_name='ai_decision_logs')
    op.drop_table('ai_decision_logs')
