"""Alley-side Signal Score service — project holder perspective."""
from __future__ import annotations
import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.tenant import tenant_filter
from app.models.ai import AITaskLog
from app.models.projects import Project, SignalScore
from app.modules.alley.signal_score.schemas import (
    AlleyProjectScoreSummary,
    BenchmarkResponse,
    CriterionDetail,
    DimensionBreakdown,
    DimensionDetail,
    GapAction,
    GapActionItem,
    GapAnalysisResponse,
    GenerateScoreResponse,
    ImprovementAction,
    ImprovementFactor,
    PortfolioScoreResponse,
    PortfolioStats,
    ProjectScoreDetailResponse,
    ProjectScoreListItem,
    ReadinessIndicator,
    ScoreHistoryPoint,
    ScoreHistoryResponse,
    SimulateResponse,
    TaskStatusResponse,
)

logger = structlog.get_logger()

_DIMENSION_MAP = [
    ("project_viability_score", "project_viability", "Project Viability"),
    ("financial_planning_score", "financial_planning", "Financial Planning"),
    ("team_strength_score", "team_strength", "Team Strength"),
    ("risk_assessment_score", "risk_assessment", "Risk Assessment"),
    ("esg_score", "esg", "ESG & Impact"),
    ("market_opportunity_score", "market_opportunity", "Market Opportunity"),
]


def _score_label(score_100: int) -> tuple[str, str]:
    """Return (label, color) for a 0–100 score."""
    if score_100 >= 90:
        return "Excellent", "green"
    if score_100 >= 75:
        return "Strong", "yellow"
    if score_100 >= 60:
        return "Good", "amber"
    return "Needs Review", "red"


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


# ── New portfolio overview ─────────────────────────────────────────────────────

async def get_portfolio_overview(db: AsyncSession, org_id: uuid.UUID) -> PortfolioScoreResponse:
    """Portfolio stats, scored project list, and improvement guidance."""
    stmt = select(Project).where(Project.is_deleted.is_(False))
    stmt = tenant_filter(stmt, org_id, Project)
    result = await db.execute(stmt)
    projects = result.scalars().all()

    scored_items: list[ProjectScoreListItem] = []
    all_raw_scores: list[int] = []
    all_gap_dicts: list[dict] = []

    for project in projects:
        score = await _latest_score(db, project.id)
        if score is None:
            continue
        prev = await _prev_score(db, project.id, score.version)
        trend, _ = _trend(score.overall_score, prev.overall_score if prev else None)
        label, color = _score_label(score.overall_score)

        sector = getattr(project, "sector", None)
        stage_attr = getattr(project, "stage", None)
        stage = stage_attr.value if stage_attr is not None else None

        scored_items.append(ProjectScoreListItem(
            project_id=project.id,
            project_name=project.name,
            sector=sector,
            stage=stage,
            score=round(score.overall_score / 10, 1),
            score_label=label,
            score_label_color=color,
            status="Ready" if score.overall_score >= 70 else "Needs Review",
            calculated_at=score.calculated_at,
            trend=trend,
        ))
        all_raw_scores.append(score.overall_score)

        raw_gaps = score.gaps or {}
        for _, dim_data in (raw_gaps.items() if isinstance(raw_gaps, dict) else []):
            if isinstance(dim_data, list):
                for gap in dim_data:
                    if isinstance(gap, dict):
                        all_gap_dicts.append(gap)

    avg_score = round(sum(all_raw_scores) / len(all_raw_scores) / 10, 1) if all_raw_scores else 0.0
    investment_ready_count = sum(1 for s in all_raw_scores if s >= 70)

    # Improvement factors: lowest-scoring dimensions across the portfolio
    dim_totals: dict[str, list[int]] = {dim_id: [] for _, dim_id, _ in _DIMENSION_MAP}
    for project in projects:
        score = await _latest_score(db, project.id)
        if score is None:
            continue
        for db_key, dim_id, _ in _DIMENSION_MAP:
            dim_totals[dim_id].append(getattr(score, db_key, 0))

    improvement_factors = sorted(
        [
            ImprovementFactor(
                dimension=dim_id,
                avg_score=round(sum(vals) / len(vals) / 10, 1) if vals else 0.0,
            )
            for _, dim_id, _ in _DIMENSION_MAP
            for vals in [dim_totals[dim_id]]
        ],
        key=lambda f: f.avg_score,
    )

    # Top improvement actions from gap data
    top_gaps = sorted(all_gap_dicts, key=lambda g: g.get("estimated_impact", 0), reverse=True)[:6]
    improvement_actions = [
        ImprovementAction(
            action=g.get("recommendation", "Upload supporting documentation"),
            dimension=g.get("dimension_name", ""),
            priority=g.get("priority", "medium"),
            estimated_impact=round(g.get("estimated_impact", 3) / 10, 1),
        )
        for g in top_gaps
    ]

    return PortfolioScoreResponse(
        stats=PortfolioStats(
            avg_score=avg_score,
            total_projects=len(scored_items),
            investment_ready_count=investment_ready_count,
        ),
        projects=scored_items,
        improvement_factors=improvement_factors,
        improvement_actions=improvement_actions,
    )


