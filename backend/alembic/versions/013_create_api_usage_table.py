"""create api_usage_daily table

Revision ID: 013
Revises: 012
Create Date: 2026-07-08

Creates api_usage_daily, which tracks per-provider, per-day request counts
so the rate limiter's daily budget survives process restarts. Composite
primary key (provider, day) since we only ever need one row per provider
per calendar day.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '013'
down_revision: Union[str, None] = '012'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create api_usage_daily table."""
    op.create_table(
        'api_usage_daily',
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('day', sa.Date(), nullable=False),
        sa.Column('request_count', sa.Integer(), nullable=False, server_default='0'),
        sa.PrimaryKeyConstraint('provider', 'day', name=op.f('pk_api_usage_daily')),
    )


def downgrade() -> None:
    """Drop api_usage_daily table."""
    op.drop_table('api_usage_daily')
