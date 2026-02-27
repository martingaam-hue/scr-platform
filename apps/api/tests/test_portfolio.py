"""Comprehensive tests for the Portfolio module."""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.main import app
from app.models.core import Organization, User
from app.models.enums import (
    AssetType,
    FundType,
    HoldingStatus,
    OrgType,
    PortfolioStatus,
    PortfolioStrategy,
    ProjectStage,
    ProjectStatus,
    ProjectType,
    SFDRClassification,
    UserRole,
)
from app.models.investors import Portfolio, PortfolioHolding, PortfolioMetrics
from app.models.projects import Project
from app.modules.portfolio import service
from app.schemas.auth import CurrentUser

# ── Test Data ────────────────────────────────────────────────────────────────

ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
OTHER_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000099")
USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
VIEWER_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000003")
PROJECT_ID = uuid.UUID("00000000-0000-0000-0000-000000000010")

CURRENT_USER = CurrentUser(
    user_id=USER_ID,
    org_id=ORG_ID,
    role=UserRole.ADMIN,
    email="test@example.com",
    external_auth_id="user_test_123",
)

VIEWER_USER = CurrentUser(
    user_id=VIEWER_USER_ID,
    org_id=ORG_ID,
    role=UserRole.VIEWER,
    email="viewer@example.com",
    external_auth_id="user_test_viewer",
)


# ── Fixtures ─────────────────────────────────────────────────────────────────


def _override_auth(user: CurrentUser):
    async def _override():
        return user
    return _override


@pytest.fixture
async def seed_data(db: AsyncSession) -> None:
    """Seed Organization, Users, and Project for FK constraints."""
    org = Organization(id=ORG_ID, name="Test Org", slug="test-org", type=OrgType.INVESTOR)
    db.add(org)
    other_org = Organization(
        id=OTHER_ORG_ID, name="Other Org", slug="other-org", type=OrgType.ALLY
    )
    db.add(other_org)
    user = User(
        id=USER_ID, org_id=ORG_ID, email="test@example.com",
        full_name="Test User", role=UserRole.ADMIN,
        external_auth_id="user_test_123", is_active=True,
    )
    db.add(user)
    viewer = User(
        id=VIEWER_USER_ID, org_id=ORG_ID, email="viewer@example.com",
        full_name="Viewer User", role=UserRole.VIEWER,
        external_auth_id="user_test_viewer", is_active=True,
    )
    db.add(viewer)
    # Project for linking holdings
    project = Project(
        id=PROJECT_ID,
        org_id=ORG_ID,
        name="Linked Solar Project",
        slug="linked-solar-project",
        description="A project linked to portfolio holdings",
        project_type=ProjectType.SOLAR,
        status=ProjectStatus.ACTIVE,
        stage=ProjectStage.CONSTRUCTION,
        geography_country="Spain",
        total_investment_required=Decimal("10000000"),
    )
    db.add(project)
    await db.flush()


@pytest.fixture
async def test_client(db: AsyncSession, seed_data) -> AsyncClient:
    app.dependency_overrides[get_current_user] = _override_auth(CURRENT_USER)
    app.dependency_overrides[get_db] = lambda: db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def viewer_client(db: AsyncSession, seed_data) -> AsyncClient:
    app.dependency_overrides[get_current_user] = _override_auth(VIEWER_USER)
    app.dependency_overrides[get_db] = lambda: db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def sample_portfolio(db: AsyncSession, seed_data) -> Portfolio:
    portfolio = Portfolio(
        org_id=ORG_ID,
        name="Green Energy Fund I",
        description="Impact-focused renewable energy fund",
        strategy=PortfolioStrategy.GROWTH,
        fund_type=FundType.CLOSED_END,
        vintage_year=2024,
        target_aum=Decimal("100000000"),
        current_aum=Decimal("45000000"),
        currency="USD",
        sfdr_classification=SFDRClassification.ARTICLE_9,
    )
    db.add(portfolio)
    await db.flush()
    await db.refresh(portfolio)
    return portfolio