# ── New project detail ─────────────────────────────────────────────────────────

async def get_project_detail(
    db: AsyncSession, project_id: uuid.UUID, org_id: uuid.UUID
) -> ProjectScoreDetailResponse:
    """Consolidated project detail: score, dimensions, indicators, breakdowns, history."""
    project = await _get_project(db, project_id, org_id)
    score = await _latest_score(db, project_id)
    if not score:
        raise LookupError("No score calculated yet")

    label, color = _score_label(score.overall_score)

    dimensions = [
        DimensionDetail(
            id=dim_id,
            label=dim_label,
            score=getattr(score, db_key, 0),
        )
        for db_key, dim_id, dim_label in _DIMENSION_MAP
    ]

    # Readiness indicators from score_factors JSONB
    indicators: list[ReadinessIndicator] = []
    score_factors = score.score_factors if hasattr(score, "score_factors") else {}
    if isinstance(score_factors, dict) and score_factors:
        for key, val in score_factors.items():
            indicators.append(ReadinessIndicator(
                label=key.replace("_", " ").title(),
                met=bool(val),
            ))
    else:
        # Synthetic fallback indicators from dimension scores
        indicators = [
            ReadinessIndicator(label="Business plan submitted", met=score.overall_score >= 40),
            ReadinessIndicator(label="Financial projections available", met=score.financial_planning_score >= 50),
            ReadinessIndicator(label="Team profiles complete", met=score.team_strength_score >= 50),
            ReadinessIndicator(label="Risk assessment completed", met=score.risk_assessment_score >= 50),
            ReadinessIndicator(label="ESG framework in place", met=score.esg_score >= 50),
            ReadinessIndicator(label="Investment ready (≥7.0)", met=score.overall_score >= 70),
        ]

    # Criteria breakdown from scoring_details JSONB
    criteria_breakdown: list[DimensionBreakdown] = []
    scoring_details = score.scoring_details if hasattr(score, "scoring_details") else {}
    if isinstance(scoring_details, dict):
        for dim_id, dim_data in scoring_details.items():
            if isinstance(dim_data, dict) and "criteria" in dim_data:
                criteria = [
                    CriterionDetail(
                        id=c.get("id", ""),
                        name=c.get("name", ""),
                        status=c.get("status", "not_met"),
                        points_earned=c.get("points_earned", 0),
                        points_max=c.get("points_max", 10),
                        evidence_note=c.get("evidence_note"),
                    )
                    for c in dim_data["criteria"]
                    if isinstance(c, dict)
                ]
                criteria_breakdown.append(DimensionBreakdown(
                    dimension_id=dim_id,
                    dimension_name=dim_data.get("name", dim_id),
                    score=dim_data.get("score", 0),
                    criteria=criteria,
                ))

    # Gap analysis
    gap_actions: list[GapAction] = []
    raw_gaps = score.gaps or {}
    for dim_id, dim_data in (raw_gaps.items() if isinstance(raw_gaps, dict) else []):
        if isinstance(dim_data, list):
            for gap in dim_data:
                if isinstance(gap, dict):
                    gap_actions.append(GapAction(
                        dimension=gap.get("dimension_name", dim_id),
                        action=gap.get("recommendation", "Upload supporting documentation"),
                        effort=gap.get("effort_level", "medium"),
                        timeline=gap.get("timeline", "2–4 weeks"),
                        estimated_impact=round(gap.get("estimated_impact", 3) / 10, 1),
                    ))
    gap_actions.sort(key=lambda x: x.estimated_impact, reverse=True)

    # Score history
    history_result = await db.execute(
        select(SignalScore)
        .where(SignalScore.project_id == project_id)
        .order_by(SignalScore.version.asc())
    )
    all_versions = history_result.scalars().all()
    score_history = [
        ScoreHistoryPoint(
            date=s.calculated_at.strftime("%Y-%m-%d"),
            score=round(s.overall_score / 10, 1),
        )
        for s in all_versions
    ]

    return ProjectScoreDetailResponse(
        project_id=project_id,
        project_name=project.name,
        score=round(score.overall_score / 10, 1),
        score_label=label,
        score_label_color=color,
        dimensions=dimensions,
        readiness_indicators=indicators,
        criteria_breakdown=criteria_breakdown,
        gap_analysis=gap_actions,
        score_history=score_history,
    )


