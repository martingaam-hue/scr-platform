"""Tests for core AI modules: Risk, Legal, Deal Intelligence, Carbon Credits, Valuation.

Modules covered:
  Risk Analysis       (/risk/...)
  Legal Automation    (/legal/...)
  Deal Intelligence   (/deals/...)
  Carbon Credits      (/carbon/...)
  Valuation Analysis  (/valuations/...)
"""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db, get_readonly_session
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

# ── Unique IDs per module section ─────────────────────────────────────────────

CM_ORG_ID = uuid.UUID("00000000-0000-00CE-0000-000000000001")
CM_USER_ID = uuid.UUID("00000000-0000-00CE-0000-000000000002")
CM_PROJECT_ID = uuid.UUID("00000000-0000-00CE-0000-000000000003")
CM_PORTFOLIO_ID = uuid.UUID("00000000-0000-00CE-0000-000000000004")

# Second org for isolation checks
CM_ORG2_ID = uuid.UUID("00000000-0000-00CE-0000-000000000010")
CM_USER2_ID = uuid.UUID("00000000-0000-00CE-0000-000000000011")

CURRENT_USER = CurrentUser(
    user_id=CM_USER_ID,
    org_id=CM_ORG_ID,
    role=UserRole.ADMIN,
    email="cm_test@example.com",
    external_auth_id="clerk_cm_test",
)

CURRENT_USER2 = CurrentUser(
    user_id=CM_USER2_ID,
    org_id=CM_ORG2_ID,
    role=UserRole.ADMIN,
    email="cm_test2@example.com",
    external_auth_id="clerk_cm_test2",
)


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
async def cm_org(db: AsyncSession) -> Organization:
    org = Organization(
        id=CM_ORG_ID,
        name="CM Test Org",
        slug="cm-test-org",
        type=OrgType.ALLY,
    )
    db.add(org)
    await db.flush()
    return org


@pytest.fixture
async def cm_user(db: AsyncSession, cm_org: Organization) -> User:
    user = User(
        id=CM_USER_ID,
        org_id=CM_ORG_ID,
        email="cm_test@example.com",
        full_name="CM Test User",
        role=UserRole.ADMIN,
        external_auth_id="clerk_cm_test",
        is_active=True,
    )
    db.add(user)
    await db.flush()
    return user


@pytest.fixture
async def cm_project(db: AsyncSession, cm_org: Organization) -> Project:
    proj = Project(
        id=CM_PROJECT_ID,
        org_id=CM_ORG_ID,
        name="CM Test Solar Project",
        slug="cm-test-solar-project",
        project_type=ProjectType.SOLAR,
        status=ProjectStatus.ACTIVE,
        geography_country="Germany",
        total_investment_required=Decimal("10000000"),
        currency="EUR",
        is_published=True,
        is_deleted=False,
    )
    db.add(proj)
    await db.flush()
    return proj


@pytest.fixture
async def cm_portfolio(db: AsyncSession, cm_org: Organization) -> Portfolio:
    portfolio = Portfolio(
        id=CM_PORTFOLIO_ID,
        org_id=CM_ORG_ID,
        name="CM Test Portfolio",
        description="Test portfolio for core module tests",
        strategy=PortfolioStrategy.IMPACT,
        fund_type=FundType.CLOSED_END,
        vintage_year=2024,
        target_aum=Decimal("100000000"),
        current_aum=Decimal("50000000"),
        currency="EUR",
        sfdr_classification=SFDRClassification.ARTICLE_9,
        status=PortfolioStatus.INVESTING,
    )
    db.add(portfolio)
    await db.flush()
    return portfolio


@pytest.fixture
async def cm_org2(db: AsyncSession) -> Organization:
    org = Organization(
        id=CM_ORG2_ID,
        name="CM Test Org 2",
        slug="cm-test-org-2",
        type=OrgType.INVESTOR,
    )
    db.add(org)
    await db.flush()
    return org


@pytest.fixture
async def cm_user2(db: AsyncSession, cm_org2: Organization) -> User:
    user = User(
        id=CM_USER2_ID,
        org_id=CM_ORG2_ID,
        email="cm_test2@example.com",
        full_name="CM Test User 2",
        role=UserRole.ADMIN,
        external_auth_id="clerk_cm_test2",
        is_active=True,
    )
    db.add(user)
    await db.flush()
    return user


