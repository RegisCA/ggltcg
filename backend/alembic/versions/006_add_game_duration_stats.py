"""Add game duration and turn count stats to player_stats

Revision ID: 006
Revises: 005
Create Date: 2025-12-06

Adds total_turns and total_game_duration_seconds columns to player_stats
for calculating average game length statistics.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add total_turns column (sum of all turns across games)
    op.add_column(
        'player_stats',
        sa.Column('total_turns', sa.Integer(), nullable=False, server_default='0')
    )
    
    # Add total_game_duration_seconds column (sum of all game durations)
    op.add_column(
        'player_stats',
        sa.Column('total_game_duration_seconds', sa.Integer(), nullable=False, server_default='0')
    )


def downgrade() -> None:
    op.drop_column('player_stats', 'total_game_duration_seconds')
    op.drop_column('player_stats', 'total_turns')
