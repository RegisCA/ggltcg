"""add favorite decks to users

Revision ID: 008
Revises: 007
Create Date: 2025-12-15 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '008'
down_revision: Union[str, None] = '007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Default starter decks
DEFAULT_DECKS = [
    ["Dream", "Knight", "Raggy", "Umbruh", "Rush", "Twist"],
    ["Ballaber", "Demideca", "Ka", "Wizard", "Copy", "Wake"],
    ["Belchaletta", "Drum", "Hind Leg Kicker", "Violin", "Jumpscare", "Surge"]
]


def upgrade() -> None:
    """Add favorite_decks JSON column to users table with default starter decks."""
    import json
    
    # Add favorite_decks column (JSON for cross-database compatibility)
    op.add_column(
        'users',
        sa.Column('favorite_decks', sa.JSON, nullable=True)
    )
    
    # Update existing users to have default decks
    # Direct SQL execution with literal JSON string
    default_decks_json = json.dumps(DEFAULT_DECKS)
    
    op.execute(
        f"""
        UPDATE users 
        SET favorite_decks = '{default_decks_json}'::json 
        WHERE favorite_decks IS NULL
        """
    )


def downgrade() -> None:
    """Remove favorite_decks column from users table."""
    op.drop_column('users', 'favorite_decks')
