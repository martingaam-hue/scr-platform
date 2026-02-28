"""Gamification service — badge evaluation, quest generation, leaderboard."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gamification import Badge, ImprovementQuest, UserBadge

logger = structlog.get_logger()

_BADGE_CATALOG = [
    {"slug": "first_steps", "name": "First Steps", "icon": "🚀", "category": "onboarding",
     "criteria": {"event": "onboarding_complete"}, "points": 10, "rarity": "common",
     "description": "Completed platform onboarding."},
    {"slug": "first_upload", "name": "First Upload", "icon": "📄", "category": "data_room",
     "criteria": {"event": "document_upload", "count": 1}, "points": 5, "rarity": "common",
     "description": "Uploaded first document to the data room."},
    {"slug": "data_room_pro", "name": "Data Room Pro", "icon": "📁", "category": "data_room",
     "criteria": {"event": "document_upload", "count": 10}, "points": 25, "rarity": "uncommon",
     "description": "Uploaded 10 documents to the data room."},
    {"slug": "score_50", "name": "Getting Noticed", "icon": "⭐", "category": "signal_score",
     "criteria": {"signal_score_min": 50}, "points": 20, "rarity": "common",
     "description": "Achieved a Signal Score of 50+."},
    {"slug": "score_60", "name": "Rising Star", "icon": "🌟", "category": "signal_score",
     "criteria": {"signal_score_min": 60}, "points": 30, "rarity": "uncommon",
     "description": "Achieved a Signal Score of 60+."},
    {"slug": "score_70", "name": "Investment Grade", "icon": "💎", "category": "signal_score",
     "criteria": {"signal_score_min": 70}, "points": 40, "rarity": "rare",
     "description": "Achieved a Signal Score of 70+."},
    {"slug": "score_80", "name": "Investor Ready", "icon": "🏆", "category": "signal_score",
     "criteria": {"signal_score_min": 80}, "points": 100, "rarity": "epic",
     "description": "Achieved a Signal Score of 80+."},
    {"slug": "score_90", "name": "Elite Project", "icon": "👑", "category": "signal_score",
     "criteria": {"signal_score_min": 90}, "points": 200, "rarity": "legendary",
     "description": "Achieved a Signal Score of 90+."},
    {"slug": "first_match", "name": "First Match", "icon": "🤝", "category": "matching",
     "criteria": {"event": "investor_match", "count": 1}, "points": 30, "rarity": "uncommon",
     "description": "Received first investor match."},
    {"slug": "popular_project", "name": "Popular Project", "icon": "🔥", "category": "matching",
     "criteria": {"event": "investor_match", "count": 5}, "points": 50, "rarity": "rare",
     "description": "Received 5 investor matches."},
    {"slug": "certified", "name": "Certified", "icon": "✅", "category": "certification",
     "criteria": {"event": "certification_earned"}, "points": 75, "rarity": "rare",
     "description": "Earned Investor Readiness Certification."},
]


async def seed_badges(db: AsyncSession) -> None:
    """Upsert badge catalog (run at startup)."""
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    for badge_data in _BADGE_CATALOG:
        stmt = (
            pg_insert(Badge)
            .values(**badge_data)
            .on_conflict_do_update(index_elements=["slug"], set_=badge_data)
        )
        await db.execute(stmt)
    await db.commit()


async def _check_criteria(
    db: AsyncSession,
    criteria: dict[str, Any],
    user_id: uuid.UUID,
    project_id: uuid.UUID | None,
    event: str | None,
) -> bool:
    """Evaluate whether a badge's criteria is met."""
    if "event" in criteria:
        if event != criteria["event"]:
            return False
        if "count" in criteria:
            # Count how many times user has triggered this event (via document count, match count, etc.)
            if criteria["event"] == "document_upload" and project_id:
                from app.models.dataroom import Document
                result = await db.execute(
                    select(func.count(Document.id)).where(
                        Document.project_id == project_id, Document.is_deleted == False
                    )
                )
                count = result.scalar_one() or 0
                return count >= criteria["count"]
            if criteria["event"] == "investor_match" and project_id:
                from app.models.matching import MatchResult
                result = await db.execute(
                    select(func.count(MatchResult.id)).where(MatchResult.project_id == project_id)
                )
                count = result.scalar_one() or 0
                return count >= criteria["count"]
        return True

    if "signal_score_min" in criteria and project_id:
        from app.models.projects import SignalScore
        result = await db.execute(
            select(SignalScore)
            .where(SignalScore.project_id == project_id)
            .order_by(SignalScore.created_at.desc())
            .limit(1)
        )
        score = result.scalar_one_or_none()
        if score:
            return (score.overall_score or 0) >= criteria["signal_score_min"]

    return False


