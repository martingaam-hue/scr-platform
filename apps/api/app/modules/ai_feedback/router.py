"""AI Feedback & Quality Tracking API.

Provides endpoints for:
- Rating AI outputs (👍 / 👎)
- Tracking user edits to AI-generated content
- Tracking direct acceptance of AI outputs
- Admin quality reports and correction analytics
"""

import uuid
from datetime import datetime, timedelta
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_permission
from app.core.database import get_db
from app.models.ai import AIOutputFeedback, AITaskLog
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()
router = APIRouter(prefix="/ai-feedback", tags=["ai-feedback"])


# ── Request / Response schemas ────────────────────────────────────────────────


class RateRequest(BaseModel):
    task_log_id: uuid.UUID | None = None
    task_type: str = Field(..., min_length=1, max_length=100)
    entity_type: str | None = None
    entity_id: uuid.UUID | None = None
    rating: int = Field(..., ge=-1, le=1, description="1 = positive, -1 = negative, 0 = neutral")
    comment: str | None = Field(default=None, max_length=2000)
    metadata: dict[str, Any] | None = None


class TrackEditRequest(BaseModel):
    task_log_id: uuid.UUID | None = None
    task_type: str = Field(..., min_length=1, max_length=100)
    entity_type: str | None = None
    entity_id: uuid.UUID | None = None
    original_content: str
    edited_content: str
    metadata: dict[str, Any] | None = None


class TrackAcceptRequest(BaseModel):
    task_log_id: uuid.UUID | None = None
    task_type: str = Field(..., min_length=1, max_length=100)
    entity_type: str | None = None
    entity_id: uuid.UUID | None = None
    metadata: dict[str, Any] | None = None


class FeedbackResponse(BaseModel):
    id: uuid.UUID
    task_type: str
    rating: int
    was_edited: bool
    was_accepted: bool
    created_at: datetime


class QualityMetric(BaseModel):
    task_type: str
    total_feedback: int
    positive_count: int
    negative_count: int
    positive_rate: float
    edit_rate: float
    accept_rate: float
    avg_edit_distance_pct: float | None


class QualityReportResponse(BaseModel):
    period_days: int
    total_feedback: int
    overall_positive_rate: float
    metrics_by_task_type: list[QualityMetric]
    generated_at: datetime


class CorrectionItem(BaseModel):
    id: uuid.UUID
    task_type: str
    entity_type: str | None
    entity_id: uuid.UUID | None
    original_content: str
    edited_content: str
    edit_distance_pct: float | None
    comment: str | None
    created_at: datetime


class CorrectionsResponse(BaseModel):
    items: list[CorrectionItem]
    total: int


# ── Helpers ───────────────────────────────────────────────────────────────────


def _edit_distance_pct(original: str, edited: str) -> float:
    """Approximate edit distance as % of original length changed.

    Uses a character-level approximation: longer strings get a rough
    estimate without the O(n²) cost of full Levenshtein.
    """
    if not original:
        return 1.0 if edited else 0.0
    if original == edited:
        return 0.0
    # Compare character sets as a cheap proxy
    orig_chars = set(original)
    edit_chars = set(edited)
    shared = len(orig_chars & edit_chars)
    total = max(len(orig_chars), len(edit_chars))
    similarity = shared / total if total else 1.0
    # Weight by length difference ratio
    len_diff = abs(len(original) - len(edited)) / max(len(original), 1)
    return min(1.0, (1.0 - similarity) * 0.5 + len_diff * 0.5)


# ── User-facing endpoints ─────────────────────────────────────────────────────


