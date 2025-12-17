"""create simulation tables

Revision ID: 009
Revises: 008
Create Date: 2025-12-16 12:00:00.000000

This migration creates tables for:
- simulation_runs: Stores simulation run configurations and progress (7 day retention)
- simulation_games: Stores individual simulation game results (cascades with parent)

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '009'
down_revision: Union[str, None] = '008'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create simulation_runs and simulation_games tables."""
    
    # ========================================
    # Simulation Runs (7 day retention)
    # ========================================
    op.create_table(
        'simulation_runs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('total_games', sa.Integer(), nullable=False),
        sa.Column('completed_games', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('results', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False
        ),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_simulation_runs')),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed', 'cancelled')",
            name='simulation_runs_status_check'
        )
    )
    
    # Indexes for simulation_runs
    op.create_index(
        op.f('idx_simulation_runs_status'),
        'simulation_runs',
        ['status'],
        unique=False
    )
    op.create_index(
        op.f('idx_simulation_runs_created_at'),
        'simulation_runs',
        ['created_at'],
        unique=False
    )
    
    # ========================================
    # Simulation Games (cascades with parent run)
    # ========================================
    op.create_table(
        'simulation_games',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            'run_id',
            sa.Integer(),
            sa.ForeignKey('simulation_runs.id', ondelete='CASCADE'),
            nullable=False
        ),
        sa.Column('game_number', sa.Integer(), nullable=False),
        sa.Column('deck1_name', sa.String(length=255), nullable=False),
        sa.Column('deck2_name', sa.String(length=255), nullable=False),
        sa.Column('player1_model', sa.String(length=100), nullable=False),
        sa.Column('player2_model', sa.String(length=100), nullable=False),
        sa.Column('outcome', sa.String(length=50), nullable=False),
        sa.Column('winner_deck', sa.String(length=255), nullable=True),
        sa.Column('turn_count', sa.Integer(), nullable=False),
        sa.Column('duration_ms', sa.Integer(), nullable=False),
        sa.Column('cc_tracking', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('action_log', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_simulation_games')),
        sa.CheckConstraint(
            "outcome IN ('player1_win', 'player2_win', 'draw')",
            name='simulation_games_outcome_check'
        )
    )
    
    # Indexes for simulation_games
    op.create_index(
        op.f('idx_simulation_games_run_id'),
        'simulation_games',
        ['run_id'],
        unique=False
    )
    op.create_index(
        op.f('idx_simulation_games_deck1_name'),
        'simulation_games',
        ['deck1_name'],
        unique=False
    )
    op.create_index(
        op.f('idx_simulation_games_deck2_name'),
        'simulation_games',
        ['deck2_name'],
        unique=False
    )
    op.create_index(
        'idx_simulation_games_matchup',
        'simulation_games',
        ['deck1_name', 'deck2_name'],
        unique=False
    )


def downgrade() -> None:
    """Drop simulation tables."""
    op.drop_table('simulation_games')
    op.drop_table('simulation_runs')
