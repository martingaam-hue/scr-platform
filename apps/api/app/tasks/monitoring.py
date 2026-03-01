"""Celery tasks for covenant & KPI monitoring."""

import structlog
from celery import shared_task

logger = structlog.get_logger()


@shared_task(name="tasks.check_all_covenants")
def check_all_covenants() -> dict:
    """Run daily at 6am. Checks all non-waived covenants across all orgs."""
    import asyncio

    async def _run():
        from sqlalchemy import distinct, select

        from app.core.database import async_session_factory
        from app.models.monitoring import Covenant
        from app.modules.monitoring.service import MonitoringService

        async with async_session_factory() as db:
            org_ids = (
                await db.execute(
                    select(distinct(Covenant.org_id)).where(
                        Covenant.status != "waived",
                        Covenant.is_deleted.is_(False),
                    )
                )
            ).scalars().all()

            total_changes = 0
            for org_id in org_ids:
                svc = MonitoringService(db, org_id)
                try:
                    changes = await svc.check_covenants()
                    total_changes += len(changes)
                except Exception as exc:
                    logger.warning(
                        "check_covenants_org_failed",
                        org_id=str(org_id),
                        error=str(exc),
                    )

            await db.commit()
            return {"org_count": len(org_ids), "status_changes": total_changes}

    result = asyncio.run(_run())
    logger.info("check_all_covenants_complete", **result)
    return result
