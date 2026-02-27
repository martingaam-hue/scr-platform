"""Valuation Analysis API router."""

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_permission
from app.core.database import get_db
from app.modules.valuation import service
from app.modules.valuation.schemas import (
    AssumptionSuggestion,
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


@router.post("/suggest-assumptions", response_model=AssumptionSuggestion)
async def suggest_assumptions(
    body: SuggestAssumptionsRequest,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
):
    """AI-assisted assumption suggestions for DCF valuation."""
    return await service.suggest_assumptions(
        body.project_type, body.geography, body.stage
    )


@router.post("/compare", response_model=list[ValuationResponse])
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


@router.get("", response_model=ValuationListResponse)
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


@router.get("/{valuation_id}", response_model=ValuationResponse)
async def get_valuation(
    valuation_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    """Get a single valuation by ID."""
    try:
        val = await service.get_valuation(db, valuation_id, current_user.org_id)
        return service._to_response(val)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.put("/{valuation_id}", response_model=ValuationResponse)
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


@router.put("/{valuation_id}/approve", response_model=ValuationResponse)
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


@router.post("/{valuation_id}/sensitivity", response_model=SensitivityMatrix)
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
            db, valuation_id, current_user.org_id
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
