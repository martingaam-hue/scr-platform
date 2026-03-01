"""Signal Score API router."""

import uuid
from datetime import datetime
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_permission
from app.core.database import get_db, get_readonly_session
from app.services.ai_budget import enforce_ai_budget
from app.modules.signal_score import service
from app.services.response_cache import cache_key, get_cached, set_cached
from app.modules.signal_score.criteria import DIMENSIONS
from app.modules.signal_score.schemas import (
    BatchScoreItem,
    BatchScoreRequest,
    BatchScoreResponse,
    CalculateAcceptedResponse,
    CriterionScoreResponse,
    DimensionScoreResponse,
    GapItem,
    GapsResponse,
    ImprovementAction,
    ImprovementGuidanceResponse,
    LiveScoreFactor,
    LiveScoreResponse,
    ScoreHistoryItem,
    ScoreHistoryResponse,
    SignalScoreDetailResponse,
    StrengthItem,
    StrengthsResponse,
    TaskStatusResponse,
)
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()

router = APIRouter(prefix="/signal-score", tags=["signal-score"])


# ── Task status (fixed path before parameterised) ──────────────────────────


@router.get("/task/{task_log_id}", summary="Get calculation task status", response_model=TaskStatusResponse)
async def get_task_status(
    task_log_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check status of a signal score calculation task."""
    task_log = await service.get_task_status(db, task_log_id, current_user.org_id)
    if not task_log:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskStatusResponse(
        id=task_log.id,
        status=task_log.status.value,
        error_message=task_log.error_message,
    )


# ── Batch scoring ────────────────────────────────────────────────────────────


@router.post(
    "/batch",
    summary="Batch score multiple projects",
    response_model=BatchScoreResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def batch_score_projects(
    body: BatchScoreRequest,
    current_user: CurrentUser = Depends(require_permission("run_analysis", "analysis")),
    db: AsyncSession = Depends(get_db),
):
    """Queue signal score computation for multiple projects at once.

    Accepts up to 50 project IDs. Dispatches a separate Celery task for each
    project and returns the individual task_log_ids for status polling.
    Projects that cannot be found (or do not belong to the org) are reported
    in the ``errors`` list but do not prevent the rest from being queued.
    """
    items: list[BatchScoreItem] = []
    errors: list[dict] = []

    for project_id in body.project_ids:
        try:
            task_log = await service.trigger_calculation(
                db, project_id, current_user.org_id, current_user.user_id
            )
            await db.flush()
            items.append(
                BatchScoreItem(
                    project_id=project_id,
                    task_log_id=task_log.id,
                    status="pending",
                )
            )
        except LookupError as exc:
            errors.append({"project_id": str(project_id), "error": str(exc)})
        except Exception as exc:
            logger.warning(
                "batch_score.project_failed",
                project_id=str(project_id),
                error=str(exc),
            )
            errors.append({"project_id": str(project_id), "error": str(exc)})

    if items:
        await db.commit()

    logger.info(
        "batch_score_queued",
        org_id=str(current_user.org_id),
        queued=len(items),
        failed=len(errors),
    )
    return BatchScoreResponse(
        queued=len(items),
        failed=len(errors),
        items=items,
        errors=errors,
    )


# ── Calculate ───────────────────────────────────────────────────────────────


@router.post(
    "/calculate/{project_id}",
    summary="Trigger signal score calculation",
    response_model=CalculateAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def calculate_score(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("run_analysis", "analysis")),
    db: AsyncSession = Depends(get_db),
    _budget: None = Depends(enforce_ai_budget),
):
    """Trigger a new signal score calculation."""
    try:
        task_log = await service.trigger_calculation(
            db, project_id, current_user.org_id, current_user.user_id
        )
        await db.commit()
    except LookupError:
        raise HTTPException(status_code=404, detail="Project not found")

    return CalculateAcceptedResponse(
        task_log_id=task_log.id,
        status="pending",
        message="Signal score calculation started",
    )


@router.post(
    "/{project_id}/recalculate",
    summary="Force recalculate signal score",
    response_model=CalculateAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def recalculate_score(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("run_analysis", "analysis")),
    db: AsyncSession = Depends(get_db),
):
    """Force recalculation of signal score (creates new version)."""
    try:
        task_log = await service.trigger_calculation(
            db, project_id, current_user.org_id, current_user.user_id
        )
        await db.commit()
    except LookupError:
        raise HTTPException(status_code=404, detail="Project not found")

    return CalculateAcceptedResponse(
        task_log_id=task_log.id,
        status="pending",
        message="Signal score recalculation started",
    )


# ── Live Score (synchronous, no documents) ───────────────────────────────────


@router.post("/{project_id}/live", summary="Get live metadata score", response_model=LiveScoreResponse)
async def live_score(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    """Quick synchronous score based on project metadata completeness only.

    Returns immediately without AI evaluation or document analysis.
    Use /calculate for a full AI-powered signal score.
    """
    try:
        result = await service.get_live_score(
            db, project_id, current_user.org_id
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="Project not found")

    return LiveScoreResponse(
        overall_score=result["overall_score"],
        factors=[LiveScoreFactor(**f) for f in result["factors"]],
        guidance=result["guidance"],
    )


# ── Read endpoints ──────────────────────────────────────────────────────────


@router.get("/{project_id}", summary="Get latest signal score", response_model=SignalScoreDetailResponse)
async def get_latest_score(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    """Get latest signal score with full dimension breakdown."""
    ck = cache_key("signal_score", str(current_user.org_id), str(project_id))
    cached = await get_cached(ck)
    if cached is not None:
        return cached

    try:
        score = await service.get_latest_score(
            db, project_id, current_user.org_id
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="Project not found")

    if not score:
        raise HTTPException(status_code=404, detail="No signal score found")

    result = _build_detail_response(score)
    await set_cached(ck, jsonable_encoder(result), ttl=600)
    return result


@router.get("/{project_id}/details", summary="Get score dimension breakdown", response_model=SignalScoreDetailResponse)
async def get_score_details(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed scoring breakdown with criteria and AI assessments."""
    try:
        score = await service.get_latest_score(
            db, project_id, current_user.org_id
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="Project not found")

    if not score:
        raise HTTPException(status_code=404, detail="No signal score found")

    return _build_detail_response(score)


@router.get("/{project_id}/gaps", summary="Get gap analysis", response_model=GapsResponse)
async def get_gaps(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    """Get gap analysis with prioritized recommendations."""
    try:
        score = await service.get_latest_score(
            db, project_id, current_user.org_id
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="Project not found")

    if not score:
        raise HTTPException(status_code=404, detail="No signal score found")

    gaps_data = score.gaps or {}
    items = [GapItem(**item) for item in gaps_data.get("items", [])]
    return GapsResponse(items=items, total=len(items))


@router.get("/{project_id}/strengths", summary="Get score strengths", response_model=StrengthsResponse)
async def get_strengths(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    """Get strengths identified by the scoring engine."""
    try:
        score = await service.get_latest_score(
            db, project_id, current_user.org_id
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="Project not found")

    if not score:
        raise HTTPException(status_code=404, detail="No signal score found")

    strengths_data = score.strengths or {}
    items = [StrengthItem(**item) for item in strengths_data.get("items", [])]
    return StrengthsResponse(items=items, total=len(items))


@router.get("/{project_id}/improvement-guidance", summary="Get improvement guidance", response_model=ImprovementGuidanceResponse)
async def get_improvement_guidance(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    """Get structured improvement guidance from the latest signal score."""
    try:
        score = await service.get_latest_score(
            db, project_id, current_user.org_id
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="Project not found")

    if not score:
        raise HTTPException(status_code=404, detail="No signal score found")

    guidance = score.improvement_guidance or {}
    return ImprovementGuidanceResponse(
        quick_wins=guidance.get("quick_wins", []),
        focus_area=guidance.get("focus_area"),
        high_priority_count=guidance.get("high_priority_count", 0),
        medium_priority_count=guidance.get("medium_priority_count", 0),
        estimated_max_gain=guidance.get("estimated_max_gain", 0),
        top_actions=[
            ImprovementAction(**action)
            for action in guidance.get("top_actions", [])
        ],
        based_on_version=score.version,
    )


@router.get("/{project_id}/history", summary="Get score history", response_model=ScoreHistoryResponse)
async def get_score_history(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_readonly_session),
):
    """Get signal score history across all versions."""
    try:
        scores = await service.get_score_history(
            db, project_id, current_user.org_id
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="Project not found")

    items = [
        ScoreHistoryItem(
            version=s.version,
            overall_score=s.overall_score,
            project_viability_score=s.project_viability_score,
            financial_planning_score=s.financial_planning_score,
            esg_score=s.esg_score,
            risk_assessment_score=s.risk_assessment_score,
            team_strength_score=s.team_strength_score,
            market_opportunity_score=s.market_opportunity_score,
            is_live=s.is_live,
            calculated_at=s.calculated_at,
        )
        for s in scores
    ]
    return ScoreHistoryResponse(items=items)


# ── Helpers ─────────────────────────────────────────────────────────────────


def _build_detail_response(score) -> SignalScoreDetailResponse:
    """Build detailed response from SignalScore model."""
    scoring_details = score.scoring_details or {}
    dimensions_data = scoring_details.get("dimensions", {})

    dimensions = []
    for dim in DIMENSIONS:
        dim_data = dimensions_data.get(dim.id, {})
        criteria = [
            CriterionScoreResponse(
                id=c.get("id", ""),
                name=c.get("name", ""),
                max_points=c.get("max_points", 0),
                score=c.get("score", 0),
                has_document=c.get("has_document", False),
                ai_assessment=c.get("ai_assessment"),
            )
            for c in dim_data.get("criteria", [])
        ]
        dimensions.append(
            DimensionScoreResponse(
                id=dim.id,
                name=dim.name,
                weight=dim.weight,
                score=dim_data.get("score", 0),
                completeness_score=dim_data.get("completeness_score", 0),
                quality_score=dim_data.get("quality_score", 0),
                criteria=criteria,
            )
        )

    return SignalScoreDetailResponse(
        id=score.id,
        project_id=score.project_id,
        overall_score=score.overall_score,
        dimensions=dimensions,
        improvement_guidance=score.improvement_guidance,
        model_used=score.model_used or "deterministic",
        version=score.version,
        is_live=score.is_live,
        calculated_at=score.calculated_at,
    )


# ── Explainability / Snapshot trend endpoints ────────────────────────────────


@router.get("/{project_id}/history-trend", summary="Get score trend over time")
async def get_score_history_trend(
    project_id: uuid.UUID,
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_readonly_session),
):
    """Get signal score trend over time from metric snapshots."""
    from app.modules.metrics.snapshot_service import MetricSnapshotService
    try:
        await service.get_latest_score(db, project_id, current_user.org_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    svc = MetricSnapshotService(db)
    snapshots = await svc.get_trend("project", project_id, "signal_score", from_date, to_date)
    return [
        {
            "date": s.recorded_at.isoformat(),
            "value": s.value,
            "previous_value": s.previous_value,
            "delta": round(s.value - s.previous_value, 2) if s.previous_value is not None else None,
            "trigger_event": s.trigger_event,
            "dimensions": (s.metadata_ or {}).get("dimensions", {}),
        }
        for s in snapshots
    ]


@router.get("/{project_id}/changes", summary="Get score change explanations")
async def get_score_changes(
    project_id: uuid.UUID,
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_readonly_session),
):
    """Get change explanations with triggers explaining what caused score movements."""
    from app.modules.signal_score.explainability import ScoreExplainability
    try:
        await service.get_latest_score(db, project_id, current_user.org_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    explainer = ScoreExplainability(db)
    return await explainer.explain_changes(project_id, from_date, to_date)


@router.get("/{project_id}/volatility", summary="Get score volatility indicator")
async def get_score_volatility(
    project_id: uuid.UUID,
    period_months: int = Query(6, ge=1, le=24),
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_readonly_session),
):
    """Get score stability indicator."""
    from app.modules.signal_score.explainability import ScoreExplainability
    try:
        await service.get_latest_score(db, project_id, current_user.org_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    explainer = ScoreExplainability(db)
    return await explainer.get_score_volatility(project_id, period_months)


@router.get("/{project_id}/dimension-history", summary="Get per-dimension score history")
async def get_dimension_history(
    project_id: uuid.UUID,
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_readonly_session),
):
    """Get per-dimension score breakdown over time."""
    from app.modules.signal_score.explainability import ScoreExplainability
    try:
        await service.get_latest_score(db, project_id, current_user.org_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    explainer = ScoreExplainability(db)
    return await explainer.get_dimension_history(project_id, from_date, to_date)


# ── Bulk Operations ─────────────────────────────────────────────────────────


class BulkScoreRequest(BaseModel):
    project_ids: list[uuid.UUID]


@router.post(
    "/bulk/compute",
    summary="Bulk enqueue score computation",
    status_code=status.HTTP_202_ACCEPTED,
)
async def bulk_compute_scores(
    req: BulkScoreRequest,
    current_user: CurrentUser = Depends(require_permission("run_analysis", "analysis")),
    db: AsyncSession = Depends(get_db),
):
    """Enqueue signal score computation for multiple projects at once.

    Dispatches a Celery task for each project ID.  Projects that cannot be
    found or fail to queue are reported in ``failed``.
    Maximum 100 projects per request.
    """
    if len(req.project_ids) > 100:
        raise HTTPException(status_code=400, detail="Max 100 items per bulk request")

    queued = 0
    failed: list[str] = []

    for project_id in req.project_ids:
        try:
            task_log = await service.trigger_calculation(
                db, project_id, current_user.org_id, current_user.user_id
            )
            await db.flush()
            queued += 1
        except LookupError as exc:
            logger.warning("bulk_compute.project_not_found", project_id=str(project_id), error=str(exc))
            failed.append(str(project_id))
        except Exception as exc:
            logger.warning("bulk_compute.project_failed", project_id=str(project_id), error=str(exc))
            failed.append(str(project_id))

    if queued:
        await db.commit()

    logger.info(
        "bulk_compute_queued",
        org_id=str(current_user.org_id),
        queued=queued,
        failed=len(failed),
    )
    return {"queued": queued, "failed": failed}
