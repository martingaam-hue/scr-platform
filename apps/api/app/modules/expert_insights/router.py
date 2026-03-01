"""Expert Insights API router."""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_permission
from app.core.database import get_db
from app.modules.expert_insights.schemas import (
    CreateExpertNoteRequest,
    ExpertNoteListResponse,
    ExpertNoteResponse,
    InsightsTimelineResponse,
    UpdateExpertNoteRequest,
)
from app.modules.expert_insights.service import ExpertInsightsService
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()

router = APIRouter(prefix="/expert-insights", tags=["expert-insights"])


def _get_svc(db: AsyncSession) -> ExpertInsightsService:
    return ExpertInsightsService(db)


# ── Create ────────────────────────────────────────────────────────────────────


@router.post("", response_model=ExpertNoteResponse, status_code=status.HTTP_201_CREATED)
async def create_expert_note(
    body: CreateExpertNoteRequest,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
) -> ExpertNoteResponse:
    """Create a new expert insight note and trigger async AI enrichment."""
    svc = _get_svc(db)
    note = await svc.create_note(
        org_id=current_user.org_id,
        user_id=current_user.user_id,
        data=body,
    )
    logger.info(
        "expert_note.created",
        note_id=str(note.id),
        project_id=str(note.project_id),
        note_type=note.note_type,
    )

    # Fire-and-forget: try Celery first, fall back to BackgroundTask
    note_id_str = str(note.id)
    try:
        from app.worker import celery_app

        celery_app.send_task("tasks.enrich_expert_note", args=[note_id_str])
    except Exception:
        from app.modules.expert_insights.tasks import enrich_expert_note_task

        background_tasks.add_task(enrich_expert_note_task, note_id_str)

    return ExpertNoteResponse.model_validate(note)


# ── List ──────────────────────────────────────────────────────────────────────


@router.get("", response_model=ExpertNoteListResponse)
async def list_expert_notes(
    project_id: uuid.UUID | None = Query(None),
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
) -> ExpertNoteListResponse:
    """List expert notes for the current org, optionally filtered by project."""
    svc = _get_svc(db)
    notes = await svc.list_notes(
        org_id=current_user.org_id,
        project_id=project_id,
    )
    return ExpertNoteListResponse(
        items=[ExpertNoteResponse.model_validate(n) for n in notes],
        total=len(notes),
    )


# ── Project timeline — must come before /{note_id} ────────────────────────────


@router.get("/projects/{project_id}/timeline", response_model=InsightsTimelineResponse)
async def get_project_insights_timeline(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
) -> InsightsTimelineResponse:
    """Get a chronological timeline of expert notes for a project."""
    svc = _get_svc(db)
    result = await svc.get_project_insights_timeline(
        org_id=current_user.org_id,
        project_id=project_id,
    )
    return InsightsTimelineResponse(**result)


# ── Get single ────────────────────────────────────────────────────────────────


@router.get("/{note_id}", response_model=ExpertNoteResponse)
async def get_expert_note(
    note_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
) -> ExpertNoteResponse:
    svc = _get_svc(db)
    note = await svc.get_note(org_id=current_user.org_id, note_id=note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Expert note not found")
    return ExpertNoteResponse.model_validate(note)


# ── Update ────────────────────────────────────────────────────────────────────


@router.patch("/{note_id}", response_model=ExpertNoteResponse)
async def update_expert_note(
    note_id: uuid.UUID,
    body: UpdateExpertNoteRequest,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
) -> ExpertNoteResponse:
    svc = _get_svc(db)
    note = await svc.update_note(
        org_id=current_user.org_id,
        note_id=note_id,
        data=body,
    )
    if not note:
        raise HTTPException(status_code=404, detail="Expert note not found")
    return ExpertNoteResponse.model_validate(note)


# ── Delete ────────────────────────────────────────────────────────────────────


@router.delete("/{note_id}")
async def delete_expert_note(
    note_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    svc = _get_svc(db)
    deleted = await svc.delete_note(org_id=current_user.org_id, note_id=note_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Expert note not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ── Manual re-enrich ─────────────────────────────────────────────────────────


@router.post("/{note_id}/enrich", response_model=ExpertNoteResponse)
async def enrich_expert_note(
    note_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
) -> ExpertNoteResponse:
    """Manually trigger AI enrichment for a note (useful after failure)."""
    svc = _get_svc(db)
    note = await svc.get_note(org_id=current_user.org_id, note_id=note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Expert note not found")

    note_id_str = str(note.id)
    try:
        from app.worker import celery_app

        celery_app.send_task("tasks.enrich_expert_note", args=[note_id_str])
    except Exception:
        from app.modules.expert_insights.tasks import enrich_expert_note_task

        background_tasks.add_task(enrich_expert_note_task, note_id_str)

    logger.info("expert_note.enrich_triggered", note_id=note_id_str)
    return ExpertNoteResponse.model_validate(note)
