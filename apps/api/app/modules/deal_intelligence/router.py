"""Deal Intelligence API router."""

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_permission
from app.core.database import get_db
from app.modules.deal_intelligence import service
from app.services.response_cache import cache_key, get_cached, set_cached
from app.modules.deal_intelligence.schemas import (
    BatchScreenItem,
    BatchScreenRequest,
    BatchScreenResponse,
    CompareRequest,
    CompareResponse,
    DealPipelineResponse,
    DealStatusUpdateRequest,
    DiscoveryResponse,
    MemoAcceptedResponse,
    MemoResponse,
    ScreenAcceptedResponse,
    ScreeningReportResponse,
)
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()

router = APIRouter(prefix="/deals", tags=["deal-intelligence"])


# ── Fixed paths (before parameterised /{project_id}) ─────────────────────────


@router.get("/pipeline", response_model=DealPipelineResponse)
async def get_pipeline(
    current_user: CurrentUser = Depends(require_permission("view", "match")),
    db: AsyncSession = Depends(get_db),
):
    """Get deal pipeline grouped by stage."""
    return await service.get_deal_pipeline(db, current_user.org_id)


@router.get("/discover", response_model=DiscoveryResponse)
async def discover_deals(
    sector: str | None = Query(None),
    geography: str | None = Query(None),
    score_min: int | None = Query(None, ge=0, le=100),
    score_max: int | None = Query(None, ge=0, le=100),
    current_user: CurrentUser = Depends(require_permission("view", "match")),
    db: AsyncSession = Depends(get_db),
):
    """Discover published projects matching investor mandate."""
    return await service.discover_deals(
        db,
        current_user.org_id,
        sector=sector,
        geography=geography,
        score_min=score_min,
        score_max=score_max,
    )


@router.post("/compare", response_model=CompareResponse)
async def compare_projects(
    body: CompareRequest,
    current_user: CurrentUser = Depends(require_permission("view", "match")),
    db: AsyncSession = Depends(get_db),
):
    """Compare 2–5 projects side by side."""
    return await service.compare_projects(db, body.project_ids, current_user.org_id)


@router.post(
    "/batch-screen",
    response_model=BatchScreenResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def batch_screen_projects(
    body: BatchScreenRequest,
    current_user: CurrentUser = Depends(require_permission("run_analysis", "analysis")),
    db: AsyncSession = Depends(get_db),
):
    """Queue AI deal screening for multiple projects in a single call.

    Accepts a list of project IDs and dispatches a Celery screening task for
    each one. Projects that are not found or not published are reported in
    ``errors`` but do not block the rest from being queued.
    Returns per-project task_log_ids for individual status polling.
    """
    if not body.project_ids:
        return BatchScreenResponse(queued=0, failed=0, items=[], errors=[])

    if len(body.project_ids) > 50:
        raise HTTPException(
            status_code=422,
            detail="Cannot batch-screen more than 50 projects at once",
        )

    items: list[BatchScreenItem] = []
    errors: list[dict] = []

    for project_id in body.project_ids:
        try:
            task_log = await service.trigger_screening(
                db, project_id, current_user.org_id, current_user.user_id
            )
            await db.flush()
            items.append(
                BatchScreenItem(
                    project_id=project_id,
                    task_log_id=task_log.id,
                    status="pending",
                )
            )
        except LookupError as exc:
            errors.append({"project_id": str(project_id), "error": str(exc)})
        except Exception as exc:
            logger.warning(
                "batch_screen.project_failed",
                project_id=str(project_id),
                error=str(exc),
            )
            errors.append({"project_id": str(project_id), "error": str(exc)})

    if items:
        await db.commit()

    logger.info(
        "batch_screen_queued",
        org_id=str(current_user.org_id),
        queued=len(items),
        failed=len(errors),
    )
    return BatchScreenResponse(
        queued=len(items),
        failed=len(errors),
        items=items,
        errors=errors,
    )


# ── Parameterised endpoints ───────────────────────────────────────────────────


@router.get("/{project_id}/screening", response_model=ScreeningReportResponse)
async def get_screening_report(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "match")),
    db: AsyncSession = Depends(get_db),
):
    """Get latest AI screening report for a project."""
    ck = cache_key("deal_screening", str(current_user.org_id), str(project_id))
    cached = await get_cached(ck)
    if cached is not None:
        return cached

    report = await service.get_screening_report(db, project_id, current_user.org_id)
    if not report:
        raise HTTPException(status_code=404, detail="No screening report found")

    # Only cache completed reports — pending/processing may change shortly
    if report.status == "completed":
        await set_cached(ck, jsonable_encoder(report), ttl=300)
    return report


@router.post(
    "/{project_id}/screen",
    response_model=ScreenAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_screening(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("run_analysis", "analysis")),
    db: AsyncSession = Depends(get_db),
):
    """Trigger AI screening for a project."""
    try:
        task_log = await service.trigger_screening(
            db, project_id, current_user.org_id, current_user.user_id
        )
        await db.commit()
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return ScreenAcceptedResponse(
        task_log_id=task_log.id,
        status="pending",
        message="Deal screening started",
    )


@router.post(
    "/{project_id}/memo",
    response_model=MemoAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_memo(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("create", "report")),
    db: AsyncSession = Depends(get_db),
):
    """Trigger investment memo generation for a project."""
    try:
        report = await service.trigger_memo(
            db, project_id, current_user.org_id, current_user.user_id
        )
        await db.commit()
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return MemoAcceptedResponse(
        memo_id=report.id,
        status="queued",
        message="Investment memo generation started",
    )


@router.get("/{project_id}/memo/{memo_id}", response_model=MemoResponse)
async def get_memo(
    project_id: uuid.UUID,
    memo_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "report")),
    db: AsyncSession = Depends(get_db),
):
    """Get investment memo status and content."""
    memo = await service.get_memo(db, project_id, memo_id, current_user.org_id)
    if not memo:
        raise HTTPException(status_code=404, detail="Memo not found")
    return memo


@router.put("/{project_id}/status", response_model=dict)
async def update_deal_status(
    project_id: uuid.UUID,
    body: DealStatusUpdateRequest,
    current_user: CurrentUser = Depends(require_permission("create", "match")),
    db: AsyncSession = Depends(get_db),
):
    """Move a deal to a different pipeline stage."""
    try:
        match = await service.update_deal_status(
            db,
            project_id,
            current_user.org_id,
            current_user.user_id,
            body.status,
            body.notes,
        )
        await db.commit()
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return {"match_id": str(match.id), "status": match.status.value}
