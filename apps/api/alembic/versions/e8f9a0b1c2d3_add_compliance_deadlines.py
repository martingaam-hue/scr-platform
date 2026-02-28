"""add_compliance_deadlines

Revision ID: e8f9a0b1c2d3
Revises: d7e8f9a0b1c2
Create Date: 2026-02-28 01:00:00.000000

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "e8f9a0b1c2d3"
down_revision = "d7e8f9a0b1c2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "compliance_deadlines",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("portfolio_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("jurisdiction", sa.String(100), nullable=True),
        sa.Column("regulatory_body", sa.String(255), nullable=True),
        sa.Column("due_date", sa.Date, nullable=False),
        sa.Column("recurrence", sa.String(20), nullable=True),
        sa.Column("status", sa.String(20), server_default="upcoming", nullable=False),
        sa.Column("priority", sa.String(10), server_default="high", nullable=False),
        sa.Column("assigned_to", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reminder_30d_sent", sa.Boolean, server_default="false", nullable=False),
        sa.Column("reminder_14d_sent", sa.Boolean, server_default="false", nullable=False),
        sa.Column("reminder_7d_sent", sa.Boolean, server_default="false", nullable=False),
        sa.Column("reminder_1d_sent", sa.Boolean, server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean, server_default="false", nullable=False),
        sa.ForeignKeyConstraint(["assigned_to"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_compliance_org_due", "compliance_deadlines", ["org_id", "due_date"])
    op.create_index("ix_compliance_org_status", "compliance_deadlines", ["org_id", "status"])
    op.create_index("ix_compliance_deadlines_org_id", "compliance_deadlines", ["org_id"])
    op.create_index("ix_compliance_deadlines_due_date", "compliance_deadlines", ["due_date"])


def downgrade() -> None:
    op.drop_table("compliance_deadlines")
