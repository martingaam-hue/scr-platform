"""Celery task: check Q&A SLA breaches every 30 minutes."""

from __future__ import annotations

import asyncio

from celery import shared_task


@shared_task(name="tasks.check_qa_sla")
def check_qa_sla() -> dict:
    """Run every 30 minutes. Flag SLA breaches for all open Q&A questions."""

    async def _run() -> dict:
        from sqlalchemy import distinct, select

        from app.core.database import async_session_factory
        from app.models.qa import QAQuestion
        from app.modules.qa_workflow.service import QAService

        async with async_session_factory() as db:
            org_ids = (
                await db.execute(
                    select(distinct(QAQuestion.org_id)).where(
                        QAQuestion.status.in_(["open", "assigned", "in_progress"]),
                        QAQuestion.is_deleted.is_(False),
                    )
                )
            ).scalars().all()

            total = 0
            for org_id in org_ids:
                svc = QAService(db, org_id)
                breaches = await svc.check_sla_breaches()
                total += len(breaches)

            await db.commit()
            return {"total_breaches": total, "orgs_checked": len(org_ids)}

    result = asyncio.run(_run())
    return result
