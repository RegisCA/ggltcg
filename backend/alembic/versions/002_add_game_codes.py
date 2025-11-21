"""add game codes for multiplayer lobby

Revision ID: 002
Revises: 001
Create Date: 2025-11-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add game_code column for lobby system and make player2 fields nullable."""
    
    # Make player2 fields nullable to support waiting_for_player state
    op.alter_column('games', 'player2_id', nullable=True)
    op.alter_column('games', 'player2_name', nullable=True)
    
    # Add game_code column (nullable initially for existing games)
    op.add_column('games', sa.Column('game_code', sa.String(6), nullable=True))
    
    # Create unique index on game_code (where not null)
    op.create_index(
        'idx_games_game_code',
        'games',
        ['game_code'],
        unique=True,
        postgresql_where=sa.text('game_code IS NOT NULL')
    )
    
    # Update status constraint to include new states
    op.drop_constraint('games_status_check', 'games', type_='check')
    op.create_check_constraint(
        'games_status_check',
        'games',
        "status IN ('waiting_for_player', 'deck_selection', 'active', 'completed', 'abandoned')"
    )


def downgrade() -> None:
    """Remove game_code column and restore player2 constraints."""
    
    # Restore original status constraint
    op.drop_constraint('games_status_check', 'games', type_='check')
    op.create_check_constraint(
        'games_status_check',
        'games',
        "status IN ('active', 'completed', 'abandoned')"
    )
    
    # Drop index
    op.drop_index('idx_games_game_code', table_name='games')
    
    # Drop column
    op.drop_column('games', 'game_code')
    
    # Restore player2 fields to non-nullable (if needed)
    op.alter_column('games', 'player2_id', nullable=False)
    op.alter_column('games', 'player2_name', nullable=False)