@pytest.fixture
async def cm_client(db: AsyncSession, cm_user: User) -> AsyncClient:
    """Authenticated AsyncClient for core module tests (org 1)."""
    app.dependency_overrides[get_current_user] = lambda: CURRENT_USER
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_readonly_session] = lambda: db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_readonly_session, None)


@pytest.fixture
async def cm_client2(db: AsyncSession, cm_user2: User) -> AsyncClient:
    """Authenticated AsyncClient for isolation tests (org 2)."""
    app.dependency_overrides[get_current_user] = lambda: CURRENT_USER2
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_readonly_session] = lambda: db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_readonly_session, None)


# =============================================================================
# RISK ANALYSIS
# =============================================================================


class TestRiskAnalysis:
    """Tests for /risk/... endpoints."""

    async def test_create_risk_assessment_201(
        self, cm_client: AsyncClient, cm_project: Project
    ):
        """Create a risk assessment for a project entity."""
        resp = await cm_client.post(
            "/v1/risk/assess",
            json={
                "entity_type": "project",
                "entity_id": str(CM_PROJECT_ID),
                "risk_type": "market",
                "severity": "high",
                "probability": "possible",
                "description": "Market risk due to energy price volatility",
                "mitigation": "Hedge with long-term PPAs",
                "status": "identified",
            },
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["entity_type"] == "project"
        assert data["entity_id"] == str(CM_PROJECT_ID)
        assert data["risk_type"] == "market"
        assert data["severity"] == "high"
        assert data["probability"] == "possible"
        assert data["description"] == "Market risk due to energy price volatility"
        assert "id" in data
        assert "created_at" in data

    async def test_list_risk_assessments_empty(self, cm_client: AsyncClient):
        """List assessments returns empty list when none exist."""
        resp = await cm_client.get("/v1/risk/assessments")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_list_risk_assessments_with_entity_filter(
        self, cm_client: AsyncClient, cm_project: Project
    ):
        """Create then list assessments filtered by entity_id."""
        # Create one
        create_resp = await cm_client.post(
            "/v1/risk/assess",
            json={
                "entity_type": "project",
                "entity_id": str(CM_PROJECT_ID),
                "risk_type": "regulatory",
                "severity": "medium",
                "probability": "unlikely",
                "description": "Regulatory permit risk",
            },
        )
        assert create_resp.status_code == 201

        # List filtered by entity
        list_resp = await cm_client.get(
            "/v1/risk/assessments",
            params={"entity_type": "project", "entity_id": str(CM_PROJECT_ID)},
        )
        assert list_resp.status_code == 200
        items = list_resp.json()
        assert isinstance(items, list)
        assert any(a["risk_type"] == "regulatory" for a in items)

    async def test_list_alerts_empty(self, cm_client: AsyncClient):
        """List monitoring alerts returns expected structure."""
        resp = await cm_client.get("/v1/risk/alerts")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)

    async def test_get_audit_trail(self, cm_client: AsyncClient):
        """Audit trail returns paginated structure."""
        resp = await cm_client.get("/v1/risk/audit-trail")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    async def test_risk_dashboard_not_found_for_unknown_portfolio(
        self, cm_client: AsyncClient
    ):
        """Dashboard returns 404 for a portfolio that doesn't exist."""
        fake_id = uuid.uuid4()
        resp = await cm_client.get(f"/v1/risk/dashboard/{fake_id}")
        assert resp.status_code == 404

    async def test_risk_dashboard_ok_for_existing_portfolio(
        self, cm_client: AsyncClient, cm_portfolio: Portfolio
    ):
        """Dashboard returns 200 with full structure for known portfolio."""
        resp = await cm_client.get(f"/v1/risk/dashboard/{CM_PORTFOLIO_ID}")
        assert resp.status_code == 200
        data = resp.json()
        assert "portfolio_id" in data
        assert "overall_risk_score" in data
        assert "heatmap" in data
        assert "top_risks" in data
        assert "concentration" in data

    async def test_multi_tenant_assessments_isolation(
        self,
        db: AsyncSession,
        cm_project: Project,
        cm_user: User,
        cm_user2: User,
    ):
        """Assessments from org1 are not visible to org2 (sequential clients)."""
        # Use org1 client to create an assessment
        app.dependency_overrides[get_current_user] = lambda: CURRENT_USER
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_readonly_session] = lambda: db
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client1:
            create_resp = await client1.post(
                "/v1/risk/assess",
                json={
                    "entity_type": "project",
                    "entity_id": str(CM_PROJECT_ID),
                    "risk_type": "climate",
                    "severity": "low",
                    "probability": "unlikely",
                    "description": "Climate risk for org1 only",
                },
            )
            assert create_resp.status_code == 201

        # Now use org2 client to list assessments — should NOT see org1's data
        app.dependency_overrides[get_current_user] = lambda: CURRENT_USER2
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client2:
            resp2 = await client2.get("/v1/risk/assessments")
            assert resp2.status_code == 200
            items = resp2.json()
            assert all(
                a.get("description") != "Climate risk for org1 only" for a in items
            )

        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_readonly_session, None)


