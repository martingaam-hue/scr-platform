"""Compliance deadline reminder and overdue-flagging Celery tasks."""

from __future__ import annotations

import asyncio

import structlog
from celery import shared_task

logger = structlog.get_logger()


@shared_task(name="tasks.check_upcoming_deadlines", bind=True, max_retries=3, default_retry_delay=300)
def check_upcoming_deadlines(self) -> dict:
    """Send 30/14/7/1-day reminder notifications for upcoming compliance deadlines."""
    from app.core.database import AsyncSessionLocal
    from app.modules.compliance.service import get_reminder_candidates, mark_reminder_sent
    from app.models.core import Notification

    async def _run() -> dict:
        sent = 0
        async with AsyncSessionLocal() as db:
            for days in [30, 14, 7, 1]:
                deadlines = await get_reminder_candidates(db, days)
                for deadline in deadlines:
                    notif = Notification(
                        user_id=deadline.assigned_to or deadline.org_id,
                        notification_type="action_required",
                        title=f"Compliance deadline in {days} day{'s' if days > 1 else ''}: {deadline.title}",
                        message=(
                            f"{deadline.category.replace('_', ' ').title()} — "
                            f"Due {deadline.due_date.isoformat()}. "
                            f"Jurisdiction: {deadline.jurisdiction or 'N/A'}."
                        ),
                    )
                    db.add(notif)
                    await mark_reminder_sent(db, deadline, days)
                    sent += 1
            await db.commit()
        logger.info("compliance.reminders_sent", count=sent)
        return {"status": "ok", "reminders_sent": sent}

    try:
        return asyncio.get_event_loop().run_until_complete(_run())
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(name="tasks.flag_overdue_deadlines", bind=True, max_retries=3, default_retry_delay=300)
def flag_overdue_deadlines(self) -> dict:
    """Mark past-due deadlines as overdue and notify assigned users."""
    from app.core.database import AsyncSessionLocal
    from app.modules.compliance.service import flag_overdue

    async def _run() -> dict:
        async with AsyncSessionLocal() as db:
            count = await flag_overdue(db)
        return {"status": "ok", "flagged_overdue": count}

    try:
        return asyncio.get_event_loop().run_until_complete(_run())
    except Exception as exc:
        raise self.retry(exc=exc)