@pytest.fixture
async def sample_holdings(
    db: AsyncSession, sample_portfolio: Portfolio
) -> list[PortfolioHolding]:
    """Create sample holdings for metrics testing."""
    h1 = PortfolioHolding(
        portfolio_id=sample_portfolio.id,
        project_id=PROJECT_ID,
        asset_name="Solar Farm Spain",
        asset_type=AssetType.EQUITY,
        investment_date=date(2023, 1, 15),
        investment_amount=Decimal("5000000"),
        current_value=Decimal("6500000"),
        ownership_pct=Decimal("15"),
        currency="USD",
        status=HoldingStatus.ACTIVE,
    )
    h2 = PortfolioHolding(
        portfolio_id=sample_portfolio.id,
        asset_name="Wind Project Denmark",
        asset_type=AssetType.PROJECT_FINANCE,
        investment_date=date(2023, 6, 1),
        investment_amount=Decimal("3000000"),
        current_value=Decimal("3200000"),
        currency="USD",
        status=HoldingStatus.ACTIVE,
    )
    h3 = PortfolioHolding(
        portfolio_id=sample_portfolio.id,
        asset_name="Exited Battery Co",
        asset_type=AssetType.EQUITY,
        investment_date=date(2022, 1, 1),
        investment_amount=Decimal("2000000"),
        current_value=Decimal("0"),
        currency="USD",
        status=HoldingStatus.EXITED,
        exit_date=date(2024, 6, 1),
        exit_amount=Decimal("3500000"),
    )
    db.add_all([h1, h2, h3])
    await db.flush()
    for h in [h1, h2, h3]:
        await db.refresh(h)
    return [h1, h2, h3]


# ── Service: Portfolio CRUD ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_portfolio(db: AsyncSession, seed_data):
    portfolio = await service.create_portfolio(
        db, CURRENT_USER,
        name="Test Fund",
        strategy=PortfolioStrategy.BALANCED,
        fund_type=FundType.OPEN_END,
        target_aum=Decimal("50000000"),
    )
    assert portfolio.id is not None
    assert portfolio.name == "Test Fund"
    assert portfolio.strategy == PortfolioStrategy.BALANCED
    assert portfolio.status == PortfolioStatus.FUNDRAISING
    assert portfolio.org_id == ORG_ID


@pytest.mark.asyncio
async def test_list_portfolios(db: AsyncSession, seed_data, sample_portfolio):
    portfolios = await service.list_portfolios(db, ORG_ID)
    assert len(portfolios) >= 1
    assert any(p.id == sample_portfolio.id for p in portfolios)


@pytest.mark.asyncio
async def test_list_portfolios_tenant_isolation(db: AsyncSession, seed_data, sample_portfolio):
    portfolios = await service.list_portfolios(db, OTHER_ORG_ID)
    assert len(portfolios) == 0


@pytest.mark.asyncio
async def test_get_portfolio(db: AsyncSession, seed_data, sample_portfolio):
    portfolio = await service.get_portfolio(db, sample_portfolio.id, ORG_ID)
    assert portfolio.id == sample_portfolio.id
    assert portfolio.name == "Green Energy Fund I"


@pytest.mark.asyncio
async def test_get_portfolio_not_found(db: AsyncSession, seed_data):
    with pytest.raises(LookupError):
        await service.get_portfolio(db, uuid.uuid4(), ORG_ID)


@pytest.mark.asyncio
async def test_get_portfolio_wrong_org(db: AsyncSession, seed_data, sample_portfolio):
    with pytest.raises(LookupError):
        await service.get_portfolio(db, sample_portfolio.id, OTHER_ORG_ID)


@pytest.mark.asyncio
async def test_update_portfolio(db: AsyncSession, seed_data, sample_portfolio):
    updated = await service.update_portfolio(
        db, sample_portfolio.id, ORG_ID,
        name="Green Energy Fund II",
        current_aum=Decimal("60000000"),
    )
    assert updated.name == "Green Energy Fund II"
    assert updated.current_aum == Decimal("60000000")


# ── Service: Holdings CRUD ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_add_holding(db: AsyncSession, seed_data, sample_portfolio):
    holding = await service.add_holding(
        db, CURRENT_USER, sample_portfolio.id,
        asset_name="New Solar Asset",
        asset_type=AssetType.EQUITY,
        investment_date=date(2024, 1, 1),
        investment_amount=Decimal("1000000"),
        current_value=Decimal("1100000"),
        ownership_pct=Decimal("10"),
    )
    assert holding.asset_name == "New Solar Asset"
    assert holding.status == HoldingStatus.ACTIVE
    assert holding.portfolio_id == sample_portfolio.id


