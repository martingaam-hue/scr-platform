"""Alley-side Signal Score service — project holder perspective."""
from __future__ import annotations
import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.tenant import tenant_filter
from app.models.projects import Project, SignalScore
from app.modules.alley.signal_score.schemas import (
    AlleyProjectScoreSummary,
    BenchmarkResponse,
    GapActionItem,
    GapAnalysisResponse,
    ScoreHistoryPoint,
    ScoreHistoryResponse,
    SimulateResponse,
)

logger = structlog.get_logger()


async def _get_project(db: AsyncSession, project_id: uuid.UUID, org_id: uuid.UUID) -> Project:
    stmt = select(Project).where(
        Project.id == project_id,
        Project.is_deleted.is_(False),
    )
    stmt = tenant_filter(stmt, org_id, Project)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if not project:
        raise LookupError(f"Project {project_id} not found")
    return project


async def _latest_score(db: AsyncSession, project_id: uuid.UUID) -> SignalScore | None:
    result = await db.execute(
        select(SignalScore)
        .where(SignalScore.project_id == project_id)
        .order_by(SignalScore.version.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _prev_score(db: AsyncSession, project_id: uuid.UUID, current_version: int) -> SignalScore | None:
    if current_version <= 1:
        return None
    result = await db.execute(
        select(SignalScore)
        .where(SignalScore.project_id == project_id, SignalScore.version == current_version - 1)
        .limit(1)
    )
    return result.scalar_one_or_none()


def _trend(current: int, previous: int | None) -> tuple[str, int]:
    if previous is None:
        return "new", 0
    diff = current - previous
    if diff > 2:
        return "up", diff
    if diff < -2:
        return "down", diff
    return "stable", diff


async def list_scores(db: AsyncSession, org_id: uuid.UUID) -> list[AlleyProjectScoreSummary]:
    """List all projects for the org with their latest signal scores."""
    stmt = select(Project).where(
        Project.is_deleted.is_(False),
    )
    stmt = tenant_filter(stmt, org_id, Project)
    result = await db.execute(stmt)
    projects = result.scalars().all()

    items = []
    for project in projects:
        score = await _latest_score(db, project.id)
        if score is None:
            continue
        prev = await _prev_score(db, project.id, score.version)
        trend, change = _trend(score.overall_score, prev.overall_score if prev else None)
        items.append(AlleyProjectScoreSummary(
            project_id=project.id,
            project_name=project.name,
            overall_score=score.overall_score,
            project_viability_score=score.project_viability_score,
            financial_planning_score=score.financial_planning_score,
            team_strength_score=score.team_strength_score,
            risk_assessment_score=score.risk_assessment_score,
            esg_score=score.esg_score,
            market_opportunity_score=score.market_opportunity_score,
            version=score.version,
            calculated_at=score.calculated_at,
            trend=trend,
            score_change=change,
        ))
    return items


async def get_score_detail(
    db: AsyncSession, project_id: uuid.UUID, org_id: uuid.UUID
) -> SignalScore:
    await _get_project(db, project_id, org_id)
    score = await _latest_score(db, project_id)
    if not score:
        raise LookupError("No score calculated yet")
    return score


async def get_gap_analysis(
    db: AsyncSession, project_id: uuid.UUID, org_id: uuid.UUID
) -> GapAnalysisResponse:
    """Return developer-framed gap analysis from stored score data."""
    await _get_project(db, project_id, org_id)
    score = await _latest_score(db, project_id)
    if not score:
        raise LookupError("No score calculated yet")

    gap_items: list[GapActionItem] = []
    raw_gaps = score.gaps or {}

    # Parse stored gaps into developer-friendly actions
    for dim_id, dim_data in raw_gaps.items() if isinstance(raw_gaps, dict) else []:
        if isinstance(dim_data, list):
            for gap in dim_data:
                if isinstance(gap, dict):
                    gap_items.append(GapActionItem(
                        dimension=gap.get("dimension_name", dim_id),
                        criterion=gap.get("criterion_name", ""),
                        current_score=gap.get("current_score", 0),
                        max_score=gap.get("max_points", 10),
                        action=gap.get("recommendation", "Upload supporting documentation"),
                        estimated_impact=gap.get("estimated_impact", 3),
                        priority=gap.get("priority", "medium"),
                        effort=gap.get("effort_level", "medium"),
                        document_types=gap.get("relevant_doc_types", []),
                    ))

    # Sort by estimated impact descending
    gap_items.sort(key=lambda x: x.estimated_impact, reverse=True)

    return GapAnalysisResponse(
        project_id=project_id,
        overall_score=score.overall_score,
        target_score=min(score.overall_score + 15, 100),
        gap_items=gap_items,
        generated_at=score.calculated_at,
    )


async def simulate_score(
    db: AsyncSession,
    project_id: uuid.UUID,
    org_id: uuid.UUID,
    criteria_overrides: dict[str, str],
) -> SimulateResponse:
    """Estimate score change from toggling criteria statuses."""
    await _get_project(db, project_id, org_id)
    score = await _latest_score(db, project_id)
    if not score:
        raise LookupError("No score calculated yet")

    # Simple heuristic: each "met" override adds ~3 points, "partial" adds ~1 point
    estimated_gain = 0
    dim_changes: dict[str, int] = {}
    for criterion_id, new_status in criteria_overrides.items():
        if new_status == "met":
            estimated_gain += 3
        elif new_status == "partial":
            estimated_gain += 1

    projected = min(score.overall_score + estimated_gain, 100)
    return SimulateResponse(
        current_score=score.overall_score,
        projected_score=projected,
        score_change=estimated_gain,
        dimension_changes=dim_changes,
    )


async def get_score_history(
    db: AsyncSession, project_id: uuid.UUID, org_id: uuid.UUID
) -> ScoreHistoryResponse:
    await _get_project(db, project_id, org_id)
    result = await db.execute(
        select(SignalScore)
        .where(SignalScore.project_id == project_id)
        .order_by(SignalScore.version.asc())
    )
    scores = result.scalars().all()
    history = [
        ScoreHistoryPoint(
            version=s.version,
            overall_score=s.overall_score,
            calculated_at=s.calculated_at,
            project_viability_score=s.project_viability_score,
            financial_planning_score=s.financial_planning_score,
            team_strength_score=s.team_strength_score,
            risk_assessment_score=s.risk_assessment_score,
            esg_score=s.esg_score,
            market_opportunity_score=s.market_opportunity_score,
        )
        for s in scores
    ]
    return ScoreHistoryResponse(project_id=project_id, history=history)


async def get_benchmark(
    db: AsyncSession, project_id: uuid.UUID, org_id: uuid.UUID
) -> BenchmarkResponse:
    """Return anonymised benchmark position vs same asset type."""
    project = await _get_project(db, project_id, org_id)
    score = await _latest_score(db, project_id)
    if not score:
        raise LookupError("No score calculated yet")

    # Aggregate platform scores for same project_type
    stmt = (
        select(SignalScore.overall_score)
        .join(Project, Project.id == SignalScore.project_id)
        .where(
            Project.project_type == project.project_type,
            Project.is_deleted.is_(False),
            SignalScore.is_live.is_(True),
        )
    )
    result = await db.execute(stmt)
    peer_scores = [row[0] for row in result.fetchall()]

    if len(peer_scores) < 3:
        # Not enough peers — return placeholder
        return BenchmarkResponse(
            project_id=project_id,
            your_score=score.overall_score,
            platform_median=65,
            top_quartile=80,
            percentile=50,
            peer_asset_type=project.project_type.value,
            peer_count=len(peer_scores),
        )

    peer_scores_sorted = sorted(peer_scores)
    n = len(peer_scores_sorted)
    median = peer_scores_sorted[n // 2]
    top_q = peer_scores_sorted[int(n * 0.75)]
    rank = sum(1 for s in peer_scores_sorted if s <= score.overall_score)
    percentile = int((rank / n) * 100)

    return BenchmarkResponse(
        project_id=project_id,
        your_score=score.overall_score,
        platform_median=median,
        top_quartile=top_q,
        percentile=percentile,
        peer_asset_type=project.project_type.value,
        peer_count=n,
    )