async def evaluate_badges(
    db: AsyncSession, user_id: uuid.UUID, project_id: uuid.UUID | None, event: str | None
) -> list[UserBadge]:
    """Check all badges and award newly qualifying ones."""
    all_badges_result = await db.execute(select(Badge).where(Badge.is_deleted == False))
    all_badges = all_badges_result.scalars().all()

    # Get slugs already earned
    earned_result = await db.execute(
        select(Badge.slug).join(UserBadge, UserBadge.badge_id == Badge.id).where(
            UserBadge.user_id == user_id, UserBadge.project_id == project_id
        )
    )
    earned_slugs = {r[0] for r in earned_result.all()}

    newly_earned: list[UserBadge] = []
    for badge in all_badges:
        if badge.slug in earned_slugs:
            continue
        try:
            qualifies = await _check_criteria(db, badge.criteria, user_id, project_id, event)
        except Exception:
            continue
        if qualifies:
            ub = UserBadge(user_id=user_id, project_id=project_id, badge_id=badge.id)
            db.add(ub)
            newly_earned.append(ub)
            logger.info("badge.earned", slug=badge.slug, user_id=str(user_id))

    if newly_earned:
        await db.commit()
    return newly_earned


async def get_user_badges(db: AsyncSession, user_id: uuid.UUID, project_id: uuid.UUID | None = None) -> list[dict]:
    stmt = (
        select(UserBadge, Badge)
        .join(Badge, UserBadge.badge_id == Badge.id)
        .where(UserBadge.user_id == user_id)
    )
    if project_id:
        stmt = stmt.where(UserBadge.project_id == project_id)
    result = await db.execute(stmt)
    rows = result.all()
    return [
        {
            "id": str(ub.id),
            "slug": b.slug,
            "name": b.name,
            "icon": b.icon,
            "description": b.description,
            "category": b.category,
            "points": b.points,
            "rarity": b.rarity,
            "earned_at": ub.created_at.isoformat(),
        }
        for ub, b in rows
    ]


async def generate_quests(db: AsyncSession, project_id: uuid.UUID) -> list[ImprovementQuest]:
    """Generate AI-informed improvement quests based on score gaps."""
    # Clear existing active quests
    existing_result = await db.execute(
        select(ImprovementQuest).where(
            ImprovementQuest.project_id == project_id,
            ImprovementQuest.status == "active",
            ImprovementQuest.is_deleted == False,
        )
    )
    for q in existing_result.scalars().all():
        q.status = "expired"
    await db.flush()

    quests: list[ImprovementQuest] = []

    # Signal score gap quest
    try:
        from app.models.projects import SignalScore
        score_result = await db.execute(
            select(SignalScore).where(SignalScore.project_id == project_id)
            .order_by(SignalScore.created_at.desc()).limit(1)
        )
        score = score_result.scalar_one_or_none()
        if score:
            # Weakest dimension
            dims = score.dimensions or {}
            if dims:
                weakest_dim, weakest_val = min(dims.items(), key=lambda x: x[1])
                quests.append(ImprovementQuest(
                    project_id=project_id,
                    title=f"Improve {weakest_dim.replace('_', ' ').title()}",
                    description=f"Your {weakest_dim} score is {weakest_val}/100. Upload supporting documents to improve it.",
                    action_type="improve_dimension",
                    target_dimension=weakest_dim,
                    estimated_score_impact=8,
                ))
            # Next milestone
            current = score.overall_score or 0
            next_milestone = next((m for m in [50, 60, 70, 80, 90] if m > current), None)
            if next_milestone:
                quests.append(ImprovementQuest(
                    project_id=project_id,
                    title=f"Reach Signal Score {next_milestone}",
                    description=f"You're {next_milestone - current} points away from the next milestone badge!",
                    action_type="improve_dimension",
                    estimated_score_impact=next_milestone - current,
                ))
    except Exception as exc:
        logger.warning("gamification.quest_gen_failed", error=str(exc))

    # Document upload quest
    quests.append(ImprovementQuest(
        project_id=project_id,
        title="Complete Your Data Room",
        description="Investors expect a complete data room. Ensure all key documents are uploaded.",
        action_type="upload_document",
        estimated_score_impact=5,
    ))

    for q in quests:
        db.add(q)
    await db.commit()
    return quests


async def get_progress(db: AsyncSession, user_id: uuid.UUID, project_id: uuid.UUID) -> dict:
    """Progress summary: score, badges, quests, next milestone."""
    badges = await get_user_badges(db, user_id, project_id)
    total_points = sum(b["points"] for b in badges)

    quests_result = await db.execute(
        select(ImprovementQuest).where(
            ImprovementQuest.project_id == project_id,
            ImprovementQuest.status == "active",
            ImprovementQuest.is_deleted == False,
        )
    )
    quests = quests_result.scalars().all()

    from app.models.projects import SignalScore
    score_result = await db.execute(
        select(SignalScore).where(SignalScore.project_id == project_id)
        .order_by(SignalScore.created_at.desc()).limit(1)
    )
    score = score_result.scalar_one_or_none()
    current_score = score.overall_score if score else 0
    next_milestone = next((m for m in [50, 60, 70, 80, 90] if m > current_score), None)

    return {
        "signal_score": current_score,
        "badge_count": len(badges),
        "total_points": total_points,
        "active_quests": len(quests),
        "next_milestone": next_milestone,
        "points_to_next_milestone": (next_milestone - current_score) if next_milestone else None,
        "badges": badges,
        "quests": [q.to_dict() for q in quests],
    }
