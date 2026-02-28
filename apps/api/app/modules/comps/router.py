"""Comparable Transactions API router."""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_permission
from app.core.database import get_db
from app.modules.comps import service
from app.modules.comps.schemas import (
    CompCreate,
    CompListResponse,
    CompResponse,
    CompUpdate,
    ImpliedValuationRequest,
    ImpliedValuationResponse,
    SimilarCompsResponse,
)
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()

router = APIRouter(prefix="/comps", tags=["comparable-transactions"])


@router.get("", response_model=CompListResponse)
async def search_comps(
    asset_type: str | None = None,
    geography: str | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    stage: str | None = None,
    min_size_eur: float | None = None,
    max_size_eur: float | None = None,
    data_quality: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: CurrentUser = Depends(require_permission("view", "comp")),
    db: AsyncSession = Depends(get_db),
):
    """Search comparable transactions (org's own + global public comps)."""
    comps, total = await service.search_comps(
        db,
        org_id=current_user.org_id,
        asset_type=asset_type,
        geography=geography,
        year_from=year_from,
        year_to=year_to,
        stage=stage,
        min_size_eur=min_size_eur,
        max_size_eur=max_size_eur,
        data_quality=data_quality,
        limit=limit,
        offset=offset,
    )
    return CompListResponse(items=[CompResponse.model_validate(c) for c in comps], total=total)


@router.post("", response_model=CompResponse, status_code=status.HTTP_201_CREATED)
async def create_comp(
    body: CompCreate,
    current_user: CurrentUser = Depends(require_permission("create", "comp")),
    db: AsyncSession = Depends(get_db),
):
    """Add a new comparable transaction."""
    comp = await service.create_comp(db, org_id=current_user.org_id, user_id=current_user.user_id, data=body)
    await db.commit()
    await db.refresh(comp)
    logger.info("comp.created", comp_id=str(comp.id), org_id=str(current_user.org_id))
    return CompResponse.model_validate(comp)


@router.get("/similar/{project_id}", response_model=SimilarCompsResponse)
async def find_similar_comps(
    project_id: uuid.UUID,
    limit: int = Query(10, ge=1, le=50),
    current_user: CurrentUser = Depends(require_permission("view", "comp")),
    db: AsyncSession = Depends(get_db),
):
    """Find comps most similar to a project using AI ranking."""
    results = await service.find_similar_comps(db, org_id=current_user.org_id, project_id=project_id, limit=limit)
    return SimilarCompsResponse(items=results)


@router.post("/implied-valuation", response_model=ImpliedValuationResponse)
async def calculate_implied_valuation(
    body: ImpliedValuationRequest,
    current_user: CurrentUser = Depends(require_permission("view", "comp")),
    db: AsyncSession = Depends(get_db),
):
    """Calculate implied valuation from selected comparable transactions."""
    result = await service.calculate_implied_valuation(db, comp_ids=body.comp_ids, project=body.project.model_dump())
    return ImpliedValuationResponse(**result)


@router.post("/import-csv", status_code=status.HTTP_201_CREATED)
async def import_comps_csv(
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(require_permission("create", "comp")),
    db: AsyncSession = Depends(get_db),
):
    """Bulk import comparable transactions from CSV."""
    contents = await file.read()
    try:
        csv_text = contents.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded CSV")

    result = await service.import_comps_csv(db, org_id=current_user.org_id, user_id=current_user.user_id, csv_content=csv_text)
    logger.info("comp.csv_import", created=result["created"], errors=len(result["errors"]), org_id=str(current_user.org_id))
    return result


@router.get("/{comp_id}", response_model=CompResponse)
async def get_comp(
    comp_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "comp")),
    db: AsyncSession = Depends(get_db),
):
    """Get a single comparable transaction."""
    comp = await service.get_comp(db, comp_id=comp_id, org_id=current_user.org_id)
    if not comp:
        raise HTTPException(status_code=404, detail="Comparable transaction not found")
    return CompResponse.model_validate(comp)


@router.put("/{comp_id}", response_model=CompResponse)
async def update_comp(
    comp_id: uuid.UUID,
    body: CompUpdate,
    current_user: CurrentUser = Depends(require_permission("create", "comp")),
    db: AsyncSession = Depends(get_db),
):
    """Update a comparable transaction."""
    comp = await service.update_comp(db, comp_id=comp_id, org_id=current_user.org_id, data=body)
    if not comp:
        raise HTTPException(status_code=404, detail="Comparable transaction not found or not editable")
    await db.commit()
    await db.refresh(comp)
    return CompResponse.model_validate(comp)


@router.delete("/{comp_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comp(
    comp_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("create", "comp")),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a comparable transaction."""
    deleted = await service.delete_comp(db, comp_id=comp_id, org_id=current_user.org_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Comparable transaction not found")
    await db.commit()
