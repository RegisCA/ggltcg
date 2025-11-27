"""create users table

Revision ID: 003
Revises: 002
Create Date: 2025-11-27 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create users table for Google OAuth authentication."""
    op.create_table(
        'users',
        sa.Column('google_id', sa.String(length=255), nullable=False),
        sa.Column('first_name', sa.String(length=255), nullable=False),
        sa.Column('custom_display_name', sa.String(length=255), nullable=True),
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
        sa.PrimaryKeyConstraint('google_id', name=op.f('pk_users'))
    )
    
    # Create index on custom_display_name for efficient lookups
    op.create_index(
        op.f('idx_users_display_name'),
        'users',
        ['custom_display_name'],
        unique=False
    )


def downgrade() -> None:
    """Drop users table."""
    op.drop_index(op.f('idx_users_display_name'), table_name='users')
    op.drop_table('users')
