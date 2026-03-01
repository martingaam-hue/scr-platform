"""add covenant kpi monitoring

Revision ID: c3a2b3c4d5e6
Revises: ("aa1122334455", "f1a2b3c4d5e6")
Create Date: 2026-03-01 14:00:00.000000

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "c3a2b3c4d5e6"
down_revision = ("aa1122334455", "f1a2b3c4d5e6")
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "covenants",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("portfolio_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("covenant_type", sa.String(50), nullable=False),
        sa.Column("metric_name", sa.String(100), nullable=False),
        sa.Column("threshold_value", sa.Float, nullable=True),
        sa.Column("comparison", sa.String(10), nullable=False),
        sa.Column("threshold_upper", sa.Float, nullable=True),
        sa.Column("current_value", sa.Float, nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            sa.String(20),
            server_default="compliant",
            nullable=False,
        ),
        sa.Column(
            "warning_threshold_pct",
            sa.Float,
            server_default="0.1",
            nullable=False,
        ),
        sa.Column("breach_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("waived_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("waived_reason", sa.Text, nullable=True),
        sa.Column("source_document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "check_frequency",
            sa.String(20),
            server_default="monthly",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("is_deleted", sa.Boolean, server_default="false", nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["portfolio_id"], ["portfolios.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["waived_by"], ["users.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["source_document_id"], ["documents.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_covenants_org_id", "covenants", ["org_id"])
    op.create_index("ix_covenants_project_id", "covenants", ["project_id"])
    op.create_index(
        "ix_covenants_org_project", "covenants", ["org_id", "project_id"]
    )
    op.create_index("ix_covenants_status", "covenants", ["status"])

    op.create_table(
        "kpi_actuals",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kpi_name", sa.String(100), nullable=False),
        sa.Column("value", sa.Float, nullable=False),
        sa.Column("unit", sa.String(50), nullable=True),
        sa.Column("period", sa.String(20), nullable=False),
        sa.Column(
            "period_type",
            sa.String(20),
            server_default="quarterly",
            nullable=False,
        ),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("source_document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("entered_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("is_deleted", sa.Boolean, server_default="false", nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["source_document_id"], ["documents.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["entered_by"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_kpi_actuals_org_id", "kpi_actuals", ["org_id"])
    op.create_index("ix_kpi_actuals_project_id", "kpi_actuals", ["project_id"])
    op.create_index(
        "ix_kpi_actuals_project_kpi", "kpi_actuals", ["project_id", "kpi_name"]
    )
    op.create_index(
        "ix_kpi_actuals_project_period", "kpi_actuals", ["project_id", "period"]
    )

    op.create_table(
        "kpi_targets",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kpi_name", sa.String(100), nullable=False),
        sa.Column("target_value", sa.Float, nullable=False),
        sa.Column("period", sa.String(20), nullable=False),
        sa.Column(
            "tolerance_pct",
            sa.Float,
            server_default="0.1",
            nullable=False,
        ),
        sa.Column(
            "source",
            sa.String(50),
            server_default="business_plan",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("is_deleted", sa.Boolean, server_default="false", nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_kpi_targets_org_id", "kpi_targets", ["org_id"])
    op.create_index("ix_kpi_targets_project_id", "kpi_targets", ["project_id"])
    op.create_index(
        "ix_kpi_targets_project_kpi", "kpi_targets", ["project_id", "kpi_name"]
    )
    op.create_index(
        "ix_kpi_targets_project_period", "kpi_targets", ["project_id", "period"]
    )


def downgrade() -> None:
    op.drop_index("ix_kpi_targets_project_period", table_name="kpi_targets")
    op.drop_index("ix_kpi_targets_project_kpi", table_name="kpi_targets")
    op.drop_index("ix_kpi_targets_project_id", table_name="kpi_targets")
    op.drop_index("ix_kpi_targets_org_id", table_name="kpi_targets")
    op.drop_table("kpi_targets")

    op.drop_index("ix_kpi_actuals_project_period", table_name="kpi_actuals")
    op.drop_index("ix_kpi_actuals_project_kpi", table_name="kpi_actuals")
    op.drop_index("ix_kpi_actuals_project_id", table_name="kpi_actuals")
    op.drop_index("ix_kpi_actuals_org_id", table_name="kpi_actuals")
    op.drop_table("kpi_actuals")

    op.drop_index("ix_covenants_status", table_name="covenants")
    op.drop_index("ix_covenants_org_project", table_name="covenants")
    op.drop_index("ix_covenants_project_id", table_name="covenants")
    op.drop_index("ix_covenants_org_id", table_name="covenants")
    op.drop_table("covenants")