@router.post("/rate", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def rate_output(
    body: RateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FeedbackResponse:
    """Submit a 👍 (1) or 👎 (-1) rating for an AI output."""
    # Validate task_log belongs to user's org
    if body.task_log_id:
        result = await db.execute(
            select(AITaskLog.id).where(
                and_(AITaskLog.id == body.task_log_id, AITaskLog.org_id == current_user.org_id)
            )
        )
        if result.scalar_one_or_none() is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task log not found")

    feedback = AIOutputFeedback(
        org_id=current_user.org_id,
        user_id=current_user.user_id,
        task_log_id=body.task_log_id,
        task_type=body.task_type,
        entity_type=body.entity_type,
        entity_id=body.entity_id,
        rating=body.rating,
        comment=body.comment,
        metadata_=body.metadata,
    )
    db.add(feedback)
    await db.commit()
    await db.refresh(feedback)

    logger.info("ai_feedback_rated", task_type=body.task_type, rating=body.rating)
    return FeedbackResponse(
        id=feedback.id,
        task_type=feedback.task_type,
        rating=feedback.rating,
        was_edited=feedback.was_edited,
        was_accepted=feedback.was_accepted,
        created_at=feedback.created_at,
    )


@router.post("/track-edit", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def track_edit(
    body: TrackEditRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FeedbackResponse:
    """Record that a user edited an AI-generated output.

    Automatically computes edit distance percentage.
    """
    dist_pct = _edit_distance_pct(body.original_content, body.edited_content)

    feedback = AIOutputFeedback(
        org_id=current_user.org_id,
        user_id=current_user.user_id,
        task_log_id=body.task_log_id,
        task_type=body.task_type,
        entity_type=body.entity_type,
        entity_id=body.entity_id,
        rating=0,  # neutral — edit is implicit signal, not explicit rating
        was_edited=True,
        original_content=body.original_content,
        edited_content=body.edited_content,
        edit_distance_pct=dist_pct,
        metadata_=body.metadata,
    )
    db.add(feedback)
    await db.commit()
    await db.refresh(feedback)

    logger.info("ai_feedback_edit_tracked", task_type=body.task_type, edit_distance_pct=dist_pct)
    return FeedbackResponse(
        id=feedback.id,
        task_type=feedback.task_type,
        rating=feedback.rating,
        was_edited=feedback.was_edited,
        was_accepted=feedback.was_accepted,
        created_at=feedback.created_at,
    )


@router.post("/track-accept", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def track_accept(
    body: TrackAcceptRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FeedbackResponse:
    """Record that a user accepted an AI output without modification."""
    feedback = AIOutputFeedback(
        org_id=current_user.org_id,
        user_id=current_user.user_id,
        task_log_id=body.task_log_id,
        task_type=body.task_type,
        entity_type=body.entity_type,
        entity_id=body.entity_id,
        rating=0,
        was_accepted=True,
        metadata_=body.metadata,
    )
    db.add(feedback)
    await db.commit()
    await db.refresh(feedback)

    logger.info("ai_feedback_accepted", task_type=body.task_type)
    return FeedbackResponse(
        id=feedback.id,
        task_type=feedback.task_type,
        rating=feedback.rating,
        was_edited=feedback.was_edited,
        was_accepted=feedback.was_accepted,
        created_at=feedback.created_at,
    )


# ── Admin endpoints ──────────────────────────────────────────────────────────


@router.get("/admin/quality-report", response_model=QualityReportResponse)
async def get_quality_report(
    period_days: int = Query(default=30, ge=1, le=365),
    current_user: CurrentUser = Depends(require_permission("manage_settings", "settings")),
    db: AsyncSession = Depends(get_db),
) -> QualityReportResponse:
    """Aggregate quality metrics by task type over the specified time window.

    Requires admin role.
    """
    since = datetime.utcnow() - timedelta(days=period_days)

    # Aggregate per task_type
    agg = await db.execute(
        select(
            AIOutputFeedback.task_type,
            func.count(AIOutputFeedback.id).label("total"),
            func.sum(case((AIOutputFeedback.rating == 1, 1), else_=0)).label("positive"),
            func.sum(case((AIOutputFeedback.rating == -1, 1), else_=0)).label("negative"),
            func.sum(case((AIOutputFeedback.was_edited.is_(True), 1), else_=0)).label("edited"),
            func.sum(case((AIOutputFeedback.was_accepted.is_(True), 1), else_=0)).label("accepted"),
            func.avg(AIOutputFeedback.edit_distance_pct).label("avg_edit_dist"),
        )
        .where(
            and_(
                AIOutputFeedback.org_id == current_user.org_id,
                AIOutputFeedback.created_at >= since,
            )
        )
        .group_by(AIOutputFeedback.task_type)
        .order_by(func.count(AIOutputFeedback.id).desc())
    )
    rows = agg.all()

    metrics: list[QualityMetric] = []
    total_feedback = 0
    total_positive = 0

    for row in rows:
        total = row.total or 0
        positive = row.positive or 0
        negative = row.negative or 0
        edited = row.edited or 0
        accepted = row.accepted or 0
        total_feedback += total
        total_positive += positive

        metrics.append(
            QualityMetric(
                task_type=row.task_type,
                total_feedback=total,
                positive_count=positive,
                negative_count=negative,
                positive_rate=round(positive / total, 4) if total else 0.0,
                edit_rate=round(edited / total, 4) if total else 0.0,
                accept_rate=round(accepted / total, 4) if total else 0.0,
                avg_edit_distance_pct=round(float(row.avg_edit_dist), 4) if row.avg_edit_dist else None,
            )
        )

    overall_positive_rate = round(total_positive / total_feedback, 4) if total_feedback else 0.0

    return QualityReportResponse(
        period_days=period_days,
        total_feedback=total_feedback,
        overall_positive_rate=overall_positive_rate,
        metrics_by_task_type=metrics,
        generated_at=datetime.utcnow(),
    )


@router.get("/admin/corrections", response_model=CorrectionsResponse)
async def list_corrections(
    task_type: str | None = Query(default=None),
    min_edit_pct: float = Query(default=0.1, ge=0.0, le=1.0),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: CurrentUser = Depends(require_permission("manage_settings", "settings")),
    db: AsyncSession = Depends(get_db),
) -> CorrectionsResponse:
    """List AI outputs that were significantly edited by users.

    Useful for prompt engineering — these represent cases where the AI
    output was materially wrong or incomplete.

    Requires admin role.
    """
    filters = [
        AIOutputFeedback.org_id == current_user.org_id,
        AIOutputFeedback.was_edited.is_(True),
        AIOutputFeedback.edit_distance_pct >= min_edit_pct,
    ]
    if task_type:
        filters.append(AIOutputFeedback.task_type == task_type)

    count_result = await db.execute(
        select(func.count(AIOutputFeedback.id)).where(and_(*filters))
    )
    total = count_result.scalar_one()

    result = await db.execute(
        select(AIOutputFeedback)
        .where(and_(*filters))
        .order_by(AIOutputFeedback.edit_distance_pct.desc(), AIOutputFeedback.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    records = result.scalars().all()

    return CorrectionsResponse(
        items=[
            CorrectionItem(
                id=r.id,
                task_type=r.task_type,
                entity_type=r.entity_type,
                entity_id=r.entity_id,
                original_content=r.original_content or "",
                edited_content=r.edited_content or "",
                edit_distance_pct=r.edit_distance_pct,
                comment=r.comment,
                created_at=r.created_at,
            )
            for r in records
        ],
        total=total,
    )
