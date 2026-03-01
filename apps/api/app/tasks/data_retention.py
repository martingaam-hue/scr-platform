"""Data retention tasks — prevent unbounded table growth.

Runs nightly (04:00 UTC) and enforces per-table retention policies.
Tables marked archive=True log row counts for future S3 archiving;
tables with archive=False are hard-deleted in 10 000-row batches to
avoid long-held locks.
"""

from datetime import datetime, timedelta

import structlog
from celery import shared_task
from sqlalchemy import text

logger = structlog.get_logger()

# (table_name, retain_days, archive_instead_of_delete)
_POLICIES: list[tuple[str, int, bool]] = [
    ("audit_logs",            365, True),   # Keep 1 year, archive older rows
    ("document_access_logs",  365, True),   # Keep 1 year, archive
    ("ai_task_logs",           90, True),   # Keep 90 days, archive
    ("digest_logs",            90, False),  # Keep 90 days, delete
    ("usage_events",          180, False),  # Keep 6 months, delete
    ("webhook_deliveries",     30, False),  # Keep 30 days (delivered), delete
]

_BATCH = 10_000  # rows per DELETE to avoid long locks

# Public alias for external inspection / tests
RETENTION_POLICIES = _POLICIES


@shared_task(name="data_retention_cleanup", bind=True, max_retries=1)  # type: ignore[misc]
def data_retention_cleanup(self) -> dict:  # type: ignore[misc]
    """Enforce retention policies on high-growth tables."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from app.core.config import settings

    engine = create_engine(settings.DATABASE_URL_SYNC)
    results: dict[str, dict] = {}

    with Session(engine) as session:
        for table, days, archive in _POLICIES:
            cutoff = datetime.utcnow() - timedelta(days=days)
            try:
                count_row = session.execute(
                    text(f"SELECT COUNT(*) FROM {table} WHERE created_at < :cutoff"),  # noqa: S608
                    {"cutoff": cutoff},
                ).scalar()
                count: int = count_row or 0

                if count == 0:
                    results[table] = {"status": "clean", "rows": 0}
                    continue

                if archive:
                    # Log candidates — actual S3 archive is a separate pipeline step
                    logger.info(
                        "retention_archive_candidate",
                        table=table,
                        rows=count,
                        cutoff=str(cutoff),
                    )
                    results[table] = {"status": "logged", "archive_candidates": count}
                else:
                    total = 0
                    while True:
                        result = session.execute(
                            text(f"""
                                DELETE FROM {table}
                                WHERE id IN (
                                    SELECT id FROM {table}
                                    WHERE created_at < :cutoff
                                    LIMIT :batch
                                )
                            """),  # noqa: S608
                            {"cutoff": cutoff, "batch": _BATCH},
                        )
                        deleted = result.rowcount
                        total += deleted
                        session.commit()
                        if deleted < _BATCH:
                            break
                    logger.info("retention_cleanup", table=table, deleted=total)
                    results[table] = {"status": "cleaned", "deleted": total}

            except Exception as exc:  # noqa: BLE001
                logger.error("retention_error", table=table, error=str(exc))
                session.rollback()
                results[table] = {"status": "failed", "error": str(exc)}

    return results


@shared_task(name="cleanup_org_rag_namespace", queue="retention")
def cleanup_org_rag_namespace(org_id: str) -> None:
    """Delete all RAG vectors for a deleted organization's namespace."""
    import httpx
    from app.core.config import settings
    ai_gateway_url = getattr(settings, "AI_GATEWAY_URL", "http://localhost:8001")
    api_key = getattr(settings, "AI_GATEWAY_API_KEY", "")
    try:
        response = httpx.delete(
            f"{ai_gateway_url}/v1/namespaces/{org_id}",
            headers={"X-API-Key": api_key},
            timeout=60,
        )
        if response.status_code in (200, 204, 404):
            logger.info("rag_namespace.cleaned", org_id=org_id, status=response.status_code)
        else:
            logger.error("rag_namespace.cleanup_failed", org_id=org_id, status=response.status_code)
    except Exception as exc:
        logger.error("rag_namespace.cleanup_error", org_id=org_id, error=str(exc))