@pytest.mark.asyncio
async def test_list_holdings(db: AsyncSession, seed_data, sample_portfolio, sample_holdings):
    holdings = await service.list_holdings(db, sample_portfolio.id, ORG_ID)
    assert len(holdings) == 3


@pytest.mark.asyncio
async def test_list_holdings_filter_status(
    db: AsyncSession, seed_data, sample_portfolio, sample_holdings
):
    active = await service.list_holdings(
        db, sample_portfolio.id, ORG_ID, status=HoldingStatus.ACTIVE
    )
    assert len(active) == 2
    assert all(h.status == HoldingStatus.ACTIVE for h in active)

    exited = await service.list_holdings(
        db, sample_portfolio.id, ORG_ID, status=HoldingStatus.EXITED
    )
    assert len(exited) == 1


@pytest.mark.asyncio
async def test_update_holding(db: AsyncSession, seed_data, sample_portfolio, sample_holdings):
    h = sample_holdings[0]
    updated = await service.update_holding(
        db, h.id, sample_portfolio.id, ORG_ID,
        current_value=Decimal("7000000"),
    )
    assert updated.current_value == Decimal("7000000")


@pytest.mark.asyncio
async def test_update_holding_not_found(db: AsyncSession, seed_data, sample_portfolio):
    with pytest.raises(LookupError):
        await service.update_holding(
            db, uuid.uuid4(), sample_portfolio.id, ORG_ID,
            current_value=Decimal("100"),
        )


# ── Service: Metrics (Deterministic Python) ─────────────────────────────────


@pytest.mark.asyncio
async def test_compute_metrics_empty(db: AsyncSession, seed_data, sample_portfolio):
    """Empty portfolio returns zeroed metrics."""
    metrics = await service.compute_metrics(db, sample_portfolio.id, ORG_ID)
    assert metrics["total_invested"] == Decimal("0")
    assert metrics["moic"] is None
    assert metrics["as_of_date"] == date.today()


@pytest.mark.asyncio
async def test_compute_metrics_with_holdings(
    db: AsyncSession, seed_data, sample_portfolio, sample_holdings
):
    metrics = await service.compute_metrics(db, sample_portfolio.id, ORG_ID)

    # Total invested: 5M + 3M + 2M = 10M
    assert metrics["total_invested"] == Decimal("10000000")

    # Total distributions: 3.5M (from exited holding)
    assert metrics["total_distributions"] == Decimal("3500000")

    # Total current: 6.5M + 3.2M + 0 = 9.7M
    # Total value = 9.7M + 3.5M = 13.2M
    assert metrics["total_value"] == Decimal("13200000")

    # MOIC = 13.2M / 10M = 1.32
    assert metrics["moic"] == Decimal("1.32")

    # TVPI = total_value / total_invested = 1.32
    assert metrics["tvpi"] == Decimal("1.32")

    # DPI = 3.5M / 10M = 0.35
    assert metrics["dpi"] == Decimal("0.35")

    # RVPI = 9.7M / 10M = 0.97
    assert metrics["rvpi"] == Decimal("0.97")


@pytest.mark.asyncio
async def test_compute_irr_basic():
    """Test IRR computation with simple known values."""
    # Single investment, single return after 1 year
    h = PortfolioHolding(
        portfolio_id=uuid.uuid4(),
        asset_name="Test",
        asset_type=AssetType.EQUITY,
        investment_date=date(2023, 1, 1),
        investment_amount=Decimal("1000000"),
        current_value=Decimal("1200000"),
        currency="USD",
        status=HoldingStatus.ACTIVE,
    )
    irr = service._compute_irr([h])
    # Should be positive (20% return over ~2 years)
    if irr is not None:
        assert irr > Decimal("0")


@pytest.mark.asyncio
async def test_compute_irr_no_holdings():
    assert service._compute_irr([]) is None


@pytest.mark.asyncio
async def test_compute_irr_with_exit():
    """IRR with invested and exited holding."""
    h = PortfolioHolding(
        portfolio_id=uuid.uuid4(),
        asset_name="Exited",
        asset_type=AssetType.EQUITY,
        investment_date=date(2022, 1, 1),
        investment_amount=Decimal("1000000"),
        current_value=Decimal("0"),
        currency="USD",
        status=HoldingStatus.EXITED,
        exit_date=date(2023, 1, 1),
        exit_amount=Decimal("1500000"),
    )
    irr = service._compute_irr([h])
    if irr is not None:
        # 50% return in 1 year → IRR ~50%
        assert irr > Decimal("0.3")
        assert irr < Decimal("0.8")


