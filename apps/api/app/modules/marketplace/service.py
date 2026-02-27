"""Marketplace service — listings, RFQs, transactions, price discovery."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import (
    ListingStatus,
    ListingType,
    ListingVisibility,
    RFQStatus,
    TransactionStatus,
)
from app.models.marketplace import Listing, RFQ, Transaction
from app.models.projects import Project, SignalScore
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

logger = structlog.get_logger()


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _get_latest_signal_score(
    db: AsyncSession, project_id: uuid.UUID
) -> int | None:
    result = await db.execute(
        select(SignalScore.overall_score)
        .where(SignalScore.project_id == project_id)
        .order_by(SignalScore.version.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _rfq_count_for_listing(db: AsyncSession, listing_id: uuid.UUID) -> int:
    result = await db.execute(
        select(func.count(RFQ.id)).where(
            RFQ.listing_id == listing_id,
            RFQ.is_deleted.is_(False),
        )
    )
    return result.scalar_one() or 0


async def _enrich_listing(
    db: AsyncSession, listing: Listing
) -> ListingResponse:
    project = None
    signal_score = None
    if listing.project_id:
        project = await db.get(Project, listing.project_id)
        signal_score = await _get_latest_signal_score(db, listing.project_id)

    rfq_count = await _rfq_count_for_listing(db, listing.id)

    return ListingResponse(
        id=listing.id,
        org_id=listing.org_id,
        project_id=listing.project_id,
        title=listing.title,
        description=listing.description,
        listing_type=listing.listing_type.value,
        status=listing.status.value,
        visibility=listing.visibility.value,
        asking_price=str(listing.asking_price) if listing.asking_price is not None else None,
        minimum_investment=str(listing.minimum_investment) if listing.minimum_investment is not None else None,
        currency=listing.currency,
        details=listing.details or {},
        expires_at=listing.expires_at,
        project_name=project.name if project else None,
        project_type=project.project_type.value if project else None,
        geography_country=project.geography_country if project else None,
        signal_score=signal_score,
        rfq_count=rfq_count,
        created_at=listing.created_at,
        updated_at=listing.updated_at,
    )


def _rfq_to_response(rfq: RFQ, listing_title: str | None = None) -> RFQResponse:
    return RFQResponse(
        id=rfq.id,
        listing_id=rfq.listing_id,
        buyer_org_id=rfq.buyer_org_id,
        proposed_price=str(rfq.proposed_price),
        currency=rfq.currency,
        status=rfq.status.value,
        message=rfq.message,
        counter_price=str(rfq.counter_price) if rfq.counter_price is not None else None,
        counter_terms=rfq.counter_terms,
        submitted_by=rfq.submitted_by,
        listing_title=listing_title,
        created_at=rfq.created_at,
        updated_at=rfq.updated_at,
    )


def _tx_to_response(tx: Transaction, listing_title: str | None = None) -> TransactionResponse:
    return TransactionResponse(
        id=tx.id,
        listing_id=tx.listing_id,
        buyer_org_id=tx.buyer_org_id,
        seller_org_id=tx.seller_org_id,
        rfq_id=tx.rfq_id,
        amount=str(tx.amount),
        currency=tx.currency,
        status=tx.status.value,
        terms=tx.terms,
        settlement_details=tx.settlement_details,
        completed_at=tx.completed_at,
        listing_title=listing_title,
        created_at=tx.created_at,
        updated_at=tx.updated_at,
    )


# ── Listings ──────────────────────────────────────────────────────────────────


async def create_listing(
    db: AsyncSession,
    org_id: uuid.UUID,
    body: ListingCreateRequest,
) -> Listing:
    # Validate project ownership if project_id provided
    if body.project_id:
        project = await db.get(Project, body.project_id)
        if not project or project.is_deleted or project.org_id != org_id:
            raise LookupError(f"Project {body.project_id} not found or not owned by org")

    listing = Listing(
        org_id=org_id,
        project_id=body.project_id,
        title=body.title,
        description=body.description,
        listing_type=ListingType(body.listing_type),
        status=ListingStatus.ACTIVE,
        visibility=ListingVisibility(body.visibility),
        asking_price=Decimal(str(body.asking_price)) if body.asking_price is not None else None,
        minimum_investment=Decimal(str(body.minimum_investment)) if body.minimum_investment is not None else None,
        currency=body.currency,
        details=body.details or {},
        expires_at=body.expires_at,
    )
    db.add(listing)
    return listing


async def get_listing(
    db: AsyncSession,
    listing_id: uuid.UUID,
    viewer_org_id: uuid.UUID,
) -> Listing:
    listing = await db.execute(
        select(Listing).where(
            Listing.id == listing_id,
            Listing.is_deleted.is_(False),
        )
    )
    listing = listing.scalar_one_or_none()
    if not listing:
        raise LookupError(f"Listing {listing_id} not found")

    # Visibility: invite_only is only visible to the seller
    if listing.visibility == ListingVisibility.INVITE_ONLY and listing.org_id != viewer_org_id:
        raise LookupError(f"Listing {listing_id} not found")

    return listing


async def list_listings(
    db: AsyncSession,
    viewer_org_id: uuid.UUID,
    listing_type: str | None = None,
    sector: str | None = None,
    geography: str | None = None,
    price_min: float | None = None,
    price_max: float | None = None,
    status: str | None = None,
) -> ListingListResponse:
    stmt = select(Listing).where(
        Listing.is_deleted.is_(False),
        # Exclude invite_only from other orgs
        (Listing.visibility != ListingVisibility.INVITE_ONLY) | (Listing.org_id == viewer_org_id),
    )

    if status:
        stmt = stmt.where(Listing.status == ListingStatus(status))
    else:
        # Default: show active + under_negotiation listings
        stmt = stmt.where(Listing.status.in_([ListingStatus.ACTIVE, ListingStatus.UNDER_NEGOTIATION]))

    if listing_type:
        stmt = stmt.where(Listing.listing_type == ListingType(listing_type))

    if price_min is not None:
        stmt = stmt.where(Listing.asking_price >= Decimal(str(price_min)))
    if price_max is not None:
        stmt = stmt.where(Listing.asking_price <= Decimal(str(price_max)))

    stmt = stmt.order_by(Listing.created_at.desc())
    result = await db.execute(stmt)
    listings = list(result.scalars().all())

    # Enrich with project data — apply sector/geography filters
    enriched: list[ListingResponse] = []
    for lst in listings:
        item = await _enrich_listing(db, lst)
        if sector and item.project_type != sector:
            continue
        if geography and item.geography_country and geography.lower() not in item.geography_country.lower():
            continue
        enriched.append(item)

    return ListingListResponse(items=enriched, total=len(enriched))


async def update_listing(
    db: AsyncSession,
    listing_id: uuid.UUID,
    seller_org_id: uuid.UUID,
    body: ListingUpdateRequest,
) -> Listing:
    listing = await db.execute(
        select(Listing).where(
            Listing.id == listing_id,
            Listing.org_id == seller_org_id,
            Listing.is_deleted.is_(False),
        )
    )
    listing = listing.scalar_one_or_none()
    if not listing:
        raise LookupError(f"Listing {listing_id} not found")

    if listing.status in (ListingStatus.SOLD, ListingStatus.WITHDRAWN):
        raise ValueError(f"Cannot update a {listing.status.value} listing")

    if body.title is not None:
        listing.title = body.title
    if body.description is not None:
        listing.description = body.description
    if body.visibility is not None:
        listing.visibility = ListingVisibility(body.visibility)
    if body.asking_price is not None:
        listing.asking_price = Decimal(str(body.asking_price))
    if body.minimum_investment is not None:
        listing.minimum_investment = Decimal(str(body.minimum_investment))
    if body.details is not None:
        listing.details = body.details
    if body.expires_at is not None:
        listing.expires_at = body.expires_at

    return listing


async def withdraw_listing(
    db: AsyncSession, listing_id: uuid.UUID, seller_org_id: uuid.UUID
) -> Listing:
    listing = await db.execute(
        select(Listing).where(
            Listing.id == listing_id,
            Listing.org_id == seller_org_id,
            Listing.is_deleted.is_(False),
        )
    )
    listing = listing.scalar_one_or_none()
    if not listing:
        raise LookupError(f"Listing {listing_id} not found")

    if listing.status == ListingStatus.SOLD:
        raise ValueError("Cannot withdraw a completed sale")

    listing.status = ListingStatus.WITHDRAWN
    return listing


# ── RFQs ──────────────────────────────────────────────────────────────────────


async def submit_rfq(
    db: AsyncSession,
    listing_id: uuid.UUID,
    buyer_org_id: uuid.UUID,
    user_id: uuid.UUID,
    body: RFQCreateRequest,
) -> RFQ:
    listing = await get_listing(db, listing_id, buyer_org_id)

    if listing.status not in (ListingStatus.ACTIVE, ListingStatus.UNDER_NEGOTIATION):
        raise ValueError(f"Cannot submit RFQ on a {listing.status.value} listing")

    if listing.org_id == buyer_org_id:
        raise ValueError("Cannot submit RFQ on your own listing")

    rfq = RFQ(
        listing_id=listing_id,
        buyer_org_id=buyer_org_id,
        proposed_price=Decimal(str(body.proposed_price)),
        proposed_terms=body.proposed_terms,
        currency=body.currency,
        status=RFQStatus.SUBMITTED,
        message=body.message,
        submitted_by=user_id,
    )
    db.add(rfq)

    # Move listing into negotiation
    if listing.status == ListingStatus.ACTIVE:
        listing.status = ListingStatus.UNDER_NEGOTIATION

    return rfq


async def list_sent_rfqs(
    db: AsyncSession, buyer_org_id: uuid.UUID
) -> RFQListResponse:
    result = await db.execute(
        select(RFQ, Listing.title)
        .join(Listing, RFQ.listing_id == Listing.id)
        .where(
            RFQ.buyer_org_id == buyer_org_id,
            RFQ.is_deleted.is_(False),
        )
        .order_by(RFQ.created_at.desc())
    )
    rows = result.all()
    items = [_rfq_to_response(rfq, title) for rfq, title in rows]
    return RFQListResponse(items=items, total=len(items))


async def list_received_rfqs(
    db: AsyncSession, seller_org_id: uuid.UUID
) -> RFQListResponse:
    result = await db.execute(
        select(RFQ, Listing.title)
        .join(Listing, RFQ.listing_id == Listing.id)
        .where(
            Listing.org_id == seller_org_id,
            RFQ.is_deleted.is_(False),
        )
        .order_by(RFQ.created_at.desc())
    )
    rows = result.all()
    items = [_rfq_to_response(rfq, title) for rfq, title in rows]
    return RFQListResponse(items=items, total=len(items))


async def respond_to_rfq(
    db: AsyncSession,
    rfq_id: uuid.UUID,
    seller_org_id: uuid.UUID,
    body: RFQRespondRequest,
) -> tuple[RFQ, Transaction | None]:
    result = await db.execute(
        select(RFQ, Listing)
        .join(Listing, RFQ.listing_id == Listing.id)
        .where(
            RFQ.id == rfq_id,
            Listing.org_id == seller_org_id,
            RFQ.is_deleted.is_(False),
        )
    )
    row = result.one_or_none()
    if not row:
        raise LookupError(f"RFQ {rfq_id} not found")

    rfq, listing = row

    if rfq.status not in (RFQStatus.SUBMITTED, RFQStatus.COUNTERED):
        raise ValueError(f"RFQ cannot be responded to in status {rfq.status.value}")

    transaction: Transaction | None = None

    if body.action == "accept":
        rfq.status = RFQStatus.ACCEPTED
        listing.status = ListingStatus.SOLD
        # Create transaction
        transaction = Transaction(
            listing_id=listing.id,
            buyer_org_id=rfq.buyer_org_id,
            seller_org_id=seller_org_id,
            rfq_id=rfq.id,
            amount=rfq.proposed_price,
            currency=rfq.currency,
            status=TransactionStatus.PENDING,
            terms=rfq.proposed_terms,
        )
        db.add(transaction)

    elif body.action == "reject":
        rfq.status = RFQStatus.REJECTED
        # If no other active RFQs, revert listing to ACTIVE
        other_active = await db.execute(
            select(func.count(RFQ.id)).where(
                RFQ.listing_id == listing.id,
                RFQ.id != rfq.id,
                RFQ.status.in_([RFQStatus.SUBMITTED, RFQStatus.COUNTERED]),
                RFQ.is_deleted.is_(False),
            )
        )
        if (other_active.scalar_one() or 0) == 0:
            listing.status = ListingStatus.ACTIVE

    elif body.action == "counter":
        rfq.status = RFQStatus.COUNTERED
        rfq.counter_price = Decimal(str(body.counter_price))
        rfq.counter_terms = body.counter_terms

    return rfq, transaction


# ── Transactions ──────────────────────────────────────────────────────────────


async def complete_transaction(
    db: AsyncSession, transaction_id: uuid.UUID, org_id: uuid.UUID
) -> Transaction:
    result = await db.execute(
        select(Transaction).where(
            Transaction.id == transaction_id,
            (Transaction.buyer_org_id == org_id) | (Transaction.seller_org_id == org_id),
            Transaction.is_deleted.is_(False),
        )
    )
    tx = result.scalar_one_or_none()
    if not tx:
        raise LookupError(f"Transaction {transaction_id} not found")

    if tx.status == TransactionStatus.COMPLETED:
        raise ValueError("Transaction is already completed")
    if tx.status == TransactionStatus.CANCELLED:
        raise ValueError("Cannot complete a cancelled transaction")

    tx.status = TransactionStatus.COMPLETED
    tx.completed_at = datetime.now(timezone.utc)
    return tx


async def list_transactions(
    db: AsyncSession, org_id: uuid.UUID
) -> TransactionListResponse:
    result = await db.execute(
        select(Transaction, Listing.title)
        .join(Listing, Transaction.listing_id == Listing.id)
        .where(
            (Transaction.buyer_org_id == org_id) | (Transaction.seller_org_id == org_id),
            Transaction.is_deleted.is_(False),
        )
        .order_by(Transaction.created_at.desc())
    )
    rows = result.all()
    items = [_tx_to_response(tx, title) for tx, title in rows]
    return TransactionListResponse(items=items, total=len(items))


# ── Price discovery ──────────────────────────────────────────────────────────


async def suggest_price(
    db: AsyncSession,
    listing_type: str,
    project_type: str | None = None,
) -> PriceSuggestion:
    """Suggest asking price based on recent completed transactions."""
    result = await db.execute(
        select(Transaction.amount)
        .join(Listing, Transaction.listing_id == Listing.id)
        .where(
            Transaction.status == TransactionStatus.COMPLETED,
            Listing.listing_type == ListingType(listing_type),
            Transaction.is_deleted.is_(False),
        )
        .order_by(Transaction.completed_at.desc())
        .limit(20)
    )
    amounts = [float(row) for row in result.scalars().all()]

    if amounts:
        avg = sum(amounts) / len(amounts)
        return PriceSuggestion(
            suggested_price=round(avg, 2),
            price_range_min=round(min(amounts), 2),
            price_range_max=round(max(amounts), 2),
            basis=f"Median of {len(amounts)} recent comparable transactions",
            comparable_count=len(amounts),
        )

    # Rule-based fallback
    fallback: dict[str, tuple[float, float, float]] = {
        "equity_sale":    (5_000_000.0, 1_000_000.0, 50_000_000.0),
        "debt_sale":      (2_000_000.0, 500_000.0,   20_000_000.0),
        "co_investment":  (1_000_000.0, 250_000.0,   10_000_000.0),
        "carbon_credit":  (25.0,         10.0,         75.0),
    }
    mid, lo, hi = fallback.get(listing_type, (1_000_000.0, 100_000.0, 10_000_000.0))
    return PriceSuggestion(
        suggested_price=mid,
        price_range_min=lo,
        price_range_max=hi,
        basis="Market estimate (no comparable transactions found)",
        comparable_count=0,
    )