# ── Generate / Task Status ─────────────────────────────────────────────────────

async def trigger_generate(
    db: AsyncSession,
    org_id: uuid.UUID,
    project_id: uuid.UUID,
) -> GenerateScoreResponse:
    """Create an AITaskLog entry and dispatch Celery score-generation task."""
    from app.models.enums import AIAgentType, AITaskStatus

    task_log = AITaskLog(
        org_id=org_id,
        agent_type=AIAgentType.SIGNAL_SCORE,
        entity_type="project",
        entity_id=project_id,
        status=AITaskStatus.PENDING,
        input_data={"project_id": str(project_id)},
    )
    db.add(task_log)
    await db.commit()
    await db.refresh(task_log)

    from app.modules.alley.signal_score.tasks import run_signal_score_generation
    run_signal_score_generation.delay(str(task_log.id), str(org_id), str(project_id))

    return GenerateScoreResponse(task_id=str(task_log.id))


async def get_task_status(
    db: AsyncSession, task_id: uuid.UUID, org_id: uuid.UUID
) -> TaskStatusResponse:
    """Poll AITaskLog for task status."""
    result = await db.execute(
        select(AITaskLog).where(
            AITaskLog.id == task_id,
            AITaskLog.org_id == org_id,
        )
    )
    log = result.scalar_one_or_none()
    if not log:
        raise LookupError(f"Task {task_id} not found")

    status_map = {
        "pending": "pending",
        "running": "running",
        "completed": "completed",
        "failed": "failed",
    }
    raw_status = log.status.value if hasattr(log.status, "value") else str(log.status)
    return TaskStatusResponse(
        task_id=str(task_id),
        status=status_map.get(raw_status.lower(), raw_status),
        progress_message=log.error_message if raw_status.lower() == "failed" else None,
        result=log.output_data if raw_status.lower() == "completed" else None,
    )


# ── Legacy service functions (kept for backward-compat endpoints) ───────────────

async def list_scores(db: AsyncSession, org_id: uuid.UUID) -> list[AlleyProjectScoreSummary]:
    stmt = select(Project).where(Project.is_deleted.is_(False))
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


async def get_gap_analysis(
    db: AsyncSession, project_id: uuid.UUID, org_id: uuid.UUID
) -> GapAnalysisResponse:
    await _get_project(db, project_id, org_id)
    score = await _latest_score(db, project_id)
    if not score:
        raise LookupError("No score calculated yet")

    gap_items: list[GapActionItem] = []
    raw_gaps = score.gaps or {}
    for dim_id, dim_data in (raw_gaps.items() if isinstance(raw_gaps, dict) else []):
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
    await _get_project(db, project_id, org_id)
    score = await _latest_score(db, project_id)
    if not score:
        raise LookupError("No score calculated yet")

    estimated_gain = sum(
        3 if v == "met" else 1 if v == "partial" else 0
        for v in criteria_overrides.values()
    )
    projected = min(score.overall_score + estimated_gain, 100)
    return SimulateResponse(
        current_score=score.overall_score,
        projected_score=projected,
        score_change=estimated_gain,
        dimension_changes={},
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
            date=s.calculated_at.strftime("%Y-%m-%d"),
            score=round(s.overall_score / 10, 1),
        )
        for s in scores
    ]
    return ScoreHistoryResponse(project_id=project_id, history=history)


async def get_benchmark(
    db: AsyncSession, project_id: uuid.UUID, org_id: uuid.UUID
) -> BenchmarkResponse:
    project = await _get_project(db, project_id, org_id)
    score = await _latest_score(db, project_id)
    if not score:
        raise LookupError("No score calculated yet")

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
