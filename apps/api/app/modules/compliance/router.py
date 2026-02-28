"""Compliance & regulatory calendar API router."""

from __future__ import annotations

import uuid
from datetime import date

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_permission
from app.core.database import get_db
from app.modules.compliance import service
from app.modules.compliance.schemas import (
    AutoGenerateRequest,
    CompleteDeadlineRequest,
    DeadlineCreate,
    DeadlineListResponse,
    DeadlineResponse,
    DeadlineUpdate,
)
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()

router = APIRouter(prefix="/compliance", tags=["compliance"])


def _enrich(deadline: object) -> DeadlineResponse:
    today = date.today()
    resp = DeadlineResponse.model_validate(deadline)
    resp.days_until_due = (deadline.due_date - today).days  # type: ignore[attr-defined]
    resp.is_overdue = deadline.due_date < today and deadline.status not in ("completed", "waived")  # type: ignore[attr-defined]
    return resp


@router.get("/deadlines", response_model=DeadlineListResponse)
async def list_deadlines(
    status: str | None = Query(None),
    category: str | None = Query(None),
    project_id: uuid.UUID | None = Query(None),
    current_user: CurrentUser = Depends(require_permission("view", "compliance")),
    db: AsyncSession = Depends(get_db),
):
    deadlines = await service.list_deadlines(
        db, current_user.org_id, status=status, category=category, project_id=project_id
    )
    today = date.today()
    items = [_enrich(d) for d in deadlines]
    return DeadlineListResponse(
        items=items,
        total=len(items),
        overdue_count=sum(1 for d in deadlines if d.due_date < today and d.status not in ("completed", "waived")),
        due_this_week=sum(1 for d in deadlines if 0 <= (d.due_date - today).days <= 7),
        due_this_month=sum(1 for d in deadlines if 0 <= (d.due_date - today).days <= 30),
    )


@router.post("/deadlines", response_model=DeadlineResponse, status_code=status.HTTP_201_CREATED)
async def create_deadline(
    body: DeadlineCreate,
    current_user: CurrentUser = Depends(require_permission("manage", "compliance")),
    db: AsyncSession = Depends(get_db),
):
    deadline = await service.create_deadline(db, current_user.org_id, body)
    return _enrich(deadline)


@router.get("/deadlines/{deadline_id}", response_model=DeadlineResponse)
async def get_deadline(
    deadline_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "compliance")),
    db: AsyncSession = Depends(get_db),
):
    deadline = await service.get_deadline(db, deadline_id, current_user.org_id)
    if not deadline:
        raise HTTPException(status_code=404, detail="Deadline not found")
    return _enrich(deadline)


@router.patch("/deadlines/{deadline_id}", response_model=DeadlineResponse)
async def update_deadline(
    deadline_id: uuid.UUID,
    body: DeadlineUpdate,
    current_user: CurrentUser = Depends(require_permission("manage", "compliance")),
    db: AsyncSession = Depends(get_db),
):
    deadline = await service.get_deadline(db, deadline_id, current_user.org_id)
    if not deadline:
        raise HTTPException(status_code=404, detail="Deadline not found")
    deadline = await service.update_deadline(db, deadline, body)
    return _enrich(deadline)


@router.post("/deadlines/{deadline_id}/complete", response_model=DeadlineResponse)
async def complete_deadline(
    deadline_id: uuid.UUID,
    body: CompleteDeadlineRequest = CompleteDeadlineRequest(),
    current_user: CurrentUser = Depends(require_permission("manage", "compliance")),
    db: AsyncSession = Depends(get_db),
):
    deadline = await service.get_deadline(db, deadline_id, current_user.org_id)
    if not deadline:
        raise HTTPException(status_code=404, detail="Deadline not found")
    deadline = await service.complete_deadline(db, deadline)
    return _enrich(deadline)


@router.delete("/deadlines/{deadline_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_deadline(
    deadline_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("manage", "compliance")),
    db: AsyncSession = Depends(get_db),
):
    deadline = await service.get_deadline(db, deadline_id, current_user.org_id)
    if not deadline:
        raise HTTPException(status_code=404, detail="Deadline not found")
    await service.delete_deadline(db, deadline)


@router.post("/deadlines/auto-generate", response_model=list[DeadlineResponse])
async def auto_generate(
    body: AutoGenerateRequest,
    current_user: CurrentUser = Depends(require_permission("manage", "compliance")),
    db: AsyncSession = Depends(get_db),
):
    deadlines = await service.auto_generate_deadlines(
        db, current_user.org_id, body.project_id, body.jurisdiction, body.project_type
    )
    return [_enrich(d) for d in deadlines]
