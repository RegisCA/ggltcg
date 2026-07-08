"""allow paused/budget_exhausted simulation_runs.status

Revision ID: 014
Revises: 013
Create Date: 2026-07-08

Widens the simulation_runs_status_check CheckConstraint to allow the two
new statuses used by resumable simulation runs (PR B3):
- "paused": a run was explicitly paused via pause_simulation()
- "budget_exhausted": a run stopped itself after the AI rate limiter's
  daily request budget ran out (see game_engine.ai.rate_limiter)

The status column itself is already String(50) and needs no schema change;
only the CHECK constraint's allowed value list changes.
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '014'
down_revision: Union[str, None] = '013'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

OLD_CONSTRAINT = "status IN ('pending', 'running', 'completed', 'failed', 'cancelled')"
NEW_CONSTRAINT = (
    "status IN ('pending', 'running', 'completed', 'failed', 'cancelled', "
    "'paused', 'budget_exhausted')"
)


def upgrade() -> None:
    """Widen the status CHECK constraint to allow paused/budget_exhausted."""
    op.drop_constraint('simulation_runs_status_check', 'simulation_runs', type_='check')
    op.create_check_constraint(
        'simulation_runs_status_check',
        'simulation_runs',
        NEW_CONSTRAINT,
    )


def downgrade() -> None:
    """Restore the original status CHECK constraint."""
    op.drop_constraint('simulation_runs_status_check', 'simulation_runs', type_='check')
    op.create_check_constraint(
        'simulation_runs_status_check',
        'simulation_runs',
        OLD_CONSTRAINT,
    )
