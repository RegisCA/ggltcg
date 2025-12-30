"""add v3 fields to ai_decision_logs

Revision ID: 011
Revises: 010
Create Date: 2025-12-30

Issue #260: Track v3 turn planning data in AI logs.
Adds fields to distinguish v2 vs v3, store turn plans, and track execution status.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '011'
down_revision: Union[str, None] = '010'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add v3 fields to ai_decision_logs table."""
    # ai_version: 2 or 3
    op.add_column(
        'ai_decision_logs',
        sa.Column('ai_version', sa.Integer(), nullable=True, server_default='2')
    )
    
    # turn_plan: Full TurnPlan JSON for v3 (stored on each action log entry)
    op.add_column(
        'ai_decision_logs',
        sa.Column(
            'turn_plan',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True
        )
    )
    
    # plan_execution_status: "complete" or "fallback"
    op.add_column(
        'ai_decision_logs',
        sa.Column('plan_execution_status', sa.String(20), nullable=True)
    )
    
    # fallback_reason: Why fallback occurred (if any)
    op.add_column(
        'ai_decision_logs',
        sa.Column('fallback_reason', sa.Text(), nullable=True)
    )
    
    # planned_action_index: Which action in the plan this log represents (0-based)
    op.add_column(
        'ai_decision_logs',
        sa.Column('planned_action_index', sa.Integer(), nullable=True)
    )


def downgrade() -> None:
    """Remove v3 fields from ai_decision_logs table."""
    op.drop_column('ai_decision_logs', 'planned_action_index')
    op.drop_column('ai_decision_logs', 'fallback_reason')
    op.drop_column('ai_decision_logs', 'plan_execution_status')
    op.drop_column('ai_decision_logs', 'turn_plan')
    op.drop_column('ai_decision_logs', 'ai_version')