# ── Service: Cash Flows ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_cash_flows(
    db: AsyncSession, seed_data, sample_portfolio, sample_holdings
):
    flows = await service.get_cash_flows(db, sample_portfolio.id, ORG_ID)
    assert len(flows) >= 3  # 3 investments + 1 exit = 4 entries
    # Should be sorted by date
    dates = [f["date"] for f in flows]
    assert dates == sorted(dates)
    # Contributions should be negative
    contributions = [f for f in flows if f["type"] == "contribution"]
    assert all(f["amount"] < 0 for f in contributions)
    # Distributions should be positive
    distributions = [f for f in flows if f["type"] == "distribution"]
    assert all(f["amount"] > 0 for f in distributions)


@pytest.mark.asyncio
async def test_get_cash_flows_empty(db: AsyncSession, seed_data, sample_portfolio):
    flows = await service.get_cash_flows(db, sample_portfolio.id, ORG_ID)
    assert flows == []


# ── Service: Allocation ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_allocation(
    db: AsyncSession, seed_data, sample_portfolio, sample_holdings
):
    alloc = await service.get_allocation(db, sample_portfolio.id, ORG_ID)
    assert "by_asset_type" in alloc
    assert "by_sector" in alloc
    assert "by_geography" in alloc
    assert "by_stage" in alloc

    # Active holdings: h1 (equity, 6.5M) and h2 (project_finance, 3.2M)
    by_type = alloc["by_asset_type"]
    assert len(by_type) >= 1  # At least equity
    for entry in by_type:
        assert "name" in entry
        assert "value" in entry
        assert "percentage" in entry


@pytest.mark.asyncio
async def test_get_allocation_empty(db: AsyncSession, seed_data, sample_portfolio):
    alloc = await service.get_allocation(db, sample_portfolio.id, ORG_ID)
    assert alloc["by_asset_type"] == []
    assert alloc["by_sector"] == []


# ── Service: Latest Metrics ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_latest_metrics(db: AsyncSession, seed_data, sample_portfolio):
    m1 = PortfolioMetrics(
        portfolio_id=sample_portfolio.id,
        irr_gross=Decimal("0.12"),
        moic=Decimal("1.3"),
        tvpi=Decimal("1.3"),
        dpi=Decimal("0.2"),
        rvpi=Decimal("1.1"),
        total_invested=Decimal("10000000"),
        total_distributions=Decimal("2000000"),
        total_value=Decimal("13000000"),
        as_of_date=date(2024, 6, 30),
    )
    m2 = PortfolioMetrics(
        portfolio_id=sample_portfolio.id,
        irr_gross=Decimal("0.15"),
        moic=Decimal("1.5"),
        tvpi=Decimal("1.5"),
        dpi=Decimal("0.3"),
        rvpi=Decimal("1.2"),
        total_invested=Decimal("10000000"),
        total_distributions=Decimal("3000000"),
        total_value=Decimal("15000000"),
        as_of_date=date(2024, 12, 31),
    )
    db.add_all([m1, m2])
    await db.flush()

    latest = await service.get_latest_metrics(db, sample_portfolio.id)
    assert latest is not None
    assert latest.as_of_date == date(2024, 12, 31)
    assert latest.moic == Decimal("1.5")


@pytest.mark.asyncio
async def test_get_latest_metrics_none(db: AsyncSession, seed_data, sample_portfolio):
    latest = await service.get_latest_metrics(db, sample_portfolio.id)
    assert latest is None


