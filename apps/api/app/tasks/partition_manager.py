"""Monthly partition manager for high-growth tables.

In production, tables should be converted to PARTITION BY RANGE(created_at):
  ALTER TABLE metric_snapshots RENAME TO metric_snapshots_old;
  CREATE TABLE metric_snapshots (...) PARTITION BY RANGE (created_at);
  INSERT INTO metric_snapshots SELECT * FROM metric_snapshots_old;

This task is a no-op until tables are partitioned — it just checks and logs
what partitions WOULD be created, so we're ready when the tables are migrated.
"""
from __future__ import annotations

from celery import shared_task
from datetime import datetime, timedelta

import structlog

logger = structlog.get_logger()

PARTITIONED_TABLES = [
    "metric_snapshots",
    "usage_events",
    "audit_logs",
    "webhook_deliveries",
    "document_access_logs",
]


def _months_ahead(n: int = 3) -> list[tuple[datetime, datetime]]:
    """Return list of (start, end) pairs for next *n* months."""
    now = datetime.utcnow()
    result = []
    for i in range(n):
        start = (now.replace(day=1) + timedelta(days=32 * i)).replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        end = (start + timedelta(days=32)).replace(day=1)
        result.append((start, end))
    return result


@shared_task(name="ensure_partitions_exist")
def ensure_partitions_exist() -> dict:
    """Create next-month partitions for partitioned tables.

    Safe to run on non-partitioned tables — detects relkind='p' and skips.
    """
    from sqlalchemy import text
    from app.core.celery_db import get_celery_db_session

    months = _months_ahead(3)
    checked = []
    created = []

    with get_celery_db_session() as session:
        for table in PARTITIONED_TABLES:
            result = session.execute(
                text("SELECT relkind FROM pg_class WHERE relname = :t"),
                {"t": table},
            )
            row = result.first()

            if row and row[0] == "p":  # partitioned table
                for start, end in months:
                    partition_name = f"{table}_{start.strftime('%Y_%m')}"
                    try:
                        session.execute(
                            text(
                                f"CREATE TABLE IF NOT EXISTS {partition_name}"
                                f" PARTITION OF {table}"
                                f" FOR VALUES FROM ('{start.isoformat()}')"
                                f" TO ('{end.isoformat()}')"
                            )
                        )
                        session.commit()
                        created.append(partition_name)
                        logger.info("partition_created", table=table, partition=partition_name)
                    except Exception as exc:
                        session.rollback()
                        logger.debug(
                            "partition_already_exists_or_error",
                            table=table,
                            partition=partition_name,
                            error=str(exc),
                        )
            else:
                logger.debug("table_not_yet_partitioned", table=table)

            checked.append(table)

    return {
        "checked": checked,
        "created": created,
        "months": [s.isoformat() for s, _ in months],
    }
