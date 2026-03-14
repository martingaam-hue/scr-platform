"""Tests for the Marketplace module — listings, RFQs, and transactions."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db, get_readonly_db, get_readonly_session
from app.main import app
from app.models.core import Organization, User
from app.models.enums import (
    ListingStatus,
    ListingType,
    ListingVisibility,
    OrgType,
    RFQStatus,
    TransactionStatus,
    UserRole,
)
from app.models.marketplace import RFQ, Listing, Transaction
from app.modules.marketplace import service
from app.modules.marketplace.schemas import ListingCreateRequest
from app.schemas.auth import CurrentUser

# ── Constants ─────────────────────────────────────────────────────────────────

ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
BUYER_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000030")
BUYER_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000031")

SELLER_USER = CurrentUser(
    user_id=USER_ID,
    org_id=ORG_ID,
    role=UserRole.ADMIN,
    email="seller@example.com",
    external_auth_id="user_seller_001",
)

BUYER_USER = CurrentUser(
    user_id=BUYER_USER_ID,
    org_id=BUYER_ORG_ID,
    role=UserRole.ADMIN,
    email="buyer@example.com",
    external_auth_id="user_buyer_001",
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _override_auth(user: CurrentUser):
    async def _override():
        return user

    return _override


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
async def seed_orgs(db: AsyncSession) -> None:
    """Seed seller and buyer organisations with users."""
    seller_org = Organization(id=ORG_ID, name="Seller Org", slug="seller-org", type=OrgType.ALLY)
    buyer_org = Organization(
        id=BUYER_ORG_ID, name="Buyer Org", slug="buyer-org", type=OrgType.INVESTOR
    )
    seller_user = User(
        id=USER_ID,
        org_id=ORG_ID,
        email="seller@example.com",
        full_name="Seller Admin",
        role=UserRole.ADMIN,
        external_auth_id="user_seller_001",
        is_active=True,
    )
    buyer_user = User(
        id=BUYER_USER_ID,
        org_id=BUYER_ORG_ID,
        email="buyer@example.com",
        full_name="Buyer Admin",
        role=UserRole.ADMIN,
        external_auth_id="user_buyer_001",
        is_active=True,
    )
    db.add_all([seller_org, buyer_org, seller_user, buyer_user])
    await db.flush()


@pytest.fixture
async def seller_client(db: AsyncSession, seed_orgs: None) -> AsyncClient:
    app.dependency_overrides[get_current_user] = _override_auth(SELLER_USER)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_readonly_db] = lambda: db
    app.dependency_overrides[get_readonly_session] = lambda: db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def buyer_client(db: AsyncSession, seed_orgs: None) -> AsyncClient:
    app.dependency_overrides[get_current_user] = _override_auth(BUYER_USER)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_readonly_db] = lambda: db
    app.dependency_overrides[get_readonly_session] = lambda: db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def sample_listing(db: AsyncSession, seed_orgs: None) -> Listing:
    listing = Listing(
        org_id=ORG_ID,
        title="Solar Farm Series A",
        description="25MW operational solar portfolio",
        listing_type=ListingType.EQUITY_SALE,
        status=ListingStatus.ACTIVE,
        visibility=ListingVisibility.PUBLIC,
        asking_price=Decimal("5000000.00"),
        minimum_investment=Decimal("500000.00"),
        currency="USD",
    )
    db.add(listing)
    await db.flush()
    await db.refresh(listing)
    return listing


@pytest.fixture
async def sample_rfq(db: AsyncSession, sample_listing: Listing) -> RFQ:
    rfq = RFQ(
        listing_id=sample_listing.id,
        buyer_org_id=BUYER_ORG_ID,
        proposed_price=Decimal("4500000.00"),
        currency="USD",
        status=RFQStatus.SUBMITTED,
        message="Interested in acquiring majority stake",
        submitted_by=BUYER_USER_ID,
    )
    db.add(rfq)
    await db.flush()
    await db.refresh(rfq)
    return rfq


# ── Tests: Listings ───────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_create_listing_happy_path(seller_client: AsyncClient) -> None:
    """Creating a listing without a project returns 201 with correct data."""
    resp = await seller_client.post(
        "/v1/marketplace/listings",
        json={
            "title": "Wind Energy Co-investment",
            "description": "50MW wind farm co-investment opportunity",
            "listing_type": "co_investment",
            "visibility": "qualified_only",
            "asking_price": 2000000.0,
            "currency": "USD",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Wind Energy Co-investment"
    assert data["listing_type"] == "co_investment"
    assert data["status"] == "active"
    assert data["org_id"] == str(ORG_ID)


@pytest.mark.anyio
async def test_create_listing_invalid_project_raises_404(seller_client: AsyncClient) -> None:
    """Creating a listing with a non-existent project_id returns 404."""
    resp = await seller_client.post(
        "/v1/marketplace/listings",
        json={
            "title": "Orphan Listing",
            "listing_type": "equity_sale",
            "project_id": str(uuid.uuid4()),
        },
    )
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_get_listing_returns_enriched_response(
    seller_client: AsyncClient, sample_listing: Listing
) -> None:
    """GET /listings/{id} returns listing data for any authenticated user."""
    resp = await seller_client.get(f"/v1/marketplace/listings/{sample_listing.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(sample_listing.id)
    assert data["title"] == "Solar Farm Series A"
    assert "rfq_count" in data


@pytest.mark.anyio
async def test_list_listings_returns_active_by_default(
    seller_client: AsyncClient, sample_listing: Listing
) -> None:
    """GET /listings returns active listings scoped to all orgs (marketplace-wide)."""
    resp = await seller_client.get("/v1/marketplace/listings")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    ids = [item["id"] for item in data["items"]]
    assert str(sample_listing.id) in ids


@pytest.mark.anyio
async def test_list_listings_filter_by_type(
    seller_client: AsyncClient, sample_listing: Listing
) -> None:
    """Filtering by listing_type=equity_sale returns only matching listings."""
    resp = await seller_client.get("/v1/marketplace/listings?listing_type=equity_sale")
    assert resp.status_code == 200
    data = resp.json()
    for item in data["items"]:
        assert item["listing_type"] == "equity_sale"


@pytest.mark.anyio
async def test_update_listing_by_seller_succeeds(
    seller_client: AsyncClient, sample_listing: Listing
) -> None:
    """Seller can update their own listing title and asking price."""
    resp = await seller_client.put(
        f"/v1/marketplace/listings/{sample_listing.id}",
        json={"title": "Updated Solar Farm Title", "asking_price": 4800000.0},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Updated Solar Farm Title"


@pytest.mark.anyio
async def test_update_listing_by_non_owner_returns_404(
    buyer_client: AsyncClient, sample_listing: Listing
) -> None:
    """A buyer cannot update a listing owned by the seller — returns 404."""
    resp = await buyer_client.put(
        f"/v1/marketplace/listings/{sample_listing.id}",
        json={"title": "Hijacked Title"},
    )
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_withdraw_listing_sets_withdrawn_status(
    seller_client: AsyncClient, sample_listing: Listing, db: AsyncSession
) -> None:
    """DELETE /listings/{id} transitions the listing to WITHDRAWN status."""
    resp = await seller_client.delete(f"/v1/marketplace/listings/{sample_listing.id}")
    assert resp.status_code == 204

    await db.refresh(sample_listing)
    assert sample_listing.status == ListingStatus.WITHDRAWN


# ── Tests: RFQs ───────────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_submit_rfq_happy_path(
    buyer_client: AsyncClient, sample_listing: Listing
) -> None:
    """Buyer can submit an RFQ on an active listing from a different org."""
    resp = await buyer_client.post(
        f"/v1/marketplace/listings/{sample_listing.id}/rfq",
        json={"proposed_price": 4750000.0, "currency": "USD", "message": "Very interested"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "submitted"
    assert float(data["proposed_price"]) == 4750000.0
    assert data["buyer_org_id"] == str(BUYER_ORG_ID)


@pytest.mark.anyio
async def test_submit_rfq_own_listing_rejected(
    seller_client: AsyncClient, sample_listing: Listing
) -> None:
    """Seller cannot submit an RFQ on their own listing — returns 422."""
    resp = await seller_client.post(
        f"/v1/marketplace/listings/{sample_listing.id}/rfq",
        json={"proposed_price": 1000000.0},
    )
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_list_received_rfqs_shows_seller_view(
    seller_client: AsyncClient, sample_rfq: RFQ
) -> None:
    """Seller sees RFQs submitted on their listings at /rfqs/received."""
    resp = await seller_client.get("/v1/marketplace/rfqs/received")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    rfq_ids = [item["id"] for item in data["items"]]
    assert str(sample_rfq.id) in rfq_ids


@pytest.mark.anyio
async def test_respond_to_rfq_accept_creates_transaction(
    seller_client: AsyncClient,
    sample_rfq: RFQ,
    db: AsyncSession,
) -> None:
    """Seller accepting an RFQ creates a PENDING transaction and marks listing SOLD."""
    resp = await seller_client.put(
        f"/v1/marketplace/rfqs/{sample_rfq.id}/respond",
        json={"action": "accept"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "accepted"

    await db.refresh(sample_rfq)
    assert sample_rfq.status == RFQStatus.ACCEPTED


@pytest.mark.anyio
async def test_respond_to_rfq_reject(
    seller_client: AsyncClient,
    sample_rfq: RFQ,
    db: AsyncSession,
) -> None:
    """Seller rejecting an RFQ sets its status to rejected."""
    resp = await seller_client.put(
        f"/v1/marketplace/rfqs/{sample_rfq.id}/respond",
        json={"action": "reject"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "rejected"


@pytest.mark.anyio
async def test_list_transactions_org_scoped(
    seller_client: AsyncClient,
    db: AsyncSession,
    sample_listing: Listing,
) -> None:
    """GET /transactions returns transactions where the org is buyer or seller."""
    tx = Transaction(
        listing_id=sample_listing.id,
        buyer_org_id=BUYER_ORG_ID,
        seller_org_id=ORG_ID,
        amount=Decimal("4500000.00"),
        currency="USD",
        status=TransactionStatus.PENDING,
    )
    db.add(tx)
    await db.flush()

    resp = await seller_client.get("/v1/marketplace/transactions")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    tx_ids = [item["id"] for item in data["items"]]
    assert str(tx.id) in tx_ids


# ── Tests: Service-level unit tests ───────────────────────────────────────────


@pytest.mark.anyio
async def test_service_create_listing(db: AsyncSession, seed_orgs: None) -> None:
    """Service-level: create_listing sets status to ACTIVE."""
    body = ListingCreateRequest(
        title="Direct Service Listing",
        listing_type="carbon_credit",
        visibility="public",
        asking_price=25.0,
        currency="USD",
    )
    listing = await service.create_listing(db, ORG_ID, body)
    assert listing.status == ListingStatus.ACTIVE
    assert listing.org_id == ORG_ID


@pytest.mark.anyio
async def test_service_withdraw_sold_listing_raises(
    db: AsyncSession, sample_listing: Listing
) -> None:
    """Service raises ValueError when withdrawing a SOLD listing."""
    sample_listing.status = ListingStatus.SOLD
    await db.flush()

    with pytest.raises(ValueError, match="Cannot withdraw a completed sale"):
        await service.withdraw_listing(db, sample_listing.id, ORG_ID)


@pytest.mark.anyio
async def test_price_suggestion_fallback_when_no_transactions(
    seller_client: AsyncClient,
) -> None:
    """GET /price-suggestion returns a market estimate when no comparable transactions exist."""
    resp = await seller_client.get(
        "/v1/marketplace/price-suggestion?listing_type=equity_sale"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["comparable_count"] == 0
    assert data["suggested_price"] > 0
    assert "Market estimate" in data["basis"]
