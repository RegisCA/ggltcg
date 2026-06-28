"""rename cc_tracking to charge_tracking

Revision ID: 012
Revises: 011
Create Date: 2026-06-28

Terminology refactor: CC ("Command Counters") is renamed to Charge throughout
the game. Renames the cc_tracking column to charge_tracking on both
game_playback and simulation_games. This is a clean break - existing rows
keep their data (the column is renamed in place, not dropped/recreated), but
the JSON payload's internal keys (cc_start/cc_gained/cc_spent/cc_end) are NOT
migrated to charge_start/charge_gained/charge_spent/charge_end since the
application no longer reads the old key names. Existing playback/simulation
rows should be treated as stale and are safe to discard.
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '012'
down_revision: Union[str, None] = '011'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rename cc_tracking column to charge_tracking on game_playback and simulation_games."""
    op.alter_column('game_playback', 'cc_tracking', new_column_name='charge_tracking')
    op.alter_column('simulation_games', 'cc_tracking', new_column_name='charge_tracking')


def downgrade() -> None:
    """Revert charge_tracking column back to cc_tracking."""
    op.alter_column('game_playback', 'charge_tracking', new_column_name='cc_tracking')
    op.alter_column('simulation_games', 'charge_tracking', new_column_name='cc_tracking')
