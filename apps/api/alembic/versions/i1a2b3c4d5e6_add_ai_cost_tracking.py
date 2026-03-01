"""add AI cost tracking columns.

Revision ID: i1a2b3c4d5e6
Revises: h2a2b3c4d5e6
Create Date: 2026-03-01 00:00:00

Adds:
  - ai_task_logs.cost_usd         NUMERIC(12,6) — computed cost of LLM call
  - ai_task_logs.tokens_input     INTEGER       — input tokens (separate from legacy tokens_used)
  - ai_task_logs.tokens_output    INTEGER       — output tokens
  - organizations.ai_monthly_budget DOUBLE PRECISION — per-org USD cap (NULL = tier default)
"""
from alembic import op
import sqlalchemy as sa

revision = "i1a2b3c4d5e6"
down_revision = "h2a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Use raw SQL with IF NOT EXISTS — columns may have been added manually
    op.execute("ALTER TABLE ai_task_logs ADD COLUMN IF NOT EXISTS cost_usd NUMERIC(12, 6)")
    op.execute("ALTER TABLE ai_task_logs ADD COLUMN IF NOT EXISTS tokens_input INTEGER")
    op.execute("ALTER TABLE ai_task_logs ADD COLUMN IF NOT EXISTS tokens_output INTEGER")
    op.execute("ALTER TABLE organizations ADD COLUMN IF NOT EXISTS ai_monthly_budget DOUBLE PRECISION")


def downgrade() -> None:
    op.drop_column("organizations", "ai_monthly_budget")
    op.drop_column("ai_task_logs", "tokens_output")
    op.drop_column("ai_task_logs", "tokens_input")
    op.drop_column("ai_task_logs", "cost_usd")
