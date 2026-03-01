"""add_composite_indexes_and_unique_constraints

Revision ID: 4b570868cd8e
Revises: 1793197fd8ed
Create Date: 2026-03-01 15:12:19.914634

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "4b570868cd8e"
down_revision: str | None = "1793197fd8ed"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Composite indexes for query performance ───────────────────────────────

    # 1. metric_snapshots — time-series lookup (all trend/benchmark queries)
    op.create_index(
        "ix_metric_snapshots_lookup",
        "metric_snapshots",
        ["org_id", "entity_type", "metric_name", "recorded_at"],
        if_not_exists=True,
    )

    # 2. audit_logs — admin audit trail queries (org + time range)
    op.create_index(
        "ix_audit_logs_org_time",
        "audit_logs",
        ["org_id", "created_at"],
        if_not_exists=True,
    )

    # 3. usage_events — feature analytics queries (org + event_type + time)
    op.create_index(
        "ix_usage_events_org_type_time",
        "usage_events",
        ["org_id", "event_type", "created_at"],
        if_not_exists=True,
    )

    # 4. webhook_deliveries — delivery retry queue (status + next_retry_at)
    op.create_index(
        "ix_webhook_deliveries_status_retry",
        "webhook_deliveries",
        ["status", "next_retry_at"],
        if_not_exists=True,
    )

    # 5. document_access_logs — engagement analytics (document + time)
    op.create_index(
        "ix_doc_access_logs_doc_time",
        "document_access_logs",
        ["document_id", "timestamp"],
        if_not_exists=True,
    )

    # 6. ai_task_logs — AI performance monitoring (org + status + time)
    op.create_index(
        "ix_ai_task_logs_org_status_time",
        "ai_task_logs",
        ["org_id", "status", "created_at"],
        if_not_exists=True,
    )

    # 7. signal_scores — project score history (project + time)
    op.create_index(
        "ix_signal_scores_project_time",
        "signal_scores",
        ["project_id", "created_at"],
        if_not_exists=True,
    )

    # ── Unique constraints for data integrity ─────────────────────────────────

    # 8. metric_snapshots — prevent duplicate daily snapshots (idempotent beat tasks)
    op.create_index(
        "uq_metric_snapshots_daily",
        "metric_snapshots",
        [
            "org_id",
            "entity_id",
            "entity_type",
            "metric_name",
            sa.text("(recorded_at::date)"),
        ],
        unique=True,
        if_not_exists=True,
        postgresql_where=sa.text("entity_id IS NOT NULL"),
    )

    # 9. cashflow_projections — prevent duplicate projections per assumption + date
    op.create_index(
        "uq_cashflow_projections_unique",
        "cashflow_projections",
        [
            "org_id",
            "assumption_id",
            sa.text("(projection_date::date)"),
        ],
        unique=True,
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index("uq_cashflow_projections_unique", table_name="cashflow_projections", if_exists=True)
    op.drop_index("uq_metric_snapshots_daily", table_name="metric_snapshots", if_exists=True)
    op.drop_index("ix_signal_scores_project_time", table_name="signal_scores", if_exists=True)
    op.drop_index("ix_ai_task_logs_org_status_time", table_name="ai_task_logs", if_exists=True)
    op.drop_index("ix_doc_access_logs_doc_time", table_name="document_access_logs", if_exists=True)
    op.drop_index("ix_webhook_deliveries_status_retry", table_name="webhook_deliveries", if_exists=True)
    op.drop_index("ix_usage_events_org_type_time", table_name="usage_events", if_exists=True)
    op.drop_index("ix_audit_logs_org_time", table_name="audit_logs", if_exists=True)
    op.drop_index("ix_metric_snapshots_lookup", table_name="metric_snapshots", if_exists=True)
