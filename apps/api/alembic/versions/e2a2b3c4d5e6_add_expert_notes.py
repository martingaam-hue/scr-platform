"""add_expert_notes

Revision ID: e2a2b3c4d5e6
Revises: e1a2b3c4d5e6
Create Date: 2026-03-01 14:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "e2a2b3c4d5e6"
down_revision = "e1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "expert_notes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("note_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("ai_summary", sa.Text(), nullable=True),
        sa.Column("key_takeaways", postgresql.JSONB(), nullable=True),
        sa.Column("risk_factors_identified", postgresql.JSONB(), nullable=True),
        sa.Column("linked_signal_dimensions", postgresql.JSONB(), nullable=True),
        sa.Column("participants", postgresql.JSONB(), nullable=True),
        sa.Column("meeting_date", sa.Date(), nullable=True),
        sa.Column("enrichment_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("is_private", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_expert_notes_org_id", "expert_notes", ["org_id"])
    op.create_index("ix_expert_notes_project_id", "expert_notes", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_expert_notes_project_id", table_name="expert_notes")
    op.drop_index("ix_expert_notes_org_id", table_name="expert_notes")
    op.drop_table("expert_notes")
