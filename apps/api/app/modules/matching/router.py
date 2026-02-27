"""Matching API router — investor & ally sides."""

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_permission
from app.core.database import get_db
from app.modules.matching import service
from app.modules.matching.schemas import (
    AllyRecommendationsResponse,
    InvestorRecommendationsResponse,
    MandateCreateRequest,
    MandateResponse,
    MandateUpdateRequest,
    MatchMessageResponse,
    MatchStatusResponse,
    MatchStatusUpdateRequest,
    MessagesResponse,
    SendMessageRequest,
)
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()

router = APIRouter(prefix="/matching", tags=["matching"])


# ── Investor recommendations ──────────────────────────────────────────────────


@router.get("/investor/recommendations", response_model=InvestorRecommendationsResponse)
async def get_investor_recommendations(
    sector: str | None = Query(None),
    geography: str | None = Query(None),
    min_alignment: int | None = Query(None, ge=0, le=100),
    sort_by: str = Query("alignment", pattern="^(alignment|signal_score|recency)$"),
    current_user: CurrentUser = Depends(require_permission("view", "match")),
    db: AsyncSession = Depends(get_db),
):
    """Projects matching this investor's mandates, scored by alignment."""
    return await service.get_investor_recommendations(
        db,
        current_user.org_id,
        sector=sector,
        geography=geography,
        min_alignment=min_alignment,
        sort_by=sort_by,
    )


# ── Ally recommendations ──────────────────────────────────────────────────────


@router.get(
    "/ally/recommendations/{project_id}",
    response_model=AllyRecommendationsResponse,
)
async def get_ally_recommendations(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "match")),
    db: AsyncSession = Depends(get_db),
):
    """Investors matching this project's profile, scored by alignment."""
    try:
        return await service.get_ally_recommendations(
            db, project_id, current_user.org_id
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ── Mandate CRUD (fixed paths before /{match_id}) ────────────────────────────


@router.get("/mandates", response_model=list[MandateResponse])
async def list_mandates(
    current_user: CurrentUser = Depends(require_permission("view", "match")),
    db: AsyncSession = Depends(get_db),
):
    """List all mandates for current org."""
    mandates = await service.list_mandates(db, current_user.org_id)
    return [service._mandate_to_response(m) for m in mandates]


@router.post(
    "/mandates",
    response_model=MandateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_mandate(
    body: MandateCreateRequest,
    current_user: CurrentUser = Depends(require_permission("create", "match")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new investment mandate."""
    try:
        mandate = await service.create_mandate(db, current_user.org_id, body)
        await db.commit()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return service._mandate_to_response(mandate)


@router.put("/mandates/{mandate_id}", response_model=MandateResponse)
async def update_mandate(
    mandate_id: uuid.UUID,
    body: MandateUpdateRequest,
    current_user: CurrentUser = Depends(require_permission("create", "match")),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing mandate."""
    try:
        mandate = await service.update_mandate(
            db, current_user.org_id, mandate_id, body
        )
        await db.commit()
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return service._mandate_to_response(mandate)


# ── Match actions (parameterised /{match_id}) ─────────────────────────────────


@router.post(
    "/{match_id}/interest",
    response_model=MatchStatusResponse,
)
async def express_interest(
    match_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("create", "match")),
    db: AsyncSession = Depends(get_db),
):
    """Investor expresses interest in a project."""
    try:
        result = await service.express_interest(
            db, match_id, current_user.org_id, current_user.user_id
        )
        await db.commit()
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return result


@router.post(
    "/{match_id}/request-intro",
    response_model=MatchStatusResponse,
)
async def request_intro(
    match_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("create", "match")),
    db: AsyncSession = Depends(get_db),
):
    """Request a formal introduction between investor and ally."""
    try:
        result = await service.request_intro(
            db, match_id, current_user.org_id, current_user.user_id
        )
        await db.commit()
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return result


@router.put("/{match_id}/status", response_model=MatchStatusResponse)
async def update_match_status(
    match_id: uuid.UUID,
    body: MatchStatusUpdateRequest,
    current_user: CurrentUser = Depends(require_permission("create", "match")),
    db: AsyncSession = Depends(get_db),
):
    """Update match pipeline status (pass, engage, etc.)."""
    try:
        result = await service.update_match_status(
            db,
            match_id,
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
    return result


@router.get("/{match_id}/messages", response_model=MessagesResponse)
async def get_messages(
    match_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "match")),
    db: AsyncSession = Depends(get_db),
):
    """Get the secure messaging thread for a match."""
    try:
        return await service.get_messages(
            db, match_id, current_user.org_id
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post(
    "/{match_id}/messages",
    response_model=MatchMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def send_message(
    match_id: uuid.UUID,
    body: SendMessageRequest,
    current_user: CurrentUser = Depends(require_permission("create", "match")),
    db: AsyncSession = Depends(get_db),
):
    """Send a message in a match thread."""
    try:
        msg = await service.send_message(
            db,
            match_id,
            current_user.org_id,
            current_user.user_id,
            body.content,
        )
        await db.commit()
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return msg
