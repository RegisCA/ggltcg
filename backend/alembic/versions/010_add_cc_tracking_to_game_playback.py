"""add cc_tracking to game_playback

Revision ID: 010
Revises: 009
Create Date: 2025-12-30

Issue #252: Track CC efficiency metrics per turn.
Adds cc_tracking column to store per-turn CC data for AI performance analysis.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '010'
down_revision: Union[str, None] = '009'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add cc_tracking column to game_playback table."""
    op.add_column(
        'game_playback',
        sa.Column(
            'cc_tracking',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True
        )
    )


def downgrade() -> None:
    """Remove cc_tracking column from game_playback table."""
    op.drop_column('game_playback', 'cc_tracking')
