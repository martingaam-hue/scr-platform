"""Q&A Workflow — FastAPI router."""

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.schemas.auth import CurrentUser
from app.modules.qa_workflow.schemas import (
    QAAnswerCreate,
    QAAnswerResponse,
    QAQuestionCreate,
    QAQuestionResponse,
    QAStatsResponse,
)
from app.modules.qa_workflow.service import QAService

logger = structlog.get_logger()

router = APIRouter(prefix="/qa", tags=["Q&A Workflow"])


def _svc(db: AsyncSession, current_user: CurrentUser) -> QAService:
    return QAService(db, current_user.org_id)


# ── Per-project endpoints ──────────────────────────────────────────────────────

@router.post(
    "/projects/{project_id}/questions",
    response_model=QAQuestionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_question(
    project_id: uuid.UUID,
    body: QAQuestionCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QAQuestionResponse:
    """Submit a new Q&A question for a project."""
    svc = _svc(db, current_user)
    question = await svc.create_question(project_id, current_user.user_id, body)
    await db.commit()
    # Reload with eager-loaded answers to avoid MissingGreenlet on lazy access
    question = await svc.get_question(question.id)
    return QAQuestionResponse.model_validate(question)


@router.get(
    "/projects/{project_id}/questions",
    response_model=list[QAQuestionResponse],
)
async def list_questions(
    project_id: uuid.UUID,
    status: str | None = Query(default=None),
    category: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[QAQuestionResponse]:
    """List questions for a project with optional filters."""
    svc = _svc(db, current_user)
    questions = await svc.list_questions(project_id, status=status, category=category, skip=skip, limit=limit)
    return [QAQuestionResponse.model_validate(q) for q in questions]


@router.get(
    "/projects/{project_id}/stats",
    response_model=QAStatsResponse,
)
async def get_stats(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QAStatsResponse:
    """Get Q&A statistics for a project."""
    svc = _svc(db, current_user)
    return await svc.get_stats(project_id)


@router.get("/projects/{project_id}/export")
async def export_qa_log(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Export all Q&A for a project as a CSV file."""
    svc = _svc(db, current_user)
    csv_bytes = await svc.export_qa_log(project_id)
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="qa_log_{project_id}.csv"',
        },
    )


# ── Per-question endpoints ─────────────────────────────────────────────────────

@router.get(
    "/questions/{question_id}",
    response_model=QAQuestionResponse,
)
async def get_question(
    question_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QAQuestionResponse:
    """Get a single question with its answers."""
    svc = _svc(db, current_user)
    question = await svc.get_question(question_id)
    if question is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
    return QAQuestionResponse.model_validate(question)


@router.post(
    "/questions/{question_id}/answers",
    response_model=QAAnswerResponse,
    status_code=status.HTTP_201_CREATED,
)
async def answer_question(
    question_id: uuid.UUID,
    body: QAAnswerCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QAAnswerResponse:
    """Post an answer to a question."""
    svc = _svc(db, current_user)
    try:
        answer = await svc.answer_question(question_id, current_user.user_id, body)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    await db.commit()
    await db.refresh(answer)
    return QAAnswerResponse.model_validate(answer)


@router.post(
    "/questions/{question_id}/suggest",
)
async def suggest_answer(
    question_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get an AI-generated answer suggestion for a question."""
    svc = _svc(db, current_user)
    return await svc.suggest_answer(question_id)


@router.put(
    "/questions/{question_id}/assign",
    response_model=QAQuestionResponse,
)
async def assign_question(
    question_id: uuid.UUID,
    assigned_to: uuid.UUID,
    assigned_team: str | None = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QAQuestionResponse:
    """Assign a question to a user and/or team."""
    svc = _svc(db, current_user)
    try:
        question = await svc.assign_question(question_id, assigned_to, assigned_team)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    await db.commit()
    question = await svc.get_question(question.id)
    return QAQuestionResponse.model_validate(question)


@router.put(
    "/questions/{question_id}/status",
    response_model=QAQuestionResponse,
)
async def update_status(
    question_id: uuid.UUID,
    status: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QAQuestionResponse:
    """Update the status of a question."""
    from app.modules.qa_workflow.schemas import QAQuestionUpdate

    svc = _svc(db, current_user)
    try:
        question = await svc.update_question(question_id, QAQuestionUpdate(status=status))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    await db.commit()
    question = await svc.get_question(question.id)
    return QAQuestionResponse.model_validate(question)
