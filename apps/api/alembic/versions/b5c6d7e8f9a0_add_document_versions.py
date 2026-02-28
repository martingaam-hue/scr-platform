"""add_document_versions

Revision ID: b5c6d7e8f9a0
Revises: b2c3d4e5f6a7
Create Date: 2026-02-28 00:04:00.000000

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "b5c6d7e8f9a0"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "document_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("s3_key", sa.String(500), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("checksum_sha256", sa.String(64), nullable=True),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("diff_stats", postgresql.JSONB(), nullable=True),
        sa.Column("diff_lines", postgresql.JSONB(), nullable=True),
        sa.Column("change_summary", sa.Text(), nullable=True),
        sa.Column("change_significance", sa.String(20), nullable=True),
        sa.Column("key_changes", postgresql.JSONB(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_document_versions_document_id", "document_versions", ["document_id"])
    op.create_index("ix_document_versions_org_id", "document_versions", ["org_id"])
    op.create_index("ix_doc_version_doc_num", "document_versions", ["document_id", "version_number"])


def downgrade() -> None:
    op.drop_index("ix_doc_version_doc_num", table_name="document_versions")
    op.drop_index("ix_document_versions_org_id", table_name="document_versions")
    op.drop_index("ix_document_versions_document_id", table_name="document_versions")
    op.drop_table("document_versions")
