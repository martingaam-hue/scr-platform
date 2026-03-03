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
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from app.core.config import settings
    from app.models.crm import CRMConnection
    from app.modules.crm_sync.service import CRMSyncService

    # Create a fresh engine per invocation so it binds to the current event loop
    engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with session_factory() as db:
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
    finally:
        await engine.dispose()
