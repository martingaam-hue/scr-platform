"""CRM Sync Celery task — runs every 15 minutes to sync all active CRM connections."""

from __future__ import annotations

import asyncio

import structlog
from celery import shared_task
from sqlalchemy import select

logger = structlog.get_logger()


@shared_task(name="tasks.sync_crm_connections")
def sync_crm_connections() -> dict:
    """Run every 15 minutes. Sync all active CRM connections."""
    return asyncio.run(_run())


async def _run() -> dict:
    from app.core.database import async_session_factory
    from app.models.crm import CRMConnection
    from app.modules.crm_sync.service import CRMSyncService

    async with async_session_factory() as db:
        result = await db.execute(
            select(CRMConnection).where(CRMConnection.is_active.is_(True))
        )
        connections = result.scalars().all()
        synced = 0
        for conn in connections:
            try:
                svc = CRMSyncService(db, conn.org_id)
                await svc.trigger_sync(conn.id)
                synced += 1
            except Exception as e:
                logger.warning(
                    "crm_sync_connection_failed",
                    connection_id=str(conn.id),
                    org_id=str(conn.org_id),
                    error=str(e),
                )
        await db.commit()
        logger.info("crm_sync_complete", connections_synced=synced)
        return {"connections_synced": synced}
