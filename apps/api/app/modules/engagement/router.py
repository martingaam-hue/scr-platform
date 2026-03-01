"""Engagement tracking API router."""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_permission
from app.core.database import get_db, get_readonly_session
from app.modules.engagement.schemas import (
    DocumentAnalyticsResponse,
    EngagementSessionResponse,
    InvestorEngagementResponse,
    TrackCloseRequest,
    TrackDownloadRequest,
    TrackOpenRequest,
    TrackPageRequest,
)
from app.modules.engagement.service import EngagementService
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()

router = APIRouter(prefix="/engagement", tags=["Engagement Tracking"])


# ── Event tracking endpoints ───────────────────────────────────────────────────


@router.post(
    "/track/open",
    response_model=EngagementSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Track document open",
)
async def track_open(
    body: TrackOpenRequest,
    current_user: CurrentUser = Depends(require_permission("view", "document")),
    db: AsyncSession = Depends(get_db),
) -> EngagementSessionResponse:
    """Record a new viewer session when a document is opened.

    Returns the engagement session including its id, which must be passed
    to subsequent track/page, track/close and track/download calls.
    """
    svc = EngagementService(db, current_user.org_id)
    try:
        engagement = await svc.track_open(
            document_id=body.document_id,
            user_id=current_user.user_id,
            session_id=body.session_id,
            total_pages=body.total_pages,
            referrer=body.referrer,
            device=body.device_type,
        )
        await db.commit()
        return EngagementSessionResponse.model_validate(engagement)
    except Exception as exc:
        logger.error("track_open_failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to record document open")


@router.post(
    "/track/page",
    response_model=EngagementSessionResponse,
    summary="Track page view",
)
async def track_page_view(
    body: TrackPageRequest,
    current_user: CurrentUser = Depends(require_permission("view", "document")),
    db: AsyncSession = Depends(get_db),
) -> EngagementSessionResponse:
    """Record or accumulate dwell time for a specific page within a session."""
    svc = EngagementService(db, current_user.org_id)
    try:
        engagement = await svc.track_page_view(
            engagement_id=body.engagement_id,
            page_number=body.page_number,
            time_seconds=body.time_seconds,
        )
        await db.commit()
        return EngagementSessionResponse.model_validate(engagement)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error("track_page_failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to record page view")


@router.post(
    "/track/close",
    response_model=EngagementSessionResponse,
    summary="Track document close",
)
async def track_close(
    body: TrackCloseRequest,
    current_user: CurrentUser = Depends(require_permission("view", "document")),
    db: AsyncSession = Depends(get_db),
) -> EngagementSessionResponse:
    """Mark a viewer session as closed."""
    svc = EngagementService(db, current_user.org_id)
    try:
        engagement = await svc.track_close(engagement_id=body.engagement_id)
        await db.commit()
        return EngagementSessionResponse.model_validate(engagement)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error("track_close_failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to record document close")


@router.post(
    "/track/download",
    response_model=EngagementSessionResponse,
    summary="Track document download",
)
async def track_download(
    body: TrackDownloadRequest,
    current_user: CurrentUser = Depends(require_permission("view", "document")),
    db: AsyncSession = Depends(get_db),
) -> EngagementSessionResponse:
    """Mark the document as downloaded within an existing viewer session."""
    svc = EngagementService(db, current_user.org_id)
    try:
        engagement = await svc.track_download(engagement_id=body.engagement_id)
        await db.commit()
        return EngagementSessionResponse.model_validate(engagement)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error("track_download_failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to record download")


# ── Analytics read endpoints ───────────────────────────────────────────────────


@router.get(
    "/document/{document_id}",
    response_model=DocumentAnalyticsResponse,
    summary="Document engagement analytics",
)
async def get_document_analytics(
    document_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "document")),
    db: AsyncSession = Depends(get_readonly_session),
) -> DocumentAnalyticsResponse:
    """Return aggregate analytics for a document: views, time, page heatmap, recent sessions."""
    svc = EngagementService(db, current_user.org_id)
    data = await svc.get_document_analytics(document_id)
    return DocumentAnalyticsResponse(**data)


@router.get(
    "/project/{project_id}",
    response_model=list[InvestorEngagementResponse],
    summary="Project investor engagement",
)
async def get_project_engagement(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_readonly_session),
) -> list[InvestorEngagementResponse]:
    """Return per-investor engagement summaries for all documents in a project."""
    svc = EngagementService(db, current_user.org_id)
    results = await svc.get_deal_engagement(project_id=project_id)
    return [InvestorEngagementResponse(**r) for r in results]


@router.get(
    "/deal-room/{deal_room_id}",
    response_model=list[InvestorEngagementResponse],
    summary="Deal room investor engagement",
)
async def get_deal_room_engagement(
    deal_room_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_readonly_session),
) -> list[InvestorEngagementResponse]:
    """Return per-investor engagement summaries filtered to a specific deal room."""
    from app.models.deal_rooms import DealRoom

    # Resolve the project_id from the deal room (org-scoped check)
    from sqlalchemy import select as sa_select
    dr_result = await db.execute(
        sa_select(DealRoom).where(
            DealRoom.id == deal_room_id,
            DealRoom.org_id == current_user.org_id,
            DealRoom.is_deleted.is_(False),
        )
    )
    deal_room = dr_result.scalar_one_or_none()
    if not deal_room:
        raise HTTPException(status_code=404, detail=f"Deal room {deal_room_id} not found")

    svc = EngagementService(db, current_user.org_id)
    results = await svc.get_deal_engagement(
        project_id=deal_room.project_id,
        deal_room_id=deal_room_id,
    )
    return [InvestorEngagementResponse(**r) for r in results]


@router.get(
    "/heatmap/{document_id}",
    response_model=dict[int, int],
    summary="Document page heatmap",
)
async def get_page_heatmap(
    document_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "document")),
    db: AsyncSession = Depends(get_readonly_session),
) -> dict[int, int]:
    """Return a page-number → total_seconds heatmap for the document."""
    svc = EngagementService(db, current_user.org_id)
    return await svc.get_page_heatmap(document_id)
