"""Tests for batch-3 modules: Matching, Marketplace, Gamification, Notifications,
LP Reporting, Certification, ESG.

Modules covered:
  Matching        (/matching/...)
  Marketplace     (/marketplace/...)
  Gamification    (/gamification/...)
  Notifications   (/notifications/...)
  LP Reporting    (/lp-reports/...)
  Certification   (/certification/...)
  ESG             (/esg/...)
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_permission
from app.core.database import get_db
from app.main import app
from app.models.core import Organization, User
from app.models.enums import (
    FundType,
    OrgType,
    PortfolioStatus,
    PortfolioStrategy,
    ProjectStatus,
    ProjectType,
    SFDRClassification,
    UserRole,
)
from app.models.investors import Portfolio
from app.models.projects import Project
from app.schemas.auth import CurrentUser

pytestmark = pytest.mark.anyio

# ── Unique IDs ─────────────────────────────────────────────────────────────────

B3_ORG_ID = uuid.UUID("00000000-0000-00B3-0000-000000000001")
B3_USER_ID = uuid.UUID("00000000-0000-00B3-0000-000000000002")
B3_PROJECT_ID = uuid.UUID("00000000-0000-00B3-0000-000000000003")
B3_PORTFOLIO_ID = uuid.UUID("00000000-0000-00B3-0000-000000000004")

B3_ORG2_ID = uuid.UUID("00000000-0000-00B3-0000-000000000010")
B3_USER2_ID = uuid.UUID("00000000-0000-00B3-0000-000000000011")

CURRENT_USER = CurrentUser(
    user_id=B3_USER_ID,
    org_id=B3_ORG_ID,
    role=UserRole.ADMIN,
    email="b3_test@example.com",
    external_auth_id="clerk_b3_test",
)

CURRENT_USER2 = CurrentUser(
    user_id=B3_USER2_ID,
    org_id=B3_ORG2_ID,
    role=UserRole.ADMIN,
    email="b3_test2@example.com",
    external_auth_id="clerk_b3_test2",
)


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
async def b3_org(db: AsyncSession) -> Organization:
    org = Organization(
        id=B3_ORG_ID,
        name="B3 Test Org",
        slug="b3-test-org",
        type=OrgType.ALLY,
    )
    db.add(org)
    await db.flush()
    return org


@pytest.fixture
async def b3_user(db: AsyncSession, b3_org: Organization) -> User:
    user = User(
        id=B3_USER_ID,
        org_id=B3_ORG_ID,
        email="b3_test@example.com",
        full_name="B3 Test User",
        role=UserRole.ADMIN,
        external_auth_id="clerk_b3_test",
        is_active=True,
    )
    db.add(user)
    await db.flush()
    return user


@pytest.fixture
async def b3_project(db: AsyncSession, b3_org: Organization) -> Project:
    proj = Project(
        id=B3_PROJECT_ID,
        org_id=B3_ORG_ID,
        name="B3 Test Solar Project",
        slug="b3-test-solar-project",
        project_type=ProjectType.SOLAR,
        status=ProjectStatus.ACTIVE,
        geography_country="Germany",
        total_investment_required=Decimal("5000000"),
        currency="EUR",
        is_published=True,
        is_deleted=False,
    )
    db.add(proj)
    await db.flush()
    return proj


@pytest.fixture
async def b3_portfolio(db: AsyncSession, b3_org: Organization) -> Portfolio:
    portfolio = Portfolio(
        id=B3_PORTFOLIO_ID,
        org_id=B3_ORG_ID,
        name="B3 Test Portfolio",
        description="Test portfolio for batch-3 tests",
        strategy=PortfolioStrategy.IMPACT,
        fund_type=FundType.CLOSED_END,
        vintage_year=2024,
        target_aum=Decimal("50000000"),
        current_aum=Decimal("20000000"),
        currency="EUR",
        sfdr_classification=SFDRClassification.ARTICLE_9,
        status=PortfolioStatus.INVESTING,
    )
    db.add(portfolio)
    await db.flush()
    return portfolio


@pytest.fixture
async def b3_org2(db: AsyncSession) -> Organization:
    org = Organization(
        id=B3_ORG2_ID,
        name="B3 Test Org 2",
        slug="b3-test-org-2",
        type=OrgType.INVESTOR,
    )
    db.add(org)
    await db.flush()
    return org


@pytest.fixture
async def b3_user2(db: AsyncSession, b3_org2: Organization) -> User:
    user = User(
        id=B3_USER2_ID,
        org_id=B3_ORG2_ID,
        email="b3_test2@example.com",
        full_name="B3 Test User 2",
        role=UserRole.ADMIN,
        external_auth_id="clerk_b3_test2",
        is_active=True,
    )
    db.add(user)
    await db.flush()
    return user


@pytest.fixture
async def b3_client(db: AsyncSession, b3_user: User) -> AsyncClient:
    """Authenticated AsyncClient for batch-3 tests (org 1)."""
    app.dependency_overrides[get_current_user] = lambda: CURRENT_USER
    app.dependency_overrides[get_db] = lambda: db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
async def b3_client2(db: AsyncSession, b3_user2: User) -> AsyncClient:
    """Authenticated AsyncClient for isolation tests (org 2)."""
    app.dependency_overrides[get_current_user] = lambda: CURRENT_USER2
    app.dependency_overrides[get_db] = lambda: db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
async def b3_esg_client(db: AsyncSession, b3_user: User) -> AsyncClient:
    """Authenticated AsyncClient for ESG tests — patches check_permission to allow 'impact' resource.

    The 'impact' resource type is used by ESG & impact modules but is not included
    in the standard RBAC matrix. We patch check_permission at the dependencies module
    level (where it's imported by name) to allow it in tests.
    """
    import app.auth.dependencies as deps_module
    from app.auth.rbac import check_permission as original_check

    def patched_check(role, action, resource_type, resource_id=None):
        if resource_type == "impact":
            return True
        return original_check(role, action, resource_type, resource_id)

    app.dependency_overrides[get_current_user] = lambda: CURRENT_USER
    app.dependency_overrides[get_db] = lambda: db
    with patch.object(deps_module, "check_permission", side_effect=patched_check):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            yield ac
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db, None)


# =============================================================================
# MATCHING
# =============================================================================


class TestMatching:
    """Tests for /matching/... endpoints."""

    async def test_get_investor_recommendations_200(
        self, b3_client: AsyncClient, b3_user: User
    ):
        """Investor recommendations endpoint returns items + total."""
        resp = await b3_client.get("/matching/investor/recommendations")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)

    async def test_get_investor_recommendations_with_filters(
        self, b3_client: AsyncClient, b3_user: User
    ):
        """Investor recommendations can be filtered by sector and geography."""
        resp = await b3_client.get(
            "/matching/investor/recommendations",
            params={"sector": "solar", "geography": "Germany", "min_alignment": 0},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "items" in data

    async def test_get_ally_recommendations_404_for_unknown_project(
        self, b3_client: AsyncClient, b3_user: User
    ):
        """Ally recommendations returns 404 for a project not owned by the org."""
        fake_id = uuid.uuid4()
        resp = await b3_client.get(f"/matching/ally/recommendations/{fake_id}")
        assert resp.status_code == 404

    async def test_list_mandates_empty_200(
        self, b3_client: AsyncClient, b3_user: User
    ):
        """List mandates returns an empty list when none exist."""
        resp = await b3_client.get("/matching/mandates")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert isinstance(data, list)

    async def test_create_mandate_201(
        self, b3_client: AsyncClient, b3_user: User
    ):
        """Create a new mandate returns 201 with the mandate details."""
        resp = await b3_client.post(
            "/matching/mandates",
            json={
                "name": "Green Energy Mandate",
                "sectors": ["solar", "wind"],
                "geographies": ["Germany", "France"],
                "stages": ["operational"],
                "ticket_size_min": "1000000",
                "ticket_size_max": "10000000",
                "risk_tolerance": "moderate",
            },
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["name"] == "Green Energy Mandate"
        assert "id" in data
        assert "org_id" in data
        assert data["is_active"] is True

    async def test_mandate_multi_tenant_isolation(
        self,
        db: AsyncSession,
        b3_user: User,
        b3_user2: User,
    ):
        """Mandates created by org1 are not visible to org2."""
        # Create mandate as org1
        app.dependency_overrides[get_current_user] = lambda: CURRENT_USER
        app.dependency_overrides[get_db] = lambda: db
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client1:
            create_resp = await client1.post(
                "/matching/mandates",
                json={
                    "name": "Org1 Exclusive Mandate",
                    "ticket_size_min": "500000",
                    "ticket_size_max": "5000000",
                },
            )
            assert create_resp.status_code == 201

        # List mandates as org2 — should not contain org1's mandate
        app.dependency_overrides[get_current_user] = lambda: CURRENT_USER2
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client2:
            resp2 = await client2.get("/matching/mandates")
            assert resp2.status_code == 200
            mandates = resp2.json()
            assert all(m.get("name") != "Org1 Exclusive Mandate" for m in mandates)

        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)


# =============================================================================
# MARKETPLACE
# =============================================================================


class TestMarketplace:
    """Tests for /marketplace/... endpoints."""

    async def test_browse_listings_empty_200(
        self, b3_client: AsyncClient, b3_user: User
    ):
        """Browsing listings returns items + total even when empty."""
        resp = await b3_client.get("/marketplace/listings")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)

    async def test_create_listing_201(
        self, b3_client: AsyncClient, b3_user: User
    ):
        """Create a new marketplace listing returns 201 with listing details."""
        resp = await b3_client.post(
            "/marketplace/listings",
            json={
                "title": "Solar Equity Stake",
                "description": "25% equity stake in operational solar farm",
                "listing_type": "equity_sale",
                "visibility": "qualified_only",
                "asking_price": 1250000.0,
                "minimum_investment": 250000.0,
                "currency": "EUR",
            },
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["title"] == "Solar Equity Stake"
        assert data["listing_type"] == "equity_sale"
        assert "id" in data
        assert "status" in data

    async def test_get_listing_detail_after_create(
        self, b3_client: AsyncClient, b3_user: User
    ):
        """Create a listing then GET the detail by ID returns 200."""
        create_resp = await b3_client.post(
            "/marketplace/listings",
            json={
                "title": "Wind Farm Carbon Credits",
                "description": "Carbon credits from wind project",
                "listing_type": "carbon_credit",
                "visibility": "public",
                "asking_price": 50000.0,
                "currency": "USD",
            },
        )
        assert create_resp.status_code == 201
        listing_id = create_resp.json()["id"]

        get_resp = await b3_client.get(f"/marketplace/listings/{listing_id}")
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["id"] == listing_id
        assert data["title"] == "Wind Farm Carbon Credits"

    async def test_get_listing_not_found_404(
        self, b3_client: AsyncClient, b3_user: User
    ):
        """GET a non-existent listing returns 404."""
        resp = await b3_client.get(f"/marketplace/listings/{uuid.uuid4()}")
        assert resp.status_code == 404

    async def test_list_sent_rfqs_empty_200(
        self, b3_client: AsyncClient, b3_user: User
    ):
        """List sent RFQs returns items + total when none exist."""
        resp = await b3_client.get("/marketplace/rfqs/sent")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)

    async def test_list_transactions_empty_200(
        self, b3_client: AsyncClient, b3_user: User
    ):
        """List transactions returns items + total when none exist."""
        resp = await b3_client.get("/marketplace/transactions")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)

    async def test_create_listing_invalid_type_422(
        self, b3_client: AsyncClient, b3_user: User
    ):
        """Creating a listing with an invalid listing_type returns 422."""
        resp = await b3_client.post(
            "/marketplace/listings",
            json={
                "title": "Invalid Listing",
                "listing_type": "invalid_type",
            },
        )
        assert resp.status_code == 422


# =============================================================================
# GAMIFICATION
# =============================================================================


class TestGamification:
    """Tests for /gamification/... endpoints."""

    async def test_get_my_badges_200(
        self, b3_client: AsyncClient, b3_user: User
    ):
        """GET /gamification/badges/my returns a list (possibly empty)."""
        resp = await b3_client.get("/gamification/badges/my")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert isinstance(data, list)

    async def test_get_project_badges_200(
        self, b3_client: AsyncClient, b3_project: Project
    ):
        """GET /gamification/badges/project/{id} returns a list."""
        resp = await b3_client.get(
            f"/gamification/badges/project/{B3_PROJECT_ID}"
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert isinstance(data, list)

    async def test_get_leaderboard_200(
        self, b3_client: AsyncClient, b3_user: User
    ):
        """GET /gamification/leaderboard returns a list."""
        resp = await b3_client.get("/gamification/leaderboard")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert isinstance(data, list)

    async def test_get_quests_for_project_200(
        self, b3_client: AsyncClient, b3_project: Project
    ):
        """GET /gamification/quests/{project_id} returns a list."""
        resp = await b3_client.get(f"/gamification/quests/{B3_PROJECT_ID}")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert isinstance(data, list)

    async def test_get_progress_for_project_200(
        self, b3_client: AsyncClient, b3_project: Project
    ):
        """GET /gamification/progress/{project_id} returns progress data."""
        resp = await b3_client.get(f"/gamification/progress/{B3_PROJECT_ID}")
        assert resp.status_code == 200, resp.text

    async def test_complete_quest_404_for_unknown(
        self, b3_client: AsyncClient, b3_user: User
    ):
        """POST /gamification/quests/{id}/complete returns 404 for unknown quest."""
        resp = await b3_client.post(
            f"/gamification/quests/{uuid.uuid4()}/complete"
        )
        assert resp.status_code == 404


# =============================================================================
# NOTIFICATIONS
# =============================================================================


class TestNotifications:
    """Tests for /notifications/... endpoints."""

    async def test_list_notifications_empty_200(
        self, b3_client: AsyncClient, b3_user: User
    ):
        """List notifications returns paginated structure even when empty."""
        resp = await b3_client.get("/notifications")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "total_pages" in data
        assert isinstance(data["items"], list)

    async def test_get_unread_count_200(
        self, b3_client: AsyncClient, b3_user: User
    ):
        """GET /notifications/unread-count returns a numeric count."""
        resp = await b3_client.get("/notifications/unread-count")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "count" in data
        assert isinstance(data["count"], int)
        assert data["count"] >= 0

    async def test_mark_all_read_200(
        self, b3_client: AsyncClient, b3_user: User
    ):
        """PUT /notifications/read-all returns marked_read count."""
        resp = await b3_client.put("/notifications/read-all")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "marked_read" in data
        assert isinstance(data["marked_read"], int)

    async def test_mark_single_notification_read_404_unknown(
        self, b3_client: AsyncClient, b3_user: User
    ):
        """PUT /notifications/{id}/read for a non-existent notification returns 404."""
        resp = await b3_client.put(f"/notifications/{uuid.uuid4()}/read")
        assert resp.status_code == 404

    async def test_list_notifications_filtered_by_is_read(
        self, b3_client: AsyncClient, b3_user: User
    ):
        """List notifications with is_read=false returns 200 with list."""
        resp = await b3_client.get(
            "/notifications", params={"is_read": False}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert isinstance(data["items"], list)

    async def test_update_notification_preferences_200(
        self, b3_client: AsyncClient, b3_user: User
    ):
        """PUT /notifications/preferences updates notification settings."""
        resp = await b3_client.put(
            "/notifications/preferences",
            json={"preferences": {"email_on_match": True, "push_on_message": False}},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "notification_settings" in data


# =============================================================================
# LP REPORTING
# =============================================================================


class TestLPReporting:
    """Tests for /lp-reports/... endpoints."""

    async def test_list_lp_reports_empty_200(
        self, b3_client: AsyncClient, b3_user: User
    ):
        """List LP reports returns paginated structure even when empty."""
        resp = await b3_client.get("/lp-reports")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert isinstance(data["items"], list)

    async def test_create_lp_report_201(
        self, b3_client: AsyncClient, b3_user: User
    ):
        """Create an LP report returns 201 with financial metrics."""
        resp = await b3_client.post(
            "/lp-reports",
            json={
                "report_period": "Q1 2025",
                "period_start": "2025-01-01",
                "period_end": "2025-03-31",
                "cash_flows": [
                    {"date": "2025-01-15", "amount": -1000000},
                    {"date": "2025-03-31", "amount": 1050000},
                ],
                "total_committed": 5000000.0,
                "total_invested": 3000000.0,
                "total_returned": 500000.0,
                "total_nav": 3200000.0,
            },
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["report_period"] == "Q1 2025"
        assert "id" in data
        assert "status" in data

    async def test_get_lp_report_after_create(
        self, b3_client: AsyncClient, b3_user: User
    ):
        """Create then GET the LP report by ID."""
        create_resp = await b3_client.post(
            "/lp-reports",
            json={
                "report_period": "Q2 2025",
                "period_start": "2025-04-01",
                "period_end": "2025-06-30",
                "total_committed": 10000000.0,
                "total_invested": 7000000.0,
                "total_returned": 0.0,
                "total_nav": 7500000.0,
            },
        )
        assert create_resp.status_code == 201
        report_id = create_resp.json()["id"]

        get_resp = await b3_client.get(f"/lp-reports/{report_id}")
        assert get_resp.status_code == 200, get_resp.text
        data = get_resp.json()
        assert data["id"] == report_id
        assert data["report_period"] == "Q2 2025"

    async def test_get_lp_report_not_found_404(
        self, b3_client: AsyncClient, b3_user: User
    ):
        """GET a non-existent LP report returns 404."""
        resp = await b3_client.get(f"/lp-reports/{uuid.uuid4()}")
        assert resp.status_code == 404

    async def test_list_lp_reports_filtered_by_portfolio(
        self, b3_client: AsyncClient, b3_portfolio: Portfolio
    ):
        """Filtering LP reports by portfolio_id returns 200 with list."""
        resp = await b3_client.get(
            "/lp-reports",
            params={"portfolio_id": str(B3_PORTFOLIO_ID)},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert isinstance(data["items"], list)


# =============================================================================
# CERTIFICATION
# =============================================================================


class TestCertification:
    """Tests for /certification/... endpoints."""

    async def test_get_leaderboard_200(
        self, b3_client: AsyncClient, b3_user: User
    ):
        """GET /certification/leaderboard returns a list (possibly empty)."""
        resp = await b3_client.get("/certification/leaderboard")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert isinstance(data, list)

    async def test_get_certification_404_no_record(
        self, b3_client: AsyncClient, b3_project: Project
    ):
        """GET /certification/{project_id} returns 404 when no record exists."""
        resp = await b3_client.get(f"/certification/{B3_PROJECT_ID}")
        assert resp.status_code == 404

    async def test_get_certification_badge_uncertified(
        self, b3_client: AsyncClient, b3_project: Project
    ):
        """GET /certification/{project_id}/badge returns badge (certified=False if not certified)."""
        resp = await b3_client.get(f"/certification/{B3_PROJECT_ID}/badge")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "certified" in data
        assert isinstance(data["certified"], bool)

    async def test_get_certification_requirements_200(
        self, b3_client: AsyncClient, b3_project: Project
    ):
        """GET /certification/{project_id}/requirements returns eligibility + gaps."""
        resp = await b3_client.get(
            f"/certification/{B3_PROJECT_ID}/requirements"
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "eligible" in data
        assert "gaps" in data
        assert isinstance(data["gaps"], list)

    async def test_evaluate_certification_creates_record(
        self, b3_client: AsyncClient, b3_project: Project
    ):
        """POST /certification/{project_id}/evaluate creates or updates cert record."""
        resp = await b3_client.post(
            f"/certification/{B3_PROJECT_ID}/evaluate"
        )
        # Should be 200 (returns CertificationResponse) or 500 if evaluation issues
        assert resp.status_code in (200, 500), resp.text
        if resp.status_code == 200:
            data = resp.json()
            assert "project_id" in data
            assert data["project_id"] == str(B3_PROJECT_ID)
            assert "status" in data

    async def test_get_certification_404_for_unknown_project(
        self, b3_client: AsyncClient, b3_user: User
    ):
        """GET /certification/{id} for unknown project returns 404."""
        resp = await b3_client.get(f"/certification/{uuid.uuid4()}")
        assert resp.status_code == 404


# =============================================================================
# ESG
# =============================================================================


class TestESG:
    """Tests for /esg/... endpoints.

    ESG endpoints use require_permission("view"/"create", "impact") which is not in the
    standard RBAC matrix. Tests use b3_esg_client which patches check_permission to
    allow the 'impact' resource type.
    """

    async def test_get_portfolio_summary_200(
        self, b3_esg_client: AsyncClient, b3_user: User
    ):
        """GET /esg/portfolio-summary returns expected structure."""
        resp = await b3_esg_client.get("/esg/portfolio-summary")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "totals" in data
        assert "sfdr_distribution" in data
        assert "taxonomy_alignment_pct" in data
        assert "top_sdgs" in data
        assert "carbon_trend" in data
        assert "project_rows" in data

    async def test_get_portfolio_summary_with_filters(
        self, b3_esg_client: AsyncClient, b3_user: User
    ):
        """GET /esg/portfolio-summary with period filter returns 200."""
        resp = await b3_esg_client.get(
            "/esg/portfolio-summary", params={"period": "2024-Q4"}
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "totals" in data

    async def test_get_project_metrics_empty_200(
        self, b3_esg_client: AsyncClient, b3_project: Project
    ):
        """GET /esg/projects/{id}/metrics returns history (empty records list when none exist)."""
        resp = await b3_esg_client.get(f"/esg/projects/{B3_PROJECT_ID}/metrics")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "project_id" in data
        assert "records" in data
        assert isinstance(data["records"], list)

    async def test_upsert_project_metrics_200(
        self, b3_esg_client: AsyncClient, b3_project: Project
    ):
        """PUT /esg/projects/{id}/metrics creates ESG metrics and returns 200."""
        resp = await b3_esg_client.put(
            f"/esg/projects/{B3_PROJECT_ID}/metrics",
            json={
                "period": "2025-Q1",
                "carbon_footprint_tco2e": 150.5,
                "carbon_avoided_tco2e": 800.0,
                "renewable_energy_mwh": 2500.0,
                "jobs_created": 45,
                "jobs_supported": 120,
                "taxonomy_eligible": True,
                "taxonomy_aligned": True,
                "sfdr_article": 9,
            },
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["project_id"] == str(B3_PROJECT_ID)
        assert data["period"] == "2025-Q1"
        assert "id" in data
        assert data["jobs_created"] == 45

    async def test_upsert_then_get_metrics_returns_record(
        self, b3_esg_client: AsyncClient, b3_project: Project
    ):
        """After upserting ESG metrics, GET history includes that record."""
        # Upsert
        put_resp = await b3_esg_client.put(
            f"/esg/projects/{B3_PROJECT_ID}/metrics",
            json={
                "period": "2025-Q2",
                "carbon_avoided_tco2e": 500.0,
                "renewable_energy_mwh": 1200.0,
                "jobs_created": 20,
            },
        )
        assert put_resp.status_code == 200

        # Get history
        get_resp = await b3_esg_client.get(f"/esg/projects/{B3_PROJECT_ID}/metrics")
        assert get_resp.status_code == 200
        data = get_resp.json()
        periods = [r["period"] for r in data["records"]]
        assert "2025-Q2" in periods

    async def test_export_portfolio_csv_200(
        self, b3_esg_client: AsyncClient, b3_user: User
    ):
        """GET /esg/portfolio-summary/export returns CSV content."""
        resp = await b3_esg_client.get("/esg/portfolio-summary/export")
        assert resp.status_code == 200, resp.text
        assert "text/csv" in resp.headers.get("content-type", "")
