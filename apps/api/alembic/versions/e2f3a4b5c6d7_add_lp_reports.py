"""add_lp_reports

Revision ID: e2f3a4b5c6d7
Revises: c9d0e1f2a3b4
Create Date: 2026-02-28 00:01:00.000000

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "e2f3a4b5c6d7"
down_revision = "c9d0e1f2a3b4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lp_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("portfolio_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("report_period", sa.String(20), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("status", sa.String(20), server_default="draft", nullable=False),
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("gross_irr", sa.Float(), nullable=True),
        sa.Column("net_irr", sa.Float(), nullable=True),
        sa.Column("tvpi", sa.Float(), nullable=True),
        sa.Column("dpi", sa.Float(), nullable=True),
        sa.Column("rvpi", sa.Float(), nullable=True),
        sa.Column("moic", sa.Float(), nullable=True),
        sa.Column("total_committed", sa.Float(), nullable=True),
        sa.Column("total_invested", sa.Float(), nullable=True),
        sa.Column("total_returned", sa.Float(), nullable=True),
        sa.Column("total_nav", sa.Float(), nullable=True),
        sa.Column("narrative", postgresql.JSONB(), nullable=True),
        sa.Column("investments_data", postgresql.JSONB(), nullable=True),
        sa.Column("pdf_s3_key", sa.String(500), nullable=True),
        sa.Column("generated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_lp_reports_org_id", "lp_reports", ["org_id"])


def downgrade() -> None:
    op.drop_index("ix_lp_reports_org_id", table_name="lp_reports")
    op.drop_table("lp_reports")
