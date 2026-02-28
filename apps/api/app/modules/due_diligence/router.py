"""Due Diligence Checklist API router."""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_permission
from app.core.database import get_db
from app.modules.due_diligence import service
from app.modules.due_diligence.schemas import (
    AddCustomItemRequest,
    DDChecklistResponse,
    GenerateChecklistRequest,
    TriggerAIReviewRequest,
    UpdateItemStatusRequest,
)
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()

router = APIRouter(prefix="/due-diligence", tags=["due-diligence"])


# ── Checklist endpoints ───────────────────────────────────────────────────────


@router.post(
    "/checklists/generate",
    status_code=status.HTTP_201_CREATED,
)
async def generate_checklist(
    body: GenerateChecklistRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a DD checklist for a project from the best matching template."""
    try:
        checklist = await service.generate_checklist(
            db,
            project_id=body.project_id,
            org_id=current_user.org_id,
            investor_id=body.investor_id,
        )
        return checklist.to_dict()
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/checklists")
async def list_checklists(
    project_id: uuid.UUID | None = Query(None),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List DD checklists for the current org, optionally filtered by project."""
    return await service.list_checklists(db, current_user.org_id, project_id=project_id)


@router.get("/checklists/{checklist_id}", response_model=DDChecklistResponse)
async def get_checklist(
    checklist_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a DD checklist with all item statuses."""
    result = await service.get_checklist(db, checklist_id, current_user.org_id)
    if not result:
        raise HTTPException(status_code=404, detail="Checklist not found")
    return result


@router.put("/checklists/{checklist_id}/items/{item_id}/status")
async def update_item_status(
    checklist_id: uuid.UUID,
    item_id: uuid.UUID,
    body: UpdateItemStatusRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the status of a checklist item."""
    valid_statuses = {"pending", "in_review", "satisfied", "partially_met", "not_met", "waived"}
    if body.status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(sorted(valid_statuses))}",
        )

    result = await service.update_item_status(
        db,
        checklist_id=checklist_id,
        item_id=item_id,
        org_id=current_user.org_id,
        status=body.status,
        notes=body.notes,
        document_id=body.document_id,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Checklist item not found")

    # Award gamification badges when a DD item is satisfied
    if body.status == "satisfied":
        try:
            from app.modules.gamification import service as _gami
            await _gami.evaluate_badges(
                db, current_user.user_id, None, "dd_item_complete"
            )
        except Exception:
            pass

    return result.to_dict()


@router.post("/checklists/{checklist_id}/items/{item_id}/review")
async def trigger_ai_review(
    checklist_id: uuid.UUID,
    item_id: uuid.UUID,
    body: TriggerAIReviewRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger AI review of a document against a checklist item."""
    result = await service.trigger_ai_review(
        db,
        checklist_id=checklist_id,
        item_id=item_id,
        document_id=body.document_id,
        org_id=current_user.org_id,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Checklist item not found")
    return result


@router.post("/checklists/{checklist_id}/items/add", status_code=status.HTTP_201_CREATED)
async def add_custom_item(
    checklist_id: uuid.UUID,
    body: AddCustomItemRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a custom item to a checklist."""
    result = await service.add_custom_item(
        db,
        checklist_id=checklist_id,
        org_id=current_user.org_id,
        name=body.name,
        category=body.category,
        description=body.description,
        priority=body.priority,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Checklist not found")
    return result.to_dict()


# ── Template endpoints ────────────────────────────────────────────────────────


@router.get("/templates")
async def list_templates(
    asset_type: str | None = Query(None),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List DD checklist templates."""
    return await service.list_templates(db, asset_type=asset_type)


@router.get("/templates/{template_id}")
async def get_template(
    template_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a DD checklist template with all its items."""
    result = await service.get_template(db, template_id)
    if not result:
        raise HTTPException(status_code=404, detail="Template not found")
    return result
