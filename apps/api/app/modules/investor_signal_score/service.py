"""Investor Signal Score service."""

import dataclasses
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.advisory import InvestorSignalScore
from app.models.projects import Project, SignalScore
from app.modules.investor_signal_score.engine import (
    DIMENSION_WEIGHTS,
    InvestorSignalScoreEngine,
)
from app.modules.investor_signal_score.schemas import (
    BenchmarkResponse,
    CriterionResult,
    DealAlignmentResponse,
    DimensionDetailResponse,
    DimensionScore,
    ImprovementAction,
    InvestorSignalScoreResponse,
    ScoreFactorItem,
    ScoreHistoryItem,
    TopMatchItem,
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _build_dimension(dim_data: dict) -> DimensionScore:
    return DimensionScore(
        score=float(dim_data.get("score", 0)),
        weight=float(dim_data.get("weight", 0)),
        details=dim_data.get("details"),
        gaps=dim_data.get("gaps", []),
        recommendations=dim_data.get("recommendations", []),
    )


def _orm_to_response(record: InvestorSignalScore, scored: dict) -> InvestorSignalScoreResponse:
    """Map ORM record + scored output dict to response schema."""
    dims = scored.get("dimensions", {})
    return InvestorSignalScoreResponse(
        id=record.id,
        org_id=record.org_id,
        overall_score=float(record.overall_score),
        financial_capacity=_build_dimension(dims.get("financial_capacity", {})),
        risk_management=_build_dimension(dims.get("risk_management", {})),
        investment_strategy=_build_dimension(dims.get("investment_strategy", {})),
        team_experience=_build_dimension(dims.get("team_experience", {})),
        esg_commitment=_build_dimension(dims.get("esg_commitment", {})),
        platform_readiness=_build_dimension(dims.get("platform_readiness", {})),
        score_change=(
            float(record.score_change) if record.score_change is not None else None
        ),
        previous_score=(
            float(record.previous_score) if record.previous_score is not None else None
        ),
        calculated_at=record.calculated_at,
    )


def _extract_stored_dimensions(record: InvestorSignalScore) -> dict:
    """Re-hydrate dimension data stored in the record's JSONB fields."""
    return {
        key: {
            "score": float(getattr(record, f"{key}_score")),
            "weight": DIMENSION_WEIGHTS[key],
            "details": getattr(record, f"{key}_details"),
            "gaps": (record.gaps or {}).get(key, []),
            "recommendations": (record.recommendations or {}).get(key, []),
        }
        for key in DIMENSION_WEIGHTS
    }


# ── Service functions ─────────────────────────────────────────────────────────


async def calculate_score(
    db: AsyncSession,
    org_id: uuid.UUID,
) -> InvestorSignalScoreResponse:
    """Calculate a new InvestorSignalScore using the multi-source engine."""
    engine = InvestorSignalScoreEngine(db, org_id)
    result = await engine.calculate()

    # Load previous score to compute change
    prev_stmt = (
        select(InvestorSignalScore)
        .where(InvestorSignalScore.org_id == org_id)
        .order_by(InvestorSignalScore.calculated_at.desc())
        .limit(1)
    )
    prev_result = await db.execute(prev_stmt)
    previous_record = prev_result.scalar_one_or_none()

    previous_score: Decimal | None = None
    score_change: Decimal | None = None
    if previous_record is not None:
        previous_score = previous_record.overall_score
        score_change = Decimal(str(result.overall_score)) - previous_score

    dims = result.dimensions
    now = datetime.now(timezone.utc)

    def _dim_details(key: str) -> dict:
        d = dims[key]
        details = dict(d.details)
        details["criteria"] = [dataclasses.asdict(c) for c in d.criteria]
        return details

    record = InvestorSignalScore(
        org_id=org_id,
        overall_score=Decimal(str(result.overall_score)),
        financial_capacity_score=Decimal(str(dims["financial_capacity"].score)),
        financial_capacity_details=_dim_details("financial_capacity"),
        risk_management_score=Decimal(str(dims["risk_management"].score)),
        risk_management_details=_dim_details("risk_management"),
        investment_strategy_score=Decimal(str(dims["investment_strategy"].score)),
        investment_strategy_details=_dim_details("investment_strategy"),
        team_experience_score=Decimal(str(dims["team_experience"].score)),
        team_experience_details=_dim_details("team_experience"),
        esg_commitment_score=Decimal(str(dims["esg_commitment"].score)),
        esg_commitment_details=_dim_details("esg_commitment"),
        platform_readiness_score=Decimal(str(dims["platform_readiness"].score)),
        platform_readiness_details=_dim_details("platform_readiness"),
        gaps={k: v.gaps for k, v in dims.items()},
        recommendations={k: v.recommendations for k, v in dims.items()},
        score_factors={
            "dimension_weights": DIMENSION_WEIGHTS,
            "improvement_actions": [dataclasses.asdict(a) for a in result.improvement_actions],
            "factors": [dataclasses.asdict(f) for f in result.score_factors],
        },
        data_sources=result.data_sources,
        calculated_at=now,
        previous_score=previous_score,
        score_change=score_change,
    )

    db.add(record)
    await db.flush()
    await db.refresh(record)

    return _orm_to_response(record, {"dimensions": _extract_stored_dimensions(record)})


async def get_latest_score(
    db: AsyncSession,
    org_id: uuid.UUID,
) -> InvestorSignalScoreResponse | None:
    """Get the most recent InvestorSignalScore for the org, or None."""
    stmt = (
        select(InvestorSignalScore)
        .where(InvestorSignalScore.org_id == org_id)
        .order_by(InvestorSignalScore.calculated_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()
    if record is None:
        return None
    return _orm_to_response(record, {"dimensions": _extract_stored_dimensions(record)})


async def get_score_history(
    db: AsyncSession,
    org_id: uuid.UUID,
    limit: int = 12,
) -> list[ScoreHistoryItem]:
    """Return the last `limit` score records for sparkline/trend display."""
    stmt = (
        select(InvestorSignalScore)
        .where(InvestorSignalScore.org_id == org_id)
        .order_by(InvestorSignalScore.calculated_at.asc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    records = result.scalars().all()
    return [
        ScoreHistoryItem(
            id=r.id,
            overall_score=float(r.overall_score),
            score_change=float(r.score_change) if r.score_change is not None else None,
            calculated_at=r.calculated_at,
        )
        for r in records
    ]


async def get_improvement_plan(
    db: AsyncSession,
    org_id: uuid.UUID,
) -> list[ImprovementAction]:
    """Return improvement actions from the latest score's stored data."""
    stmt = (
        select(InvestorSignalScore)
        .where(InvestorSignalScore.org_id == org_id)
        .order_by(InvestorSignalScore.calculated_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()
    if record is None:
        return []

    raw_actions = (record.score_factors or {}).get("improvement_actions", [])
    return [ImprovementAction(**a) for a in raw_actions]


async def get_score_factors(
    db: AsyncSession,
    org_id: uuid.UUID,
) -> list[ScoreFactorItem]:
    """Return positive/negative score factors from the latest score."""
    stmt = (
        select(InvestorSignalScore)
        .where(InvestorSignalScore.org_id == org_id)
        .order_by(InvestorSignalScore.calculated_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()
    if record is None:
        return []

    raw_factors = (record.score_factors or {}).get("factors", [])
    return [ScoreFactorItem(**f) for f in raw_factors]


async def get_dimension_details(
    db: AsyncSession,
    org_id: uuid.UUID,
    dimension: str,
) -> DimensionDetailResponse | None:
    """Return full dimension details including per-criterion breakdown."""
    if dimension not in DIMENSION_WEIGHTS:
        return None

    stmt = (
        select(InvestorSignalScore)
        .where(InvestorSignalScore.org_id == org_id)
        .order_by(InvestorSignalScore.calculated_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()
    if record is None:
        return None

    score_val = float(getattr(record, f"{dimension}_score", 0))
    raw_details = getattr(record, f"{dimension}_details", {}) or {}
    gaps = (record.gaps or {}).get(dimension, [])
    recs = (record.recommendations or {}).get(dimension, [])

    raw_criteria = raw_details.get("criteria", [])
    criteria = [CriterionResult(**c) for c in raw_criteria]
    # details without criteria list (already returned separately)
    details = {k: v for k, v in raw_details.items() if k != "criteria"}

    return DimensionDetailResponse(
        score=score_val,
        weight=DIMENSION_WEIGHTS.get(dimension, 0.0),
        gaps=gaps,
        recommendations=recs,
        details=details,
        criteria=criteria,
    )


async def get_benchmark(
    db: AsyncSession,
    org_id: uuid.UUID,
) -> BenchmarkResponse:
    """Compare this org's score against the platform distribution."""
    # This org's latest score
    my_stmt = (
        select(InvestorSignalScore)
        .where(InvestorSignalScore.org_id == org_id)
        .order_by(InvestorSignalScore.calculated_at.desc())
        .limit(1)
    )
    my_result = await db.execute(my_stmt)
    my_record = my_result.scalar_one_or_none()
    my_score = float(my_record.overall_score) if my_record else 0.0

    # All orgs' latest scores (deduplication in Python — platform is small)
    all_stmt = select(InvestorSignalScore).order_by(
        InvestorSignalScore.org_id,
        InvestorSignalScore.calculated_at.desc(),
    )
    all_result = await db.execute(all_stmt)
    all_records = all_result.scalars().all()

    seen: set[uuid.UUID] = set()
    all_scores: list[float] = []
    for r in all_records:
        if r.org_id not in seen:
            seen.add(r.org_id)
            all_scores.append(float(r.overall_score))

    if not all_scores:
        return BenchmarkResponse(
            your_score=round(my_score, 1),
            platform_average=round(my_score, 1),
            top_quartile=round(my_score, 1),
            percentile=50,
        )

    avg = sum(all_scores) / len(all_scores)
    sorted_scores = sorted(all_scores)
    p75_idx = max(0, int(len(sorted_scores) * 0.75) - 1)
    p75 = sorted_scores[p75_idx]

    below = sum(1 for s in sorted_scores if s < my_score)
    percentile = int(round(below / len(sorted_scores) * 100))

    return BenchmarkResponse(
        your_score=round(my_score, 1),
        platform_average=round(avg, 1),
        top_quartile=round(p75, 1),
        percentile=percentile,
    )


async def get_top_matches(
    db: AsyncSession,
    org_id: uuid.UUID,
    limit: int = 5,
) -> list[TopMatchItem]:
    """Return top deal alignment matches using the engine."""
    from app.models.matching import MatchResult

    match_stmt = (
        select(MatchResult)
        .where(
            MatchResult.investor_org_id == org_id,
            MatchResult.is_deleted.is_(False),
        )
        .order_by(MatchResult.match_score.desc())
        .limit(limit * 3)
    )
    match_result = await db.execute(match_stmt)
    matches = list(match_result.scalars().all())

    if not matches:
        return []

    # Unique project IDs
    seen_project_ids: list[uuid.UUID] = []
    seen_set: set[uuid.UUID] = set()
    for m in matches:
        if m.project_id not in seen_set:
            seen_set.add(m.project_id)
            seen_project_ids.append(m.project_id)
        if len(seen_project_ids) >= limit:
            break

    # Load projects
    proj_stmt = select(Project).where(
        Project.id.in_(seen_project_ids),
        Project.is_deleted.is_(False),
    )
    proj_result = await db.execute(proj_stmt)
    projects = {p.id: p for p in proj_result.scalars().all()}

    engine = InvestorSignalScoreEngine(db, org_id)
    items: list[TopMatchItem] = []
    for pid in seen_project_ids:
        if pid not in projects:
            continue
        project = projects[pid]
        try:
            alignment = await engine.calculate_deal_alignment(pid)
            items.append(
                TopMatchItem(
                    project_id=pid,
                    project_name=alignment["project_name"],
                    alignment_score=alignment["alignment_score"],
                    recommendation=alignment["recommendation"],
                    project_type=str(getattr(project, "project_type", "") or ""),
                    geography_country=getattr(project, "geography_country", None),
                )
            )
        except Exception:
            continue

    return sorted(items, key=lambda x: x.alignment_score, reverse=True)


async def get_deal_alignment(
    db: AsyncSession,
    org_id: uuid.UUID,
    project_id: uuid.UUID,
) -> DealAlignmentResponse:
    """
    Compute alignment between the investor's signal score and a given project.

    Uses the engine's calculate_deal_alignment for richer factor analysis.
    Returns a 0-100 alignment score.
    """
    # Load investor's latest score for the investor_score field
    investor_record_stmt = (
        select(InvestorSignalScore)
        .where(InvestorSignalScore.org_id == org_id)
        .order_by(InvestorSignalScore.calculated_at.desc())
        .limit(1)
    )
    investor_result = await db.execute(investor_record_stmt)
    investor_record = investor_result.scalar_one_or_none()
    investor_overall = float(investor_record.overall_score) if investor_record else 50.0

    # Use engine for alignment calculation
    engine = InvestorSignalScoreEngine(db, org_id)
    alignment = await engine.calculate_deal_alignment(project_id)

    return DealAlignmentResponse(
        project_id=project_id,
        investor_score=investor_overall,
        alignment_score=alignment["alignment_score"],
        alignment_factors=[
            {
                "dimension": f["name"],
                "score": f["score"],
                "impact": "high" if f["score"] >= 80 else ("medium" if f["score"] >= 50 else "low"),
            }
            for f in alignment["factors"]
        ],
        recommendation=alignment["recommendation"],
    )
