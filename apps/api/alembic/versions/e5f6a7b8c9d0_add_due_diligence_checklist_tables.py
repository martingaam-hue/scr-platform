"""add_due_diligence_checklist_tables

Revision ID: e5f6a7b8c9d0
Revises: f3a9d1e72b08
Create Date: 2026-02-28 00:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "e5f6a7b8c9d0"
down_revision = "f3a9d1e72b08"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── dd_checklist_templates ───────────────────────────────────────────────
    op.create_table(
        "dd_checklist_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("asset_type", sa.String(50), nullable=False),
        sa.Column("deal_stage", sa.String(50), nullable=False),
        sa.Column("jurisdiction_group", sa.String(20), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default="false"),
    )
    op.create_index("ix_dd_checklist_templates_asset_type", "dd_checklist_templates", ["asset_type"])
    op.create_index("ix_dd_checklist_templates_deal_stage", "dd_checklist_templates", ["deal_stage"])
    op.create_index("ix_dd_template_type_stage", "dd_checklist_templates", ["asset_type", "deal_stage"])

    # ── dd_checklist_items ───────────────────────────────────────────────────
    op.create_table(
        "dd_checklist_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("dd_checklist_templates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("requirement_type", sa.String(30), nullable=False),
        sa.Column("required_document_types", postgresql.JSONB, nullable=True),
        sa.Column("verification_criteria", sa.Text, nullable=True),
        sa.Column("priority", sa.String(20), nullable=False, server_default="required"),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("estimated_time_hours", sa.Float, nullable=True),
        sa.Column("regulatory_reference", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default="false"),
    )
    op.create_index("ix_dd_checklist_items_template_id", "dd_checklist_items", ["template_id"])

    # ── dd_project_checklists ────────────────────────────────────────────────
    op.create_table(
        "dd_project_checklists",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("dd_checklist_templates.id"), nullable=False),
        sa.Column("investor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="in_progress"),
        sa.Column("completion_percentage", sa.Float, nullable=False, server_default="0"),
        sa.Column("total_items", sa.Integer, nullable=False, server_default="0"),
        sa.Column("completed_items", sa.Integer, nullable=False, server_default="0"),
        sa.Column("custom_items", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default="false"),
    )
    op.create_index("ix_dd_project_checklists_project_id", "dd_project_checklists", ["project_id"])

    # ── dd_item_statuses ─────────────────────────────────────────────────────
    op.create_table(
        "dd_item_statuses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("checklist_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("dd_project_checklists.id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("dd_checklist_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("satisfied_by_document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("ai_review_result", postgresql.JSONB, nullable=True),
        sa.Column("reviewer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewer_notes", sa.Text, nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default="false"),
        sa.UniqueConstraint("checklist_id", "item_id", name="uq_dd_item_status"),
    )
    op.create_index("ix_dd_item_status_checklist", "dd_item_statuses", ["checklist_id"])


def downgrade() -> None:
    op.drop_table("dd_item_statuses")
    op.drop_table("dd_project_checklists")
    op.drop_table("dd_checklist_items")
    op.drop_table("dd_checklist_templates")
