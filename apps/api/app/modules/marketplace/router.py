"""Marketplace API router."""

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_permission
from app.core.database import get_db
from app.modules.marketplace import service
from app.modules.marketplace.schemas import (
    ListingCreateRequest,
    ListingListResponse,
    ListingResponse,
    ListingUpdateRequest,
    PriceSuggestion,
    RFQCreateRequest,
    RFQListResponse,
    RFQRespondRequest,
    RFQResponse,
    TransactionListResponse,
    TransactionResponse,
)
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()

router = APIRouter(prefix="/marketplace", tags=["marketplace"])


# ── Fixed paths (before parameterised) ───────────────────────────────────────


@router.get("/listings", response_model=ListingListResponse)
async def browse_listings(
    listing_type: str | None = Query(None),
    sector: str | None = Query(None),
    geography: str | None = Query(None),
    price_min: float | None = Query(None),
    price_max: float | None = Query(None),
    status: str | None = Query(None),
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    """Browse active marketplace listings with optional filters."""
    return await service.list_listings(
        db,
        viewer_org_id=current_user.org_id,
        listing_type=listing_type,
        sector=sector,
        geography=geography,
        price_min=price_min,
        price_max=price_max,
        status=status,
    )


@router.post(
    "/listings",
    response_model=ListingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_listing(
    body: ListingCreateRequest,
    current_user: CurrentUser = Depends(require_permission("create", "project")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new marketplace listing."""
    try:
        listing = await service.create_listing(db, current_user.org_id, body)
        await db.commit()
        await db.refresh(listing)
        return await service._enrich_listing(db, listing)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/rfqs/sent", response_model=RFQListResponse)
async def list_sent_rfqs(
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    """List RFQs submitted by my organisation (buyer view)."""
    return await service.list_sent_rfqs(db, current_user.org_id)


@router.get("/rfqs/received", response_model=RFQListResponse)
async def list_received_rfqs(
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    """List RFQs received on my listings (seller view)."""
    return await service.list_received_rfqs(db, current_user.org_id)


@router.get("/transactions", response_model=TransactionListResponse)
async def list_transactions(
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    """List all transactions where my org is buyer or seller."""
    return await service.list_transactions(db, current_user.org_id)


@router.get("/price-suggestion", response_model=PriceSuggestion)
async def get_price_suggestion(
    listing_type: str = Query(...),
    project_type: str | None = Query(None),
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    """Suggest an asking price based on recent comparable transactions."""
    try:
        return await service.suggest_price(db, listing_type, project_type)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc))


# ── Parameterised listing routes ───────────────────────────────────────────────


@router.get("/listings/{listing_id}", response_model=ListingResponse)
async def get_listing(
    listing_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    """Get listing detail."""
    try:
        listing = await service.get_listing(db, listing_id, current_user.org_id)
        return await service._enrich_listing(db, listing)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.put("/listings/{listing_id}", response_model=ListingResponse)
async def update_listing(
    listing_id: uuid.UUID,
    body: ListingUpdateRequest,
    current_user: CurrentUser = Depends(require_permission("create", "project")),
    db: AsyncSession = Depends(get_db),
):
    """Update a listing (seller only)."""
    try:
        listing = await service.update_listing(db, listing_id, current_user.org_id, body)
        await db.commit()
        await db.refresh(listing)
        return await service._enrich_listing(db, listing)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.delete("/listings/{listing_id}", status_code=status.HTTP_204_NO_CONTENT)
async def withdraw_listing(
    listing_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("create", "project")),
    db: AsyncSession = Depends(get_db),
):
    """Withdraw (soft-delete) a listing."""
    try:
        await service.withdraw_listing(db, listing_id, current_user.org_id)
        await db.commit()
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post(
    "/listings/{listing_id}/rfq",
    response_model=RFQResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_rfq(
    listing_id: uuid.UUID,
    body: RFQCreateRequest,
    current_user: CurrentUser = Depends(require_permission("create", "match")),
    db: AsyncSession = Depends(get_db),
):
    """Submit a Request for Quote on a listing."""
    try:
        rfq = await service.submit_rfq(
            db, listing_id, current_user.org_id, current_user.user_id, body
        )
        await db.commit()
        await db.refresh(rfq)
        return service._rfq_to_response(rfq)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


# ── RFQ response ──────────────────────────────────────────────────────────────


@router.put("/rfqs/{rfq_id}/respond", response_model=RFQResponse)
async def respond_to_rfq(
    rfq_id: uuid.UUID,
    body: RFQRespondRequest,
    current_user: CurrentUser = Depends(require_permission("create", "match")),
    db: AsyncSession = Depends(get_db),
):
    """Accept, reject, or counter an RFQ (seller only)."""
    try:
        rfq, _tx = await service.respond_to_rfq(
            db, rfq_id, current_user.org_id, body
        )
        await db.commit()
        await db.refresh(rfq)
        return service._rfq_to_response(rfq)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


# ── Transaction completion ────────────────────────────────────────────────────


@router.post(
    "/transactions/{transaction_id}/complete",
    response_model=TransactionResponse,
)
async def complete_transaction(
    transaction_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("create", "match")),
    db: AsyncSession = Depends(get_db),
):
    """Mark a transaction as completed."""
    try:
        tx = await service.complete_transaction(
            db, transaction_id, current_user.org_id
        )
        await db.commit()
        await db.refresh(tx)
        return service._tx_to_response(tx)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
