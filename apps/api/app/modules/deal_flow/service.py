"""Deal Flow Analytics — business logic."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.deal_flow import DealStageTransition
from app.modules.deal_flow.schemas import (
    AvgTimeInStage,
    ConversionStep,
    FunnelResponse,
    PipelineValueResponse,
    StageCount,
    VelocityResponse,
)

DEAL_STAGES_ORDER = [
    "discovery",
    "screening",
    "preliminary_dd",
    "full_dd",
    "negotiation",
    "term_sheet",
    "closing",
    "closed",
]


async def record_transition(
    db: AsyncSession,
    org_id: uuid.UUID,
    project_id: uuid.UUID,
    to_stage: str,
    from_stage: str | None = None,
    reason: str | None = None,
    investor_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    metadata: dict | None = None,
) -> DealStageTransition:
    """Append a stage transition event."""
    t = DealStageTransition(
        org_id=org_id,
        project_id=project_id,
        investor_id=investor_id,
        from_stage=from_stage,
        to_stage=to_stage,
        reason=reason,
        metadata_=metadata or {},
        transitioned_by=user_id,
    )
    db.add(t)
    await db.commit()
    return t


async def get_funnel(
    db: AsyncSession,
    org_id: uuid.UUID,
    period_days: int = 90,
    investor_id: uuid.UUID | None = None,
) -> FunnelResponse:
    """Calculate funnel metrics for the period."""
    since = datetime.utcnow() - timedelta(days=period_days)

    filters = [
        DealStageTransition.org_id == org_id,
        DealStageTransition.created_at >= since,
    ]
    if investor_id:
        filters.append(DealStageTransition.investor_id == investor_id)

    result = await db.execute(select(DealStageTransition).where(*filters))
    transitions = result.scalars().all()

    # Stage counts
    stage_counts: dict[str, int] = {}
    for t in transitions:
        stage_counts[t.to_stage] = stage_counts.get(t.to_stage, 0) + 1

    # Build StageCount list in order
    stage_count_list = [
        StageCount(stage=s, count=stage_counts.get(s, 0), deal_value=None)
        for s in DEAL_STAGES_ORDER + ["passed"]
    ]

    # Conversions
    conversions = []
    for i in range(len(DEAL_STAGES_ORDER) - 1):
        f, t_stage = DEAL_STAGES_ORDER[i], DEAL_STAGES_ORDER[i + 1]
        fc = stage_counts.get(f, 0)
        tc = stage_counts.get(t_stage, 0)
        conversions.append(
            ConversionStep(
                from_stage=f,
                to_stage=t_stage,
                from_count=fc,
                to_count=tc,
                conversion_rate=round(tc / fc, 3) if fc > 0 else 0.0,
            )
        )

    # Avg time in stage (using consecutive transitions for same project)
    avg_times = await _calculate_avg_times(db, org_id, since, investor_id)

    # Drop-off reasons
    reasons: dict[str, int] = {}
    for t in transitions:
        if t.to_stage == "passed" and t.reason:
            reasons[t.reason] = reasons.get(t.reason, 0) + 1

    return FunnelResponse(
        period_days=period_days,
        stage_counts=stage_count_list,
        conversions=conversions,
        avg_time_in_stage=avg_times,
        drop_off_reasons=reasons,
        total_entered=stage_counts.get("discovery", 0),
        total_closed=stage_counts.get("closed", 0),
        overall_conversion_rate=round(
            stage_counts.get("closed", 0) / max(stage_counts.get("discovery", 1), 1),
            3,
        ),
        generated_at=datetime.utcnow(),
    )


async def _calculate_avg_times(
    db: AsyncSession,
    org_id: uuid.UUID,
    since: datetime,
    investor_id: uuid.UUID | None,
) -> list[AvgTimeInStage]:
    """Calculate average days between stage transitions."""
    filters = [
        DealStageTransition.org_id == org_id,
        DealStageTransition.created_at >= since,
    ]
    if investor_id:
        filters.append(DealStageTransition.investor_id == investor_id)

    result = await db.execute(
        select(DealStageTransition)
        .where(*filters)
        .order_by(DealStageTransition.project_id, DealStageTransition.created_at)
    )
    transitions = result.scalars().all()

    # Group by project
    by_project: dict[str, list[DealStageTransition]] = {}
    for t in transitions:
        key = str(t.project_id)
        by_project.setdefault(key, []).append(t)

    # Calculate time per stage
    stage_times: dict[str, list[float]] = {s: [] for s in DEAL_STAGES_ORDER}
    for proj_transitions in by_project.values():
        for i in range(len(proj_transitions) - 1):
            curr = proj_transitions[i]
            nxt = proj_transitions[i + 1]
            days = (nxt.created_at - curr.created_at).total_seconds() / 86400
            if curr.to_stage in stage_times:
                stage_times[curr.to_stage].append(days)

    return [
        AvgTimeInStage(
            stage=s,
            avg_days=round(sum(times) / len(times), 1) if times else None,
        )
        for s, times in stage_times.items()
    ]


async def get_pipeline_value(
    db: AsyncSession,
    org_id: uuid.UUID,
    investor_id: uuid.UUID | None = None,
) -> PipelineValueResponse:
    """Sum project investment required by current stage."""
    from app.models.projects import Project

    # Get latest stage per project
    subq = (
        select(
            DealStageTransition.project_id,
            func.max(DealStageTransition.created_at).label("latest"),
        )
        .where(DealStageTransition.org_id == org_id)
        .group_by(DealStageTransition.project_id)
        .subquery()
    )

    latest_transitions_result = await db.execute(
        select(DealStageTransition).join(
            subq,
            and_(
                DealStageTransition.project_id == subq.c.project_id,
                DealStageTransition.created_at == subq.c.latest,
            ),
        )
    )
    transitions = latest_transitions_result.scalars().all()

    # Sum by stage
    by_stage: dict[str, float] = {s: 0.0 for s in DEAL_STAGES_ORDER}
    project_ids = [t.project_id for t in transitions]

    if project_ids:
        projects_result = await db.execute(
            select(Project).where(Project.id.in_(project_ids))
        )
        project_map = {p.id: p for p in projects_result.scalars().all()}
        for t in transitions:
            proj = project_map.get(t.project_id)
            if proj and proj.total_investment_required and t.to_stage in by_stage:
                by_stage[t.to_stage] += float(proj.total_investment_required)

    return PipelineValueResponse(by_stage=by_stage, total=sum(by_stage.values()))


async def get_velocity(
    db: AsyncSession,
    org_id: uuid.UUID,
    investor_id: uuid.UUID | None = None,
) -> VelocityResponse:
    """Return deal velocity metrics."""
    since = datetime.utcnow() - timedelta(days=365)
    avg_times = await _calculate_avg_times(db, org_id, since, investor_id)

    # Avg days to close = sum of all stage avg times
    total_days = sum(
        at.avg_days for at in avg_times if at.avg_days is not None
    )
    avg_days_to_close = round(total_days, 1) if total_days > 0 else None

    # Monthly trend placeholder — requires heavier aggregation; return empty list
    trend: list[dict] = []

    return VelocityResponse(
        avg_days_to_close=avg_days_to_close,
        by_stage=avg_times,
        trend=trend,
    )
