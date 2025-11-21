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
    """Add game_code column for lobby system."""
    
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
    """Remove game_code column."""
    
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
