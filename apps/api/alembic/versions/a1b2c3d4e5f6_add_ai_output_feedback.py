"""Add ai_output_feedback table.

Revision ID: a1b2c3d4e5f6
Revises: f1a2b3c4d5e6
Create Date: 2026-02-28 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "f1a2b3c4d5e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_output_feedback",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("task_log_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("task_type", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=True),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("rating", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("was_edited", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("original_content", sa.Text(), nullable=True),
        sa.Column("edited_content", sa.Text(), nullable=True),
        sa.Column("edit_distance_pct", sa.Float(), nullable=True),
        sa.Column("was_accepted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["task_log_id"], ["ai_task_logs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_output_feedback_task_log_id", "ai_output_feedback", ["task_log_id"])
    op.create_index("ix_ai_output_feedback_org_id", "ai_output_feedback", ["org_id"])
    op.create_index("ix_ai_output_feedback_user_id", "ai_output_feedback", ["user_id"])
    op.create_index("ix_ai_output_feedback_task_type", "ai_output_feedback", ["task_type"])
    op.create_index("ix_ai_output_feedback_rating", "ai_output_feedback", ["rating"])


def downgrade() -> None:
    op.drop_index("ix_ai_output_feedback_rating", table_name="ai_output_feedback")
    op.drop_index("ix_ai_output_feedback_task_type", table_name="ai_output_feedback")
    op.drop_index("ix_ai_output_feedback_user_id", table_name="ai_output_feedback")
    op.drop_index("ix_ai_output_feedback_org_id", table_name="ai_output_feedback")
    op.drop_index("ix_ai_output_feedback_task_log_id", table_name="ai_output_feedback")
    op.drop_table("ai_output_feedback")