# =============================================================================
# LEGAL AUTOMATION
# =============================================================================


class TestLegalAutomation:
    """Tests for /legal/... endpoints."""

    async def test_list_templates_200(self, cm_client: AsyncClient, cm_user: User):
        """Templates endpoint returns a list of system templates."""
        resp = await cm_client.get("/v1/legal/templates")
        assert resp.status_code == 200
        items = resp.json()
        assert isinstance(items, list)
        assert len(items) > 0
        first = items[0]
        assert "id" in first
        assert "name" in first
        assert "doc_type" in first

    async def test_get_template_detail_200(
        self, cm_client: AsyncClient, cm_user: User
    ):
        """Fetching an existing template by ID returns its questionnaire."""
        resp = await cm_client.get("/v1/legal/templates/nda_standard")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "nda_standard"
        assert "questionnaire" in data
        assert "sections" in data["questionnaire"]

    async def test_get_template_not_found(
        self, cm_client: AsyncClient, cm_user: User
    ):
        """Unknown template ID returns 404."""
        resp = await cm_client.get("/v1/legal/templates/does_not_exist")
        assert resp.status_code == 404

    async def test_list_jurisdictions_200(
        self, cm_client: AsyncClient, cm_user: User
    ):
        """Jurisdictions endpoint returns a list of strings."""
        resp = await cm_client.get("/v1/legal/jurisdictions")
        assert resp.status_code == 200
        items = resp.json()
        assert isinstance(items, list)
        assert len(items) > 0
        assert all(isinstance(j, str) for j in items)

    async def test_create_legal_document_201(
        self, cm_client: AsyncClient, cm_user: User
    ):
        """Create a new legal document from the NDA template."""
        resp = await cm_client.post(
            "/v1/legal/documents",
            json={
                "template_id": "nda_standard",
                "title": "Test NDA Agreement",
            },
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["title"] == "Test NDA Agreement"
        assert data["template_id"] == "nda_standard"
        assert data["doc_type"] == "nda"
        assert "id" in data
        assert "status" in data

    async def test_list_legal_documents_200(
        self, cm_client: AsyncClient, cm_user: User
    ):
        """List documents returns paginated structure."""
        resp = await cm_client.get("/v1/legal/documents")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)

    async def test_legal_review_trigger_202(
        self, cm_client: AsyncClient, cm_user: User
    ):
        """Trigger a legal review via document text returns 202 with review_id."""
        resp = await cm_client.post(
            "/v1/legal/review",
            json={
                "document_text": (
                    "This Non-Disclosure Agreement is entered into between "
                    "Party A and Party B for the purpose of discussing a "
                    "potential investment. Both parties agree to keep all "
                    "information confidential for a period of two years."
                ),
                "mode": "risk_focused",
                "jurisdiction": "England & Wales",
            },
        )
        assert resp.status_code == 202, resp.text
        data = resp.json()
        assert "review_id" in data
        assert data["status"] == "accepted"

    async def test_legal_review_missing_content_422(
        self, cm_client: AsyncClient, cm_user: User
    ):
        """Submitting a review with neither document_id nor document_text returns 422."""
        resp = await cm_client.post(
            "/v1/legal/review",
            json={
                "mode": "risk_focused",
                "jurisdiction": "England & Wales",
            },
        )
        assert resp.status_code == 422

    async def test_get_legal_document_after_create(
        self, cm_client: AsyncClient, cm_user: User
    ):
        """Create then GET the document by ID."""
        create_resp = await cm_client.post(
            "/v1/legal/documents",
            json={
                "template_id": "nda_standard",
                "title": "Fetch Me NDA",
            },
        )
        assert create_resp.status_code == 201
        doc_id = create_resp.json()["id"]

        get_resp = await cm_client.get(f"/v1/legal/documents/{doc_id}")
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["id"] == doc_id
        assert data["title"] == "Fetch Me NDA"


