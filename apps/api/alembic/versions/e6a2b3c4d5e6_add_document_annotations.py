"""add_document_annotations

Revision ID: e6a2b3c4d5e6
Revises: e4a2b3c4d5e6
Create Date: 2026-03-01 16:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "e6a2b3c4d5e6"
down_revision = "e4a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── document_annotations ──────────────────────────────────────────────────
    op.create_table(
        "document_annotations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("annotation_type", sa.String(50), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column(
            "position",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column(
            "color",
            sa.String(20),
            nullable=False,
            server_default="#FFFF00",
        ),
        sa.Column("linked_qa_question_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("linked_citation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "is_private",
            sa.Boolean(),
            nullable=False,
            server_default="false",
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
        "ix_document_annotations_org_id", "document_annotations", ["org_id"]
    )
    op.create_index(
        "ix_document_annotations_document_id",
        "document_annotations",
        ["document_id"],
    )
    op.create_index(
        "ix_document_annotations_created_by",
        "document_annotations",
        ["created_by"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_document_annotations_created_by", table_name="document_annotations"
    )
    op.drop_index(
        "ix_document_annotations_document_id", table_name="document_annotations"
    )
    op.drop_index(
        "ix_document_annotations_org_id", table_name="document_annotations"
    )
    op.drop_table("document_annotations")
