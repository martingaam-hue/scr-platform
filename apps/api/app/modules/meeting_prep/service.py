"""Meeting Prep service — aggregate module data and generate AI briefings."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.meeting_prep import MeetingBriefing

logger = structlog.get_logger()

_AI_TIMEOUT = 90.0


# ── Data gathering helpers ────────────────────────────────────────────────────


def _safe(result: Any) -> Any:
    return result if not isinstance(result, Exception) else None


def _safe_dict(obj: Any) -> dict[str, Any] | None:
    if obj is None:
        return None
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    if isinstance(obj, dict):
        return obj
    return None


async def _get_project(db: AsyncSession, project_id: uuid.UUID, org_id: uuid.UUID) -> Any:
    from app.models.projects import Project
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.org_id == org_id, Project.is_deleted == False)
    )
    return result.scalar_one_or_none()


async def _get_signal_score(db: AsyncSession, project_id: uuid.UUID) -> Any:
    from app.models.projects import SignalScore
    result = await db.execute(
        select(SignalScore)
        .where(SignalScore.project_id == project_id)
        .order_by(SignalScore.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _get_risk_summary(db: AsyncSession, project_id: uuid.UUID) -> Any:
    from app.models.investors import RiskAssessment
    result = await db.execute(
        select(RiskAssessment)
        .where(RiskAssessment.project_id == project_id)
        .order_by(RiskAssessment.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _get_dd_status(db: AsyncSession, project_id: uuid.UUID, org_id: uuid.UUID) -> Any:
    from app.models.due_diligence import DDProjectChecklist
    result = await db.execute(
        select(DDProjectChecklist)
        .where(DDProjectChecklist.project_id == project_id, DDProjectChecklist.org_id == org_id)
        .order_by(DDProjectChecklist.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _get_doc_count(db: AsyncSession, project_id: uuid.UUID) -> int:
    from sqlalchemy import func
    from app.models.dataroom import Document
    result = await db.execute(
        select(func.count(Document.id)).where(
            Document.project_id == project_id,
            Document.is_deleted == False,
        )
    )
    return result.scalar_one() or 0


# ── AI generation ─────────────────────────────────────────────────────────────


async def _ai_generate_briefing(
    meeting_type: str,
    project: Any,
    signal_score: Any,
    risks: Any,
    dd_status: Any,
    doc_count: int,
    previous_meeting_date: date | None,
    db: AsyncSession | None = None,
) -> dict[str, Any]:
    context = {
        "meeting_type": meeting_type,
        "project": _safe_dict(project),
        "signal_score": _safe_dict(signal_score),
        "risks": _safe_dict(risks),
        "dd_status": _safe_dict(dd_status),
        "document_count": doc_count,
        "has_previous_meeting": previous_meeting_date is not None,
        "previous_meeting_date": str(previous_meeting_date) if previous_meeting_date else None,
    }

    # Try PromptRegistry for meeting_preparation prompt
    _registry_messages: list[dict[str, Any]] = []
    _template_id: str | None = None
    if db is not None:
        try:
            from app.services.prompt_registry import PromptRegistry
            _reg = PromptRegistry(db)
            _registry_messages, _template_id, _ = await _reg.render(
                "meeting_preparation",
                {
                    "meeting_type": meeting_type,
                    "project_name": getattr(project, "name", "") if project else "",
                    "project_type": getattr(project, "project_type", {}).value if project and hasattr(getattr(project, "project_type", None), "value") else "",
                    "signal_score": str(getattr(signal_score, "overall_score", "N/A")) if signal_score else "N/A",
                    "document_count": str(doc_count),
                    "has_previous_meeting": str(previous_meeting_date is not None),
                },
            )
        except Exception:
            pass  # fall back to hardcoded context payload

    try:
        payload: dict[str, Any]
        if _registry_messages:
            payload = {
                "task_type": "meeting_preparation",
                "messages": _registry_messages,
            }
        else:
            payload = {"task_type": "generate_meeting_briefing", "context": context}
        async with httpx.AsyncClient(timeout=_AI_TIMEOUT) as client:
            resp = await client.post(
                f"{settings.AI_GATEWAY_URL}/v1/completions",
                json=payload,
                headers={"X-API-Key": settings.AI_GATEWAY_API_KEY},
            )
            resp.raise_for_status()
            data = resp.json()
        if _template_id and db is not None:
            try:
                from app.services.prompt_registry import PromptRegistry
                await PromptRegistry(db).update_quality_metrics(_template_id, 1.0)
            except Exception:
                pass
        return data.get("validated_data") or {}
    except Exception as exc:
        logger.warning("meeting_prep.ai_failed", error=str(exc))
        return _fallback_briefing(meeting_type, project)


def _fallback_briefing(meeting_type: str, project: Any) -> dict[str, Any]:
    name = getattr(project, "name", "this project") if project else "this project"
    return {
        "executive_summary": f"Briefing for {meeting_type} meeting on {name}.",
        "key_metrics": {},
        "risk_flags": [],
        "dd_progress": {},
        "talking_points": [
            "Confirm project timeline and milestones",
            "Review financial model assumptions",
            "Discuss risk mitigation strategies",
            "Confirm regulatory status",
            "Next steps and action items",
        ],
        "questions_to_ask": [
            "What is the current project stage and key blockers?",
            "How does the financial model hold under stress scenarios?",
            "What regulatory approvals are still pending?",
            "Who are the key team members and their track records?",
            "What are the exit options and timeline?",
        ],
        "changes_since_last": [],
    }


# ── CRUD ──────────────────────────────────────────────────────────────────────


async def generate_briefing(
    db: AsyncSession,
    org_id: uuid.UUID,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    meeting_type: str,
    meeting_date: date | None = None,
    previous_meeting_date: date | None = None,
) -> MeetingBriefing:
    """Aggregate all module data and generate an AI briefing."""
    # Sequential awaits — asyncio.gather shares the DB connection which breaks
    # under NullPool (tests) and causes issues with some async drivers.
    async def _try(coro: Any) -> Any:
        try:
            return await coro
        except Exception as exc:
            return exc

    project = _safe(await _try(_get_project(db, project_id, org_id)))
    score = _safe(await _try(_get_signal_score(db, project_id)))
    risks = _safe(await _try(_get_risk_summary(db, project_id)))
    dd_status = _safe(await _try(_get_dd_status(db, project_id, org_id)))
    doc_count = _safe(await _try(_get_doc_count(db, project_id)))
    if isinstance(doc_count, Exception) or doc_count is None:
        doc_count = 0

    briefing_content = await _ai_generate_briefing(
        meeting_type=meeting_type,
        project=project,
        signal_score=score,
        risks=risks,
        dd_status=dd_status,
        doc_count=int(doc_count),
        previous_meeting_date=previous_meeting_date,
        db=db,
    )

    briefing = MeetingBriefing(
        org_id=org_id,
        project_id=project_id,
        created_by=user_id,
        meeting_type=meeting_type,
        meeting_date=meeting_date,
        previous_meeting_date=previous_meeting_date,
        briefing_content=briefing_content,
    )
    db.add(briefing)
    await db.flush()
    return briefing


async def list_briefings(
    db: AsyncSession,
    org_id: uuid.UUID,
    project_id: uuid.UUID | None = None,
) -> list[MeetingBriefing]:
    stmt = select(MeetingBriefing).where(
        MeetingBriefing.org_id == org_id,
        MeetingBriefing.is_deleted == False,
    ).order_by(MeetingBriefing.created_at.desc())
    if project_id:
        stmt = stmt.where(MeetingBriefing.project_id == project_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_briefing(db: AsyncSession, briefing_id: uuid.UUID, org_id: uuid.UUID) -> MeetingBriefing | None:
    result = await db.execute(
        select(MeetingBriefing).where(
            MeetingBriefing.id == briefing_id,
            MeetingBriefing.org_id == org_id,
            MeetingBriefing.is_deleted == False,
        )
    )
    return result.scalar_one_or_none()


async def update_briefing(
    db: AsyncSession,
    briefing_id: uuid.UUID,
    org_id: uuid.UUID,
    custom_overrides: dict[str, Any],
) -> MeetingBriefing | None:
    briefing = await get_briefing(db, briefing_id, org_id)
    if not briefing:
        return None
    briefing.custom_overrides = custom_overrides
    await db.flush()
    return briefing


async def delete_briefing(db: AsyncSession, briefing_id: uuid.UUID, org_id: uuid.UUID) -> bool:
    briefing = await get_briefing(db, briefing_id, org_id)
    if not briefing:
        return False
    briefing.is_deleted = True
    await db.flush()
    return True