# =============================================================================
# DEAL INTELLIGENCE
# =============================================================================


class TestDealIntelligence:
    """Tests for /deals/... endpoints."""

    async def test_get_pipeline_200(self, cm_client: AsyncClient, cm_user: User):
        """Pipeline endpoint returns grouped deal stages."""
        resp = await cm_client.get("/v1/deals/pipeline")
        assert resp.status_code == 200
        data = resp.json()
        assert "discovered" in data
        assert "screening" in data
        assert "due_diligence" in data
        assert "negotiation" in data
        assert "passed" in data

    async def test_discover_deals_200(self, cm_client: AsyncClient, cm_user: User):
        """Discover endpoint returns items and total."""
        resp = await cm_client.get("/v1/deals/discover")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)

    async def test_discover_deals_with_filters(
        self, cm_client: AsyncClient, cm_user: User
    ):
        """Discover can be filtered by sector and geography."""
        resp = await cm_client.get(
            "/v1/deals/discover",
            params={"sector": "solar", "geography": "Germany", "score_min": 0},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data

    async def test_trigger_screening_on_own_project_202(
        self, cm_client: AsyncClient, cm_project: Project
    ):
        """Triggering screening on an existing project returns 202 with task_log_id."""
        resp = await cm_client.post(f"/v1/deals/{CM_PROJECT_ID}/screen")
        assert resp.status_code == 202, resp.text
        data = resp.json()
        assert "task_log_id" in data
        assert data["status"] == "pending"

    async def test_get_screening_report_404_before_run(
        self, cm_client: AsyncClient, cm_project: Project
    ):
        """Getting screening report for project with no completed report returns 404."""
        # Use a fresh UUID that has no screening report
        fresh_id = uuid.uuid4()
        resp = await cm_client.get(f"/v1/deals/{fresh_id}/screening")
        assert resp.status_code == 404

    async def test_batch_screen_empty_list_200(
        self, cm_client: AsyncClient, cm_user: User
    ):
        """Batch screen with empty list returns 200 with zero queued."""
        resp = await cm_client.post(
            "/v1/deals/batch-screen",
            json={"project_ids": []},
        )
        assert resp.status_code == 202, resp.text
        data = resp.json()
        assert data["queued"] == 0
        assert data["failed"] == 0
        assert data["items"] == []

    async def test_batch_screen_unknown_projects_errors(
        self, cm_client: AsyncClient, cm_user: User
    ):
        """Batch screen with unknown project IDs reports them in errors."""
        fake1 = str(uuid.uuid4())
        fake2 = str(uuid.uuid4())
        resp = await cm_client.post(
            "/v1/deals/batch-screen",
            json={"project_ids": [fake1, fake2]},
        )
        assert resp.status_code == 202
        data = resp.json()
        assert data["queued"] == 0
        assert data["failed"] == 2
        assert len(data["errors"]) == 2

    async def test_batch_screen_too_many_projects_422(
        self, cm_client: AsyncClient, cm_user: User
    ):
        """Batch screen with more than 50 projects returns 422."""
        ids = [str(uuid.uuid4()) for _ in range(51)]
        resp = await cm_client.post(
            "/v1/deals/batch-screen",
            json={"project_ids": ids},
        )
        assert resp.status_code == 422

    async def test_compare_projects_invalid_count_422(
        self, cm_client: AsyncClient, cm_user: User
    ):
        """Compare with fewer than 2 project IDs fails validation."""
        resp = await cm_client.post(
            "/v1/deals/compare",
            json={"project_ids": [str(uuid.uuid4())]},
        )
        assert resp.status_code == 422


# =============================================================================
# CARBON CREDITS
# =============================================================================


class TestCarbonCredits:
    """Tests for /carbon/... endpoints."""

    async def test_get_pricing_trends_200(
        self, cm_client: AsyncClient, cm_user: User
    ):
        """Pricing trends returns a list of data points."""
        resp = await cm_client.get("/v1/carbon/pricing-trends")
        assert resp.status_code == 200
        items = resp.json()
        assert isinstance(items, list)
        assert len(items) > 0
        first = items[0]
        assert "date" in first
        assert "vcs_price" in first
        assert "gold_standard_price" in first
        assert "eu_ets_price" in first

    async def test_get_methodologies_200(
        self, cm_client: AsyncClient, cm_user: User
    ):
        """Methodologies endpoint returns list with registry and description."""
        resp = await cm_client.get("/v1/carbon/methodologies")
        assert resp.status_code == 200
        items = resp.json()
        assert isinstance(items, list)
        assert len(items) > 0
        first = items[0]
        assert "id" in first
        assert "name" in first
        assert "registry" in first

    async def test_estimate_carbon_credits_for_project(
        self, cm_client: AsyncClient, cm_project: Project
    ):
        """Estimate carbon credits for a known project returns estimate + record."""
        resp = await cm_client.post(f"/v1/carbon/estimate/{CM_PROJECT_ID}")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "estimate" in data
        assert "credit_record" in data
        assert data["estimate"]["annual_tons_co2e"] > 0
        assert "methodology" in data["estimate"]

    async def test_estimate_carbon_credits_unknown_project_404(
        self, cm_client: AsyncClient, cm_user: User
    ):
        """Estimate for unknown project returns 404."""
        resp = await cm_client.post(f"/v1/carbon/estimate/{uuid.uuid4()}")
        assert resp.status_code == 404

    async def test_get_carbon_credit_after_estimate(
        self, cm_client: AsyncClient, cm_project: Project
    ):
        """After estimating, GET /carbon/{project_id} returns the record."""
        # First create via estimate
        est_resp = await cm_client.post(f"/v1/carbon/estimate/{CM_PROJECT_ID}")
        assert est_resp.status_code == 200

        # Now fetch the record
        get_resp = await cm_client.get(f"/v1/carbon/{CM_PROJECT_ID}")
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["project_id"] == str(CM_PROJECT_ID)
        assert "verification_status" in data
        assert "quantity_tons" in data

    async def test_get_carbon_credit_not_found_404(
        self, cm_client: AsyncClient, cm_user: User
    ):
        """GET credit record for project with no carbon credit returns 404."""
        resp = await cm_client.get(f"/v1/carbon/{uuid.uuid4()}")
        assert resp.status_code == 404

    async def test_update_carbon_credit_after_estimate(
        self, cm_client: AsyncClient, cm_project: Project
    ):
        """Update carbon credit fields after creating via estimate."""
        # Create via estimate
        est_resp = await cm_client.post(f"/v1/carbon/estimate/{CM_PROJECT_ID}")
        assert est_resp.status_code == 200

        # Update fields
        put_resp = await cm_client.put(
            f"/v1/carbon/{CM_PROJECT_ID}",
            json={
                "price_per_ton": 15.5,
                "currency": "USD",
                "serial_number": "VCS-2024-TEST-001",
            },
        )
        assert put_resp.status_code == 200, put_resp.text
        data = put_resp.json()
        assert data["price_per_ton"] == 15.5
        assert data["serial_number"] == "VCS-2024-TEST-001"


# =============================================================================
# VALUATION ANALYSIS
# =============================================================================


class TestValuationAnalysis:
    """Tests for /valuations/... endpoints."""

    async def test_list_valuations_empty_200(
        self, cm_client: AsyncClient, cm_user: User
    ):
        """List valuations returns correct structure when empty."""
        resp = await cm_client.get("/v1/valuations")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)

    async def test_create_dcf_valuation_201(
        self, cm_client: AsyncClient, cm_project: Project
    ):
        """Create a DCF valuation for a known project."""
        resp = await cm_client.post(
            "/v1/valuations",
            json={
                "project_id": str(CM_PROJECT_ID),
                "method": "dcf",
                "currency": "EUR",
                "dcf_params": {
                    "cash_flows": [1000000, 1200000, 1400000, 1600000, 1800000],
                    "discount_rate": 0.10,
                    "terminal_growth_rate": 0.02,
                    "terminal_method": "gordon",
                    "net_debt": 0.0,
                },
            },
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["method"] == "dcf"
        assert data["currency"] == "EUR"
        assert data["project_id"] == str(CM_PROJECT_ID)
        assert "id" in data
        assert "enterprise_value" in data
        assert "equity_value" in data
        assert data["status"] in ("draft", "approved")

    async def test_create_dcf_valuation_unknown_project_404(
        self, cm_client: AsyncClient, cm_user: User
    ):
        """Creating a valuation for a non-existent project returns 404."""
        resp = await cm_client.post(
            "/v1/valuations",
            json={
                "project_id": str(uuid.uuid4()),
                "method": "dcf",
                "currency": "USD",
                "dcf_params": {
                    "cash_flows": [500000, 600000],
                    "discount_rate": 0.12,
                    "terminal_growth_rate": 0.02,
                    "terminal_method": "gordon",
                },
            },
        )
        assert resp.status_code == 404

    async def test_get_valuation_by_id(
        self, cm_client: AsyncClient, cm_project: Project
    ):
        """Create then GET the valuation by ID."""
        create_resp = await cm_client.post(
            "/v1/valuations",
            json={
                "project_id": str(CM_PROJECT_ID),
                "method": "dcf",
                "currency": "USD",
                "dcf_params": {
                    "cash_flows": [2000000, 2200000, 2400000],
                    "discount_rate": 0.09,
                    "terminal_growth_rate": 0.015,
                    "terminal_method": "gordon",
                },
            },
        )
        assert create_resp.status_code == 201
        val_id = create_resp.json()["id"]

        get_resp = await cm_client.get(f"/v1/valuations/{val_id}")
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["id"] == val_id
        assert data["method"] == "dcf"

    async def test_get_valuation_not_found_404(
        self, cm_client: AsyncClient, cm_user: User
    ):
        """GET non-existent valuation returns 404."""
        resp = await cm_client.get(f"/v1/valuations/{uuid.uuid4()}")
        assert resp.status_code == 404

    async def test_suggest_assumptions_200(
        self, cm_client: AsyncClient, cm_user: User
    ):
        """AI assumption suggestions endpoint returns plausible defaults."""
        resp = await cm_client.post(
            "/v1/valuations/suggest-assumptions",
            json={
                "project_type": "solar",
                "geography": "Germany",
                "stage": "operational",
            },
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "discount_rate" in data
        assert "terminal_growth_rate" in data
        assert "terminal_method" in data
        assert "projection_years" in data
        # Values should be sane for a solar project
        assert 0 < data["discount_rate"] < 1.0
        assert data["projection_years"] > 0

    async def test_compare_valuations_empty_list(
        self, cm_client: AsyncClient, cm_user: User
    ):
        """Compare endpoint with unknown IDs returns empty list (silently skips missing)."""
        resp = await cm_client.post(
            "/v1/valuations/compare",
            json=[str(uuid.uuid4()), str(uuid.uuid4())],
        )
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_list_valuations_filtered_by_project(
        self, cm_client: AsyncClient, cm_project: Project
    ):
        """Filtering list by project_id returns only that project's valuations."""
        # Create one first
        create_resp = await cm_client.post(
            "/v1/valuations",
            json={
                "project_id": str(CM_PROJECT_ID),
                "method": "dcf",
                "currency": "GBP",
                "dcf_params": {
                    "cash_flows": [800000, 900000],
                    "discount_rate": 0.11,
                    "terminal_growth_rate": 0.02,
                    "terminal_method": "gordon",
                },
            },
        )
        assert create_resp.status_code == 201

        list_resp = await cm_client.get(
            "/v1/valuations", params={"project_id": str(CM_PROJECT_ID)}
        )
        assert list_resp.status_code == 200
        data = list_resp.json()
        assert data["total"] >= 1
        assert all(v["project_id"] == str(CM_PROJECT_ID) for v in data["items"])
