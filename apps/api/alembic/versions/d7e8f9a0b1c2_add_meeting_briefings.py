"""add_meeting_briefings

Revision ID: d7e8f9a0b1c2
Revises: e2f3a4b5c6d7
Create Date: 2026-02-28 00:06:00.000000

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "d7e8f9a0b1c2"
down_revision = "e2f3a4b5c6d7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "meeting_briefings",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("meeting_type", sa.String(50), nullable=False),
        sa.Column("meeting_date", sa.Date(), nullable=True),
        sa.Column("previous_meeting_date", sa.Date(), nullable=True),
        sa.Column("briefing_content", postgresql.JSONB(), nullable=True),
        sa.Column("custom_overrides", postgresql.JSONB(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_meeting_briefings_org_id", "meeting_briefings", ["org_id"])
    op.create_index("ix_meeting_briefings_project_id", "meeting_briefings", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_meeting_briefings_project_id", table_name="meeting_briefings")
    op.drop_index("ix_meeting_briefings_org_id", table_name="meeting_briefings")
    op.drop_table("meeting_briefings")