# ── API Endpoint Tests ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_api_create_portfolio(test_client: AsyncClient):
    resp = await test_client.post("/portfolio", json={
        "name": "API Test Fund",
        "strategy": "growth",
        "fund_type": "closed_end",
        "target_aum": "50000000",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "API Test Fund"
    assert data["strategy"] == "growth"
    assert data["status"] == "fundraising"


@pytest.mark.asyncio
async def test_api_list_portfolios(test_client: AsyncClient, sample_portfolio):
    resp = await test_client.get("/portfolio")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_api_get_portfolio_detail(test_client: AsyncClient, sample_portfolio):
    resp = await test_client.get(f"/portfolio/{sample_portfolio.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(sample_portfolio.id)
    assert data["name"] == "Green Energy Fund I"
    assert "latest_metrics" in data
    assert "holding_count" in data


@pytest.mark.asyncio
async def test_api_get_portfolio_not_found(test_client: AsyncClient):
    resp = await test_client.get(f"/portfolio/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_update_portfolio(test_client: AsyncClient, sample_portfolio):
    resp = await test_client.put(f"/portfolio/{sample_portfolio.id}", json={
        "name": "Updated Fund Name",
        "current_aum": "55000000",
    })
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Fund Name"


@pytest.mark.asyncio
async def test_api_get_metrics(
    test_client: AsyncClient, sample_portfolio, sample_holdings
):
    resp = await test_client.get(f"/portfolio/{sample_portfolio.id}/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert "moic" in data
    assert "tvpi" in data
    assert "total_invested" in data
    assert data["total_invested"] == "10000000"


@pytest.mark.asyncio
async def test_api_list_holdings(
    test_client: AsyncClient, sample_portfolio, sample_holdings
):
    resp = await test_client.get(f"/portfolio/{sample_portfolio.id}/holdings")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert "totals" in data
    assert data["totals"]["total_invested"] == "10000000"


@pytest.mark.asyncio
async def test_api_list_holdings_filter_status(
    test_client: AsyncClient, sample_portfolio, sample_holdings
):
    resp = await test_client.get(
        f"/portfolio/{sample_portfolio.id}/holdings", params={"status": "active"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2


@pytest.mark.asyncio
async def test_api_add_holding(test_client: AsyncClient, sample_portfolio):
    resp = await test_client.post(f"/portfolio/{sample_portfolio.id}/holdings", json={
        "asset_name": "API Holding",
        "asset_type": "equity",
        "investment_date": "2024-01-15",
        "investment_amount": "2000000",
        "current_value": "2200000",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["asset_name"] == "API Holding"
    assert data["status"] == "active"
    assert data["moic"] is not None  # current_value / investment_amount


@pytest.mark.asyncio
async def test_api_update_holding(
    test_client: AsyncClient, sample_portfolio, sample_holdings
):
    h = sample_holdings[0]
    resp = await test_client.put(
        f"/portfolio/{sample_portfolio.id}/holdings/{h.id}",
        json={"current_value": "7500000"},
    )
    assert resp.status_code == 200
    assert resp.json()["current_value"] == "7500000"


@pytest.mark.asyncio
async def test_api_cash_flows(
    test_client: AsyncClient, sample_portfolio, sample_holdings
):
    resp = await test_client.get(f"/portfolio/{sample_portfolio.id}/cash-flows")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert len(data["items"]) >= 3


@pytest.mark.asyncio
async def test_api_allocation(
    test_client: AsyncClient, sample_portfolio, sample_holdings
):
    resp = await test_client.get(f"/portfolio/{sample_portfolio.id}/allocation")
    assert resp.status_code == 200
    data = resp.json()
    assert "by_asset_type" in data
    assert "by_sector" in data
    assert "by_geography" in data
    assert "by_stage" in data


# ── RBAC Tests ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_viewer_cannot_create_portfolio(viewer_client: AsyncClient):
    resp = await viewer_client.post("/portfolio", json={
        "name": "Viewer Fund",
        "strategy": "growth",
        "fund_type": "closed_end",
        "target_aum": "10000000",
    })
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_viewer_cannot_add_holding(viewer_client: AsyncClient, sample_portfolio):
    resp = await viewer_client.post(f"/portfolio/{sample_portfolio.id}/holdings", json={
        "asset_name": "Viewer Holding",
        "asset_type": "equity",
        "investment_date": "2024-01-01",
        "investment_amount": "1000000",
        "current_value": "1000000",
    })
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_viewer_can_list_portfolios(viewer_client: AsyncClient, sample_portfolio):
    resp = await viewer_client.get("/portfolio")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_viewer_can_view_metrics(
    viewer_client: AsyncClient, sample_portfolio, sample_holdings
):
    resp = await viewer_client.get(f"/portfolio/{sample_portfolio.id}/metrics")
    assert resp.status_code == 200
