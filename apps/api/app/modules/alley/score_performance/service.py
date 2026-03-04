"""Alley Score Performance (Score Journey) service."""
from __future__ import annotations
import uuid
from datetime import datetime, timezone

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.middleware.tenant import tenant_filter
from app.models.projects import Project, SignalScore
from app.modules.alley.score_performance.schemas import (
    DimensionTrendPoint,
    DimensionTrendsResponse,
    ProjectScorePerformanceSummary,
    ScoreInsightItem,
    ScoreInsightsResponse,
    ScoreJourneyPoint,
    ScoreJourneyResponse,
)

logger = structlog.get_logger()


async def _get_scores_ordered(db: AsyncSession, project_id: uuid.UUID) -> list[SignalScore]:
    result = await db.execute(
        select(SignalScore)
        .where(SignalScore.project_id == project_id)
        .order_by(SignalScore.version.asc())
    )
    return list(result.scalars().all())


async def list_performance_summaries(
    db: AsyncSession, org_id: uuid.UUID
) -> list[ProjectScorePerformanceSummary]:
    stmt = select(Project).where(Project.is_deleted.is_(False))
    stmt = tenant_filter(stmt, org_id, Project)
    result = await db.execute(stmt)
    projects = result.scalars().all()

    items = []
    for p in projects:
        scores = await _get_scores_ordered(db, p.id)
        if not scores:
            continue
        first = scores[0].overall_score
        last = scores[-1].overall_score
        diff = last - first
        if len(scores) == 1:
            trend = "new"
        elif diff > 3:
            trend = "improving"
        elif diff < -3:
            trend = "declining"
        else:
            trend = "stable"

        items.append(ProjectScorePerformanceSummary(
            project_id=p.id,
            project_name=p.name,
            current_score=last,
            start_score=first,
            total_improvement=diff,
            versions=len(scores),
            trend=trend,
        ))
    return items


async def get_score_journey(
    db: AsyncSession, project_id: uuid.UUID, org_id: uuid.UUID
) -> ScoreJourneyResponse:
    stmt = select(Project).where(Project.id == project_id, Project.is_deleted.is_(False))
    stmt = tenant_filter(stmt, org_id, Project)
    result = await db.execute(stmt)
    if not result.scalar_one_or_none():
        raise LookupError(f"Project {project_id} not found")

    scores = await _get_scores_ordered(db, project_id)
    journey = []
    for i, s in enumerate(scores):
        prev_score = scores[i - 1].overall_score if i > 0 else s.overall_score
        journey.append(ScoreJourneyPoint(
            version=s.version,
            overall_score=s.overall_score,
            calculated_at=s.calculated_at,
            score_change=s.overall_score - prev_score,
        ))

    total = (scores[-1].overall_score - scores[0].overall_score) if len(scores) > 1 else 0
    return ScoreJourneyResponse(project_id=project_id, journey=journey, total_improvement=total)


async def get_dimension_trends(
    db: AsyncSession, project_id: uuid.UUID, org_id: uuid.UUID
) -> DimensionTrendsResponse:
    stmt = select(Project).where(Project.id == project_id, Project.is_deleted.is_(False))
    stmt = tenant_filter(stmt, org_id, Project)
    result = await db.execute(stmt)
    if not result.scalar_one_or_none():
        raise LookupError(f"Project {project_id} not found")

    scores = await _get_scores_ordered(db, project_id)
    trends = [
        DimensionTrendPoint(
            version=s.version,
            calculated_at=s.calculated_at,
            project_viability=s.project_viability_score,
            financial_planning=s.financial_planning_score,
            team_strength=s.team_strength_score,
            risk_assessment=s.risk_assessment_score,
            esg=s.esg_score,
            market_opportunity=s.market_opportunity_score,
        )
        for s in scores
    ]
    return DimensionTrendsResponse(project_id=project_id, trends=trends)


async def get_score_insights(
    db: AsyncSession, project_id: uuid.UUID, org_id: uuid.UUID
) -> ScoreInsightsResponse:
    stmt = select(Project).where(Project.id == project_id, Project.is_deleted.is_(False))
    stmt = tenant_filter(stmt, org_id, Project)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if not project:
        raise LookupError(f"Project {project_id} not found")

    scores = await _get_scores_ordered(db, project_id)
    if not scores:
        raise LookupError("No score history yet")

    latest = scores[-1]
    history_text = "\n".join(
        f"v{s.version} ({s.calculated_at.date()}): overall={s.overall_score}, "
        f"viability={s.project_viability_score}, financial={s.financial_planning_score}, "
        f"esg={s.esg_score}"
        for s in scores[-5:]  # last 5 versions
    )

    prompt = (
        f"You are a project development coach. Analyse this project's score trajectory.\n\n"
        f"Project: {project.name} ({project.project_type.value}, {project.geography_country})\n"
        f"Score history (last 5 versions):\n{history_text}\n\n"
        "Identify 3-4 actionable insights. Respond ONLY with valid JSON:\n"
        '[{"dimension": "...", "insight": "...", "recommendation": "...", "estimated_impact": <1-15>}]'
    )

    insights: list[ScoreInsightItem] = []
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{settings.AI_GATEWAY_URL}/v1/completions",
                json={"prompt": prompt, "task_type": "alley_score_insights", "max_tokens": 800, "temperature": 0.3},
                headers={"Authorization": f"Bearer {settings.AI_GATEWAY_API_KEY}"},
            )
        resp.raise_for_status()
        import json, re
        raw = resp.json().get("content", "")
        match = re.search(r'\[.*\]', raw, re.DOTALL)
        if match:
            data = json.loads(match.group())
            insights = [ScoreInsightItem(**item) for item in data if isinstance(item, dict)]
    except Exception as exc:
        logger.warning("score_insights_ai_failed", error=str(exc))

    if not insights:
        # Fallback: synthetic insights from lowest-scoring dimensions
        dim_scores = {
            "project_viability": latest.project_viability_score,
            "financial_planning": latest.financial_planning_score,
            "team_strength": latest.team_strength_score,
            "risk_assessment": latest.risk_assessment_score,
            "esg": latest.esg_score,
            "market_opportunity": latest.market_opportunity_score,
        }
        for dim, score in sorted(dim_scores.items(), key=lambda x: x[1])[:3]:
            insights.append(ScoreInsightItem(
                dimension=dim,
                insight=f"Your {dim.replace('_', ' ')} score is {score}/100",
                recommendation=f"Focus on improving {dim.replace('_', ' ')} by uploading relevant documentation",
                estimated_impact=10,
            ))

    return ScoreInsightsResponse(
        project_id=project_id,
        insights=insights,
        generated_at=datetime.now(timezone.utc),
    )
