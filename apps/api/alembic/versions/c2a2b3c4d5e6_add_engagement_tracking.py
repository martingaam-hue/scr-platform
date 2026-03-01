"""add_engagement_tracking

Revision ID: c2a2b3c4d5e6
Revises: aa1122334455, f1a2b3c4d5e6
Create Date: 2026-03-01 10:00:00.000000

Creates document_engagements and deal_engagement_summaries tables
for the C02 Document Engagement Tracking feature.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c2a2b3c4d5e6"
down_revision: Union[str, tuple[str, ...]] = ("aa1122334455", "f1a2b3c4d5e6")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── document_engagements ──────────────────────────────────────────────────
    op.create_table(
        "document_engagements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_id", sa.String(100), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_time_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pages_viewed", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("total_pages", sa.Integer(), nullable=True),
        sa.Column("pages_viewed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_pct", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("downloaded", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("printed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("referrer_page", sa.String(200), nullable=True),
        sa.Column("device_type", sa.String(20), nullable=True),
    )

    op.create_index("ix_document_engagements_org_id", "document_engagements", ["org_id"])
    op.create_index("ix_document_engagements_document_id", "document_engagements", ["document_id"])
    op.create_index("ix_document_engagements_user_id", "document_engagements", ["user_id"])
    op.create_index("ix_document_engagements_doc_opened", "document_engagements", ["document_id", "opened_at"])
    op.create_index("ix_document_engagements_user_org", "document_engagements", ["user_id", "org_id"])

    # ── deal_engagement_summaries ─────────────────────────────────────────────
    op.create_table(
        "deal_engagement_summaries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("deal_room_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("deal_rooms.id", ondelete="SET NULL"), nullable=True),
        sa.Column("investor_org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("total_sessions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_time_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unique_documents_viewed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_documents_available", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("documents_downloaded", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("engagement_score", sa.Float(), nullable=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_index("ix_deal_engagement_summaries_org_id", "deal_engagement_summaries", ["org_id"])
    op.create_index("ix_deal_engagement_summaries_project_id", "deal_engagement_summaries", ["project_id"])
    op.create_index("ix_deal_engagement_summaries_project_investor", "deal_engagement_summaries", ["project_id", "investor_org_id"])


def downgrade() -> None:
    op.drop_index("ix_deal_engagement_summaries_project_investor", table_name="deal_engagement_summaries")
    op.drop_index("ix_deal_engagement_summaries_project_id", table_name="deal_engagement_summaries")
    op.drop_index("ix_deal_engagement_summaries_org_id", table_name="deal_engagement_summaries")
    op.drop_table("deal_engagement_summaries")

    op.drop_index("ix_document_engagements_user_org", table_name="document_engagements")
    op.drop_index("ix_document_engagements_doc_opened", table_name="document_engagements")
    op.drop_index("ix_document_engagements_user_id", table_name="document_engagements")
    op.drop_index("ix_document_engagements_document_id", table_name="document_engagements")
    op.drop_index("ix_document_engagements_org_id", table_name="document_engagements")
    op.drop_table("document_engagements")
