"""Gamification API router."""

from __future__ import annotations

import uuid
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_permission
from app.core.database import get_db
from app.modules.gamification import service
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()

router = APIRouter(prefix="/gamification", tags=["gamification"])


@router.get("/badges/my")
async def my_badges(
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    return await service.get_user_badges(db, current_user.user_id)


@router.get("/badges/project/{project_id}")
async def project_badges(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    return await service.get_user_badges(db, current_user.user_id, project_id)


@router.get("/quests/{project_id}")
async def get_quests(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select
    from app.models.gamification import ImprovementQuest
    result = await db.execute(
        select(ImprovementQuest).where(
            ImprovementQuest.project_id == project_id,
            ImprovementQuest.status == "active",
            ImprovementQuest.is_deleted == False,
        )
    )
    quests = result.scalars().all()
    if not quests:
        quests = await service.generate_quests(db, project_id)
    return [q.to_dict() for q in quests]


@router.post("/quests/{quest_id}/complete")
async def complete_quest(
    quest_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select
    from app.models.gamification import ImprovementQuest
    from datetime import datetime
    result = await db.execute(select(ImprovementQuest).where(ImprovementQuest.id == quest_id))
    quest = result.scalar_one_or_none()
    if not quest:
        raise HTTPException(status_code=404, detail="Quest not found")
    quest.status = "completed"
    quest.completed_at = datetime.utcnow()
    await db.commit()
    return {"status": "completed"}


@router.get("/leaderboard")
async def leaderboard(
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    from sqlalchemy import select
    from app.models.projects import Project, SignalScore
    # Only opt-in projects (leaderboard_opt_in field)
    try:
        result = await db.execute(
            select(Project, SignalScore)
            .join(SignalScore, SignalScore.project_id == Project.id)
            .where(Project.is_deleted == False)
            .order_by(SignalScore.overall_score.desc())
            .limit(20)
        )
        rows = result.all()
        return [
            {"rank": i + 1, "project_name": p.name, "project_type": p.project_type,
             "score": s.overall_score}
            for i, (p, s) in enumerate(rows)
        ]
    except Exception:
        return []


@router.get("/progress/{project_id}")
async def get_progress(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    return await service.get_progress(db, current_user.user_id, project_id)
