"""create_games_tables

Revision ID: 001
Revises: 
Create Date: 2025-11-21 16:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create games table
    op.create_table(
        'games',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('player1_id', sa.String(255), nullable=False),
        sa.Column('player1_name', sa.String(255), nullable=False),
        sa.Column('player2_id', sa.String(255), nullable=False),
        sa.Column('player2_name', sa.String(255), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('winner_id', sa.String(255), nullable=True),
        sa.Column('turn_number', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('active_player_id', sa.String(255), nullable=False),
        sa.Column('phase', sa.String(50), nullable=False, server_default='Start'),
        sa.Column('game_state', postgresql.JSONB(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("status IN ('active', 'completed', 'abandoned')", name='games_status_check')
    )
    
    # Create indexes
    op.create_index('idx_games_player1', 'games', ['player1_id'])
    op.create_index('idx_games_player2', 'games', ['player2_id'])
    op.create_index('idx_games_status', 'games', ['status'])
    op.create_index('idx_games_updated_at', 'games', ['updated_at'])
    op.create_index('idx_games_player_active', 'games', ['player1_id', 'player2_id', 'status'])
    op.create_index(
        'idx_games_active_player', 
        'games', 
        ['active_player_id'], 
        postgresql_where=sa.text("status = 'active'")
    )
    
    # Create trigger function for updating updated_at
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    # Create trigger
    op.execute("""
        CREATE TRIGGER update_games_updated_at
        BEFORE UPDATE ON games
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    """)
    
    # Create game_actions table (optional, for future use)
    op.create_table(
        'game_actions',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('game_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('turn_number', sa.Integer(), nullable=False),
        sa.Column('player_id', sa.String(255), nullable=False),
        sa.Column('action_type', sa.String(50), nullable=False),
        sa.Column('action_data', postgresql.JSONB(), nullable=False),
        sa.Column('result_description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for game_actions
    op.create_index('idx_game_actions_game_id', 'game_actions', ['game_id'])
    op.create_index('idx_game_actions_player', 'game_actions', ['player_id'])
    op.create_index('idx_game_actions_type', 'game_actions', ['action_type'])
    op.create_index('idx_game_actions_turn', 'game_actions', ['game_id', 'turn_number'])
    
    # Create game_stats table (optional, for future use)
    op.create_table(
        'game_stats',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('game_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('winner_id', sa.String(255), nullable=False),
        sa.Column('loser_id', sa.String(255), nullable=False),
        sa.Column('total_turns', sa.Integer(), nullable=False),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('winner_cards_played', sa.Integer(), nullable=True),
        sa.Column('winner_tussles_initiated', sa.Integer(), nullable=True),
        sa.Column('winner_direct_attacks', sa.Integer(), nullable=True),
        sa.Column('loser_cards_played', sa.Integer(), nullable=True),
        sa.Column('loser_tussles_initiated', sa.Integer(), nullable=True),
        sa.Column('loser_direct_attacks', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('game_id', name='game_stats_unique_game')
    )
    
    # Create indexes for game_stats
    op.create_index('idx_game_stats_winner', 'game_stats', ['winner_id'])
    op.create_index('idx_game_stats_loser', 'game_stats', ['loser_id'])
    op.create_index('idx_game_stats_created_at', 'game_stats', ['created_at'], postgresql_ops={'created_at': 'DESC'})


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('game_stats')
    op.drop_table('game_actions')
    
    # Drop trigger and function
    op.execute('DROP TRIGGER IF EXISTS update_games_updated_at ON games;')
    op.execute('DROP FUNCTION IF EXISTS update_updated_at_column();')
    
    # Drop games table
    op.drop_table('games')
