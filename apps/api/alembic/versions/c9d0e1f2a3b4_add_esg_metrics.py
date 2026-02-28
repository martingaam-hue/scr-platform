"""add_esg_metrics

Revision ID: c9d0e1f2a3b4
Revises: e5f6a7b8c9d0
Create Date: 2026-02-28 00:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "c9d0e1f2a3b4"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "esg_metrics",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "is_deleted",
            sa.Boolean,
            nullable=False,
            server_default="false",
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("period", sa.String(20), nullable=False),
        # Environmental
        sa.Column("carbon_footprint_tco2e", sa.Float, nullable=True),
        sa.Column("carbon_avoided_tco2e", sa.Float, nullable=True),
        sa.Column("renewable_energy_mwh", sa.Float, nullable=True),
        sa.Column("water_usage_cubic_m", sa.Float, nullable=True),
        sa.Column("waste_diverted_tonnes", sa.Float, nullable=True),
        sa.Column("biodiversity_score", sa.Float, nullable=True),
        # Social
        sa.Column("jobs_created", sa.Integer, nullable=True),
        sa.Column("jobs_supported", sa.Integer, nullable=True),
        sa.Column("local_procurement_pct", sa.Float, nullable=True),
        sa.Column("community_investment_eur", sa.Float, nullable=True),
        sa.Column("gender_diversity_pct", sa.Float, nullable=True),
        sa.Column("health_safety_incidents", sa.Integer, nullable=True),
        # Governance
        sa.Column("board_independence_pct", sa.Float, nullable=True),
        sa.Column("audit_completed", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("esg_reporting_standard", sa.String(50), nullable=True),
        # EU Taxonomy
        sa.Column("taxonomy_eligible", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("taxonomy_aligned", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("taxonomy_activity", sa.String(100), nullable=True),
        # SFDR
        sa.Column("sfdr_article", sa.Integer, nullable=True),
        # SDG contributions
        sa.Column("sdg_contributions", postgresql.JSONB, nullable=True),
        # AI narrative
        sa.Column("esg_narrative", sa.Text, nullable=True),
        # Unique constraint
        sa.UniqueConstraint("project_id", "period", name="uq_esg_project_period"),
    )

    op.create_index("ix_esg_metrics_project_id", "esg_metrics", ["project_id"])
    op.create_index("ix_esg_metrics_org_id", "esg_metrics", ["org_id"])
    op.create_index(
        "ix_esg_metrics_org_period", "esg_metrics", ["org_id", "period"]
    )


def downgrade() -> None:
    op.drop_index("ix_esg_metrics_org_period", table_name="esg_metrics")
    op.drop_index("ix_esg_metrics_org_id", table_name="esg_metrics")
    op.drop_index("ix_esg_metrics_project_id", table_name="esg_metrics")
    op.drop_table("esg_metrics")
