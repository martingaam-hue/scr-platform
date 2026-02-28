"""Weekly digest service — aggregates platform activity for email digest."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any

import httpx
import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.ai import AITaskLog

logger = structlog.get_logger()


async def gather_digest_data(
    db: AsyncSession,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    since: datetime,
) -> dict[str, Any]:
    """Aggregate platform activity for the past week."""
    from app.models.enums import AITaskStatus

    # Count AI tasks completed this week
    ai_tasks_result = await db.execute(
        select(func.count(AITaskLog.id)).where(
            AITaskLog.org_id == org_id,
            AITaskLog.created_at >= since,
            AITaskLog.status == AITaskStatus.COMPLETED,
        )
    )
    ai_tasks_count = ai_tasks_result.scalar() or 0

    # Count AI tasks by agent type
    from app.models.enums import AIAgentType
    agent_counts_result = await db.execute(
        select(AITaskLog.agent_type, func.count(AITaskLog.id).label("count"))
        .where(
            AITaskLog.org_id == org_id,
            AITaskLog.created_at >= since,
            AITaskLog.status == AITaskStatus.COMPLETED,
        )
        .group_by(AITaskLog.agent_type)
    )
    agent_breakdown = {
        row.agent_type.value: row.count
        for row in agent_counts_result.all()
    }

    # Recent projects (just count)
    try:
        from app.models.projects import Project
        projects_result = await db.execute(
            select(func.count(Project.id)).where(
                Project.org_id == org_id,
                Project.created_at >= since,
                Project.is_deleted.is_(False),
            )
        )
        new_projects = projects_result.scalar() or 0
    except Exception:
        new_projects = 0

    # Documents processed
    try:
        from app.models.dataroom import DataroomDocument
        docs_result = await db.execute(
            select(func.count(DataroomDocument.id)).where(
                DataroomDocument.org_id == org_id,
                DataroomDocument.created_at >= since,
                DataroomDocument.is_deleted.is_(False),
            )
        )
        new_documents = docs_result.scalar() or 0
    except Exception:
        new_documents = 0

    return {
        "period_start": since.isoformat(),
        "period_end": datetime.utcnow().isoformat(),
        "ai_tasks_completed": ai_tasks_count,
        "ai_agent_breakdown": agent_breakdown,
        "new_projects": new_projects,
        "new_documents": new_documents,
    }


async def generate_digest_summary(
    activity_data: dict[str, Any],
    org_name: str,
) -> str:
    """Call AI gateway to generate a narrative digest summary."""
    import json

    prompt_data = {
        "org_name": org_name,
        "activity_summary": json.dumps(activity_data, indent=2),
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{settings.AI_GATEWAY_URL}/v1/completions",
                json={
                    "task_type": "generate_digest_summary",
                    "prompt": json.dumps(prompt_data),
                    "org_id": "system",
                },
                headers={"Authorization": f"Bearer {settings.AI_GATEWAY_API_KEY}"},
            )
            if resp.status_code == 200:
                return resp.json().get("content", _fallback_summary(activity_data))
    except Exception as e:
        logger.warning("digest_summary_generation_failed", error=str(e))

    return _fallback_summary(activity_data)


def _fallback_summary(data: dict[str, Any]) -> str:
    """Simple template-based summary when AI is unavailable."""
    tasks = data.get("ai_tasks_completed", 0)
    projects = data.get("new_projects", 0)
    docs = data.get("new_documents", 0)
    parts = [f"This week your team completed {tasks} AI-powered analyses"]
    if projects:
        parts.append(f"added {projects} new project{'s' if projects != 1 else ''}")
    if docs:
        parts.append(f"uploaded {docs} document{'s' if docs != 1 else ''}")
    return ", ".join(parts) + "."


# ── Digest preferences ─────────────────────────────────────────────────────────

_DEFAULT_PREFS: dict[str, Any] = {
    "is_subscribed": True,
    "frequency": "weekly",
}


async def get_preferences(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> dict[str, Any]:
    """Return digest preferences stored in user.preferences['digest']."""
    from app.models.core import User

    user = await db.get(User, user_id)
    if not user:
        return dict(_DEFAULT_PREFS)
    prefs = user.preferences or {}
    return prefs.get("digest", dict(_DEFAULT_PREFS))


async def update_preferences(
    db: AsyncSession,
    user_id: uuid.UUID,
    is_subscribed: bool,
    frequency: str,
) -> dict[str, Any]:
    """Persist digest preferences in user.preferences['digest'].

    Also updates the legacy ``email_digest_enabled`` top-level key so that
    the ``tasks.send_weekly_digests`` Celery beat task continues to honour
    the opt-in/out setting.
    """
    from app.models.core import User

    user = await db.get(User, user_id)
    if not user:
        raise LookupError(f"User {user_id} not found")

    prefs = dict(user.preferences or {})
    prefs["digest"] = {"is_subscribed": is_subscribed, "frequency": frequency}
    # Legacy key used by weekly_digest.py Celery task
    prefs["email_digest_enabled"] = is_subscribed
    user.preferences = prefs
    await db.commit()
    return prefs["digest"]
