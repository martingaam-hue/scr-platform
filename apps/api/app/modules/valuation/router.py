"""Valuation Analysis API router."""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_permission
from app.core.database import get_db
from app.modules.valuation import service
from app.services.response_cache import cache_key, get_cached, set_cached
from app.modules.valuation.schemas import (
    AssumptionSuggestion,
    BatchValuationItem,
    BatchValuationRequest,
    BatchValuationResponse,
    SensitivityMatrix,
    SensitivityRequest,
    SuggestAssumptionsRequest,
    ValuationCreateRequest,
    ValuationListResponse,
    ValuationReportResponse,
    ValuationResponse,
    ValuationUpdateRequest,
)
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()

router = APIRouter(prefix="/valuations", tags=["valuations"])


# ── Fixed paths (MUST come before /{valuation_id}) ────────────────────────────


@router.post(
    "/batch",
    summary="Batch create valuations",
    response_model=BatchValuationResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def batch_valuations(
    body: BatchValuationRequest,
    current_user: CurrentUser = Depends(require_permission("create", "project")),
    db: AsyncSession = Depends(get_db),
):
    """Trigger valuation analysis for multiple projects at once.

    Accepts up to 50 project IDs. Creates a Valuation record for each project
    using the shared method and params from the request body. Projects that
    fail (e.g. missing params for the method, or project not found) are
    reported in the ``errors`` list but do not prevent the rest from running.
    """
    if len(body.project_ids) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 projects per batch")

    items: list[BatchValuationItem] = []
    errors: list[dict] = []

    for pid in body.project_ids:
        try:
            valuation_data = ValuationCreateRequest(
                project_id=pid,
                method=body.method,
                currency=body.currency,
                dcf_params=body.dcf_params,
                comparable_params=body.comparable_params,
                replacement_params=body.replacement_params,
                blended_params=body.blended_params,
            )
            val = await service.create_valuation(
                db, current_user.org_id, current_user.user_id, valuation_data
            )
            await db.flush()
            items.append(
                BatchValuationItem(
                    project_id=pid,
                    valuation_id=val.id,
                    status="queued",
                )
            )
        except Exception as exc:
            logger.warning(
                "batch_valuation.project_failed",
                project_id=str(pid),
                error=str(exc),
            )
            errors.append({"project_id": str(pid), "error": str(exc)})

    if items:
        await db.commit()

    logger.info(
        "batch_valuations_queued",
        org_id=str(current_user.org_id),
        queued=len(items),
        failed=len(errors),
    )
    return BatchValuationResponse(
        queued=len(items),
        failed=len(errors),
        items=items,
        errors=errors,
    )


@router.post("/suggest-assumptions", summary="Suggest DCF assumptions", response_model=AssumptionSuggestion)
async def suggest_assumptions(
    body: SuggestAssumptionsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("view", "project")),
):
    """AI-assisted assumption suggestions for DCF valuation."""
    return await service.suggest_assumptions(
        body.project_type, body.geography, body.stage, db=db
    )


@router.post("/compare", summary="Compare multiple valuations", response_model=list[ValuationResponse])
async def compare_valuations(
    valuation_ids: list[uuid.UUID],
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    """Fetch multiple valuations for side-by-side comparison."""
    results = []
    for vid in valuation_ids[:5]:  # limit to 5
        try:
            val = await service.get_valuation(db, vid, current_user.org_id)
            results.append(service._to_response(val))
        except LookupError:
            pass
    return results


# ── CRUD ──────────────────────────────────────────────────────────────────────


@router.post(
    "",
    summary="Create valuation",
    response_model=ValuationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_valuation(
    body: ValuationCreateRequest,
    current_user: CurrentUser = Depends(require_permission("create", "project")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new valuation for a project."""
    try:
        val = await service.create_valuation(
            db, current_user.org_id, current_user.user_id, body
        )
        await db.commit()
        await db.refresh(val)
        return service._to_response(val)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("", summary="List valuations", response_model=ValuationListResponse)
async def list_valuations(
    project_id: uuid.UUID | None = Query(None),
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    """List valuations for the organisation, optionally filtered by project."""
    items = await service.list_valuations(db, current_user.org_id, project_id)
    return ValuationListResponse(
        items=[service._to_response(v) for v in items],
        total=len(items),
    )


@router.get("/{valuation_id}", summary="Get valuation", response_model=ValuationResponse)
async def get_valuation(
    valuation_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    """Get a single valuation by ID."""
    ck = cache_key("valuation", str(current_user.org_id), str(valuation_id))
    cached = await get_cached(ck)
    if cached is not None:
        return cached

    try:
        val = await service.get_valuation(db, valuation_id, current_user.org_id)
        result = service._to_response(val)
        await set_cached(ck, jsonable_encoder(result), ttl=600)
        return result
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.put("/{valuation_id}", summary="Update valuation", response_model=ValuationResponse)
async def update_valuation(
    valuation_id: uuid.UUID,
    body: ValuationUpdateRequest,
    current_user: CurrentUser = Depends(require_permission("create", "project")),
    db: AsyncSession = Depends(get_db),
):
    """Update valuation inputs and recalculate. Blocked for APPROVED valuations."""
    try:
        val = await service.update_valuation(db, valuation_id, current_user.org_id, body)
        await db.commit()
        await db.refresh(val)
        return service._to_response(val)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.put("/{valuation_id}/approve", summary="Approve valuation", response_model=ValuationResponse)
async def approve_valuation(
    valuation_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("approve", "project")),
    db: AsyncSession = Depends(get_db),
):
    """Approve a valuation. Supersedes any previously approved version."""
    try:
        val = await service.approve_valuation(
            db, valuation_id, current_user.org_id, current_user.user_id
        )
        await db.commit()
        await db.refresh(val)
        return service._to_response(val)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


# ── Analysis ──────────────────────────────────────────────────────────────────


@router.post("/{valuation_id}/sensitivity", summary="Run sensitivity matrix", response_model=SensitivityMatrix)
async def run_sensitivity(
    valuation_id: uuid.UUID,
    body: SensitivityRequest,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    """Run a two-variable sensitivity matrix on a DCF valuation."""
    try:
        return await service.run_sensitivity(
            db, valuation_id, current_user.org_id, body
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post(
    "/{valuation_id}/report",
    summary="Generate valuation report",
    response_model=ValuationReportResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_report(
    valuation_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("create", "report")),
    db: AsyncSession = Depends(get_db),
):
    """Queue a valuation report for async generation."""
    try:
        report = await service.trigger_report(
            db, valuation_id, current_user.org_id, current_user.user_id
        )
        await db.commit()
        await db.refresh(report)

        from app.modules.valuation.tasks import generate_valuation_report_task
        generate_valuation_report_task.delay(str(report.id))

        return ValuationReportResponse(
            report_id=report.id,
            status=report.status.value,
            message="Valuation report queued for generation.",
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
