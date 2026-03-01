"""add_redaction_jobs

Revision ID: e3a2b3c4d5e6
Revises: e6a2b3c4d5e6
Create Date: 2026-03-01 17:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "e3a2b3c4d5e6"
down_revision = "e6a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── redaction_jobs ────────────────────────────────────────────────────────
    op.create_table(
        "redaction_jobs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("detected_entities", postgresql.JSONB(), nullable=True),
        sa.Column("approved_redactions", postgresql.JSONB(), nullable=True),
        sa.Column("redacted_document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("redacted_s3_key", sa.String(1024), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "entity_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "approved_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["org_id"], ["organizations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], ondelete="SET NULL"
        ),
    )
    op.create_index(
        "ix_redaction_jobs_org_id", "redaction_jobs", ["org_id"]
    )
    op.create_index(
        "ix_redaction_jobs_document_id", "redaction_jobs", ["document_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_redaction_jobs_document_id", table_name="redaction_jobs")
    op.drop_index("ix_redaction_jobs_org_id", table_name="redaction_jobs")
    op.drop_table("redaction_jobs")
