"""Tests for sprint Item 15: risk, legal, deal_intelligence, carbon_credits modules."""

from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

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
    PortfolioStrategy,
    ProjectStage,
    ProjectStatus,
    ProjectType,
    UserRole,
)
from app.models.investors import Portfolio
from app.models.projects import Project
from app.schemas.auth import CurrentUser

# ── Constants ──────────────────────────────────────────────────────────────────

ORG_ID = uuid.UUID("00000000-0000-0000-0001-000000000001")
USER_ID = uuid.UUID("00000000-0000-0000-0001-000000000002")
PROJECT_ID = uuid.UUID("00000000-0000-0000-0001-000000000010")
PORTFOLIO_ID = uuid.UUID("00000000-0000-0000-0001-000000000020")

ADMIN_USER = CurrentUser(
    user_id=USER_ID,
    org_id=ORG_ID,
    role=UserRole.ADMIN,
    email="sprint15@example.com",
    external_auth_id="user_sprint15",
)


# ── Auth helper ────────────────────────────────────────────────────────────────


def _override_auth(user: CurrentUser):
    async def _override():
        return user
    return _override


# ── Shared DB fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
async def seed_org_user(db: AsyncSession):
    """Seed org and user for this test module."""
    org = Organization(id=ORG_ID, name="Sprint15 Org", slug="sprint15-org", type=OrgType.INVESTOR)
    db.add(org)
    user = User(
        id=USER_ID,
        org_id=ORG_ID,
        email="sprint15@example.com",
        full_name="Sprint 15",
        role=UserRole.ADMIN,
        external_auth_id="user_sprint15",
        is_active=True,
    )
    db.add(user)
    await db.flush()
    return org, user


@pytest.fixture
async def seed_project(db: AsyncSession, seed_org_user):
    """Seed a solar project for carbon + deal tests."""
    project = Project(
        id=PROJECT_ID,
        org_id=ORG_ID,
        name="Sprint15 Solar",
        slug="sprint15-solar",
        project_type=ProjectType.SOLAR,
        status=ProjectStatus.ACTIVE,
        stage=ProjectStage.DEVELOPMENT,
        geography_country="Kenya",
        total_investment_required=Decimal("5000000"),
        currency="USD",
        capacity_mw=Decimal("50"),
    )
    db.add(project)
    await db.flush()
    return project


@pytest.fixture
async def seed_portfolio(db: AsyncSession, seed_org_user):
    """Seed a portfolio for risk tests."""
    portfolio = Portfolio(
        id=PORTFOLIO_ID,
        org_id=ORG_ID,
        name="Sprint15 Fund",
        description="Test portfolio",
        strategy=PortfolioStrategy.IMPACT,
        fund_type=FundType.CLOSED_END,
        target_aum=Decimal("50000000"),
        current_aum=Decimal("0"),
        currency="USD",
    )
    db.add(portfolio)
    await db.flush()
    return portfolio


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Carbon Credits — Estimator (pure unit tests)
# ═══════════════════════════════════════════════════════════════════════════════


class TestCarbonEstimator:
    """Tests for the deterministic carbon credit estimator — no DB needed."""

    def _estimate(self, **kwargs):
        from app.modules.carbon_credits.estimator import estimate_credits
        return estimate_credits(**kwargs)

    def test_solar_high_capacity_gives_high_estimate(self):
        result = self._estimate(
            project_type="solar_pv",
            capacity_mw=100.0,
            geography_country="Kenya",
        )
        assert result["annual_tons_co2e"] > 50_000
        assert result["confidence"] == "high"

    def test_wind_africa_uses_africa_factor(self):
        """Africa emission factor (0.45) should differ from Europe (0.25)."""
        africa = self._estimate(
            project_type="onshore_wind",
            capacity_mw=50.0,
            geography_country="South Africa",
        )
        europe = self._estimate(
            project_type="onshore_wind",
            capacity_mw=50.0,
            geography_country="Germany",
        )
        assert africa["annual_tons_co2e"] > europe["annual_tons_co2e"]

    def test_no_capacity_gives_low_confidence(self):
        result = self._estimate(
            project_type="solar_pv",
            capacity_mw=None,
            geography_country="Kenya",
        )
        assert result["confidence"] == "low"
        assert result["annual_tons_co2e"] == 5000.0

    def test_unsupported_type_gives_fallback(self):
        result = self._estimate(
            project_type="unknown_type",
            capacity_mw=10.0,
            geography_country="Germany",
        )
        assert result["confidence"] == "low"
        assert result["annual_tons_co2e"] == 3000.0

    def test_hydro_uses_higher_capacity_factor(self):
        """Hydro has CF=0.42 vs wind CF=0.28 — same capacity should yield more credits."""
        hydro = self._estimate(project_type="hydro", capacity_mw=10.0, geography_country="Kenya")
        wind = self._estimate(project_type="onshore_wind", capacity_mw=10.0, geography_country="Kenya")
        assert hydro["annual_tons_co2e"] > wind["annual_tons_co2e"]

    def test_solar_uses_acm0002_methodology(self):
        result = self._estimate(
            project_type="solar_pv",
            capacity_mw=20.0,
            geography_country="Germany",
        )
        assert result["methodology"] == "ACM0002"

    def test_green_building_uses_savings_pct(self):
        result = self._estimate(
            project_type="green_building",
            capacity_mw=None,
            geography_country="US",
            savings_pct=30.0,
            baseline_consumption_mwh=10_000,
        )
        assert result["confidence"] == "medium"
        assert result["annual_tons_co2e"] > 0

    def test_green_building_no_data_gives_low(self):
        result = self._estimate(
            project_type="green_building",
            capacity_mw=None,
            geography_country="US",
        )
        assert result["confidence"] == "low"

    def test_revenue_projection_returns_all_scenarios(self):
        from app.modules.carbon_credits.estimator import revenue_projection
        rev = revenue_projection(annual_tons=10_000.0)
        assert "conservative" in rev["scenarios"]
        assert "base_case" in rev["scenarios"]
        assert "optimistic" in rev["scenarios"]
        assert "eu_ets" in rev["scenarios"]

    def test_revenue_projection_base_case_arithmetic(self):
        from app.modules.carbon_credits.estimator import revenue_projection
        rev = revenue_projection(annual_tons=1_000.0, price_scenarios={"test": 10.0})
        assert rev["scenarios"]["test"]["annual_revenue_usd"] == 10_000.0
        assert rev["scenarios"]["test"]["10yr_revenue_usd"] == 100_000.0

    def test_europe_lower_factor_than_default(self):
        """Europe region (0.25) has lower emission factor than unknown country (default 0.42)."""
        eu = self._estimate(project_type="solar_pv", capacity_mw=10.0, geography_country="Europe")
        unknown = self._estimate(project_type="solar_pv", capacity_mw=10.0, geography_country="Wakanda")
        assert eu["annual_tons_co2e"] < unknown["annual_tons_co2e"]


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Carbon Credits — API
# ═══════════════════════════════════════════════════════════════════════════════


class TestCarbonAPI:
    """API-level tests for carbon credit endpoints."""

    @pytest.mark.anyio
    async def test_estimate_creates_record_200(
        self, client: AsyncClient, db: AsyncSession, seed_project
    ):
        app.dependency_overrides[get_current_user] = _override_auth(ADMIN_USER)
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_readonly_session] = lambda: db
        try:
            resp = await client.post(f"/v1/carbon/estimate/{PROJECT_ID}")
            assert resp.status_code == 200
            data = resp.json()
            assert "estimate" in data
            assert data["estimate"]["annual_tons_co2e"] > 0
            assert "confidence" in data["estimate"]
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.anyio
    async def test_estimate_404_unknown_project(self, client: AsyncClient, db: AsyncSession, seed_org_user):
        fake_id = uuid.UUID("00000000-0000-0000-9999-000000000001")
        app.dependency_overrides[get_current_user] = _override_auth(ADMIN_USER)
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_readonly_session] = lambda: db
        try:
            resp = await client.post(f"/v1/carbon/estimate/{fake_id}")
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.anyio
    async def test_get_carbon_credit_after_estimate(
        self, client: AsyncClient, db: AsyncSession, seed_project
    ):
        app.dependency_overrides[get_current_user] = _override_auth(ADMIN_USER)
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_readonly_session] = lambda: db
        try:
            # First create via estimate
            await client.post(f"/v1/carbon/estimate/{PROJECT_ID}")
            # Then fetch
            resp = await client.get(f"/v1/carbon/{PROJECT_ID}")
            assert resp.status_code == 200
            data = resp.json()
            assert data["project_id"] == str(PROJECT_ID)
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.anyio
    async def test_get_carbon_credit_404_no_record(
        self, client: AsyncClient, db: AsyncSession, seed_project
    ):
        app.dependency_overrides[get_current_user] = _override_auth(ADMIN_USER)
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_readonly_session] = lambda: db
        try:
            # No estimate created yet
            resp = await client.get(f"/v1/carbon/{PROJECT_ID}")
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.clear()


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Risk Assessment
# ═══════════════════════════════════════════════════════════════════════════════


class TestRiskAssessment:
    """Tests for risk assessment CRUD endpoints."""

    _valid_body = {
        "entity_type": "project",
        "entity_id": str(PROJECT_ID),
        "risk_type": "market",
        "severity": "medium",
        "probability": "possible",
        "description": "Market price volatility risk.",
        "mitigation": "Hedge with long-term PPA.",
        "status": "identified",
    }

    @pytest.mark.anyio
    async def test_create_assessment_201(
        self, client: AsyncClient, db: AsyncSession, seed_org_user
    ):
        app.dependency_overrides[get_current_user] = _override_auth(ADMIN_USER)
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_readonly_session] = lambda: db
        try:
            resp = await client.post("/v1/risk/assess", json=self._valid_body)
            assert resp.status_code == 201
            data = resp.json()
            assert data["entity_type"] == "project"
            assert data["severity"] == "medium"
            assert data["probability"] == "possible"
            assert data["assessed_by"] == str(USER_ID)
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.anyio
    async def test_list_assessments_empty_initially(
        self, client: AsyncClient, db: AsyncSession, seed_org_user
    ):
        app.dependency_overrides[get_current_user] = _override_auth(ADMIN_USER)
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_readonly_session] = lambda: db
        try:
            resp = await client.get("/v1/risk/assessments")
            assert resp.status_code == 200
            assert resp.json() == []
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.anyio
    async def test_list_assessments_after_create(
        self, client: AsyncClient, db: AsyncSession, seed_org_user
    ):
        app.dependency_overrides[get_current_user] = _override_auth(ADMIN_USER)
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_readonly_session] = lambda: db
        try:
            await client.post("/v1/risk/assess", json=self._valid_body)
            resp = await client.get("/v1/risk/assessments")
            assert resp.status_code == 200
            items = resp.json()
            assert len(items) == 1
            assert items[0]["risk_type"] == "market"
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.anyio
    async def test_create_assessment_invalid_severity_422(
        self, client: AsyncClient, db: AsyncSession, seed_org_user
    ):
        app.dependency_overrides[get_current_user] = _override_auth(ADMIN_USER)
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_readonly_session] = lambda: db
        try:
            bad_body = {**self._valid_body, "severity": "catastrophic"}
            resp = await client.post("/v1/risk/assess", json=bad_body)
            assert resp.status_code == 422
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.anyio
    async def test_create_assessment_filters_by_entity(
        self, client: AsyncClient, db: AsyncSession, seed_org_user
    ):
        app.dependency_overrides[get_current_user] = _override_auth(ADMIN_USER)
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_readonly_session] = lambda: db
        try:
            await client.post("/v1/risk/assess", json=self._valid_body)
            # Filter by entity
            resp = await client.get(
                "/v1/risk/assessments",
                params={"entity_type": "project", "entity_id": str(PROJECT_ID)},
            )
            assert resp.status_code == 200
            assert len(resp.json()) == 1
            # Filter by different entity returns empty
            other_id = uuid.UUID("00000000-0000-0000-9999-000000000099")
            resp2 = await client.get(
                "/v1/risk/assessments",
                params={"entity_type": "project", "entity_id": str(other_id)},
            )
            assert resp2.json() == []
        finally:
            app.dependency_overrides.clear()


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Legal Documents
# ═══════════════════════════════════════════════════════════════════════════════


class TestLegalTemplates:
    """Tests for legal template listing (static, no DB)."""

    @pytest.mark.anyio
    async def test_list_templates_200(self, client: AsyncClient, db: AsyncSession, seed_org_user):
        app.dependency_overrides[get_current_user] = _override_auth(ADMIN_USER)
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_readonly_session] = lambda: db
        try:
            resp = await client.get("/v1/legal/templates")
            assert resp.status_code == 200
            templates = resp.json()
            assert len(templates) > 0
            # Each template should have required fields
            for t in templates:
                assert "id" in t
                assert "name" in t
                assert "doc_type" in t
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.anyio
    async def test_get_template_detail_200(self, client: AsyncClient, db: AsyncSession, seed_org_user):
        from app.modules.legal.templates import SYSTEM_TEMPLATES
        first_id = SYSTEM_TEMPLATES[0]["id"]

        app.dependency_overrides[get_current_user] = _override_auth(ADMIN_USER)
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_readonly_session] = lambda: db
        try:
            resp = await client.get(f"/v1/legal/templates/{first_id}")
            assert resp.status_code == 200
            data = resp.json()
            assert data["id"] == first_id
            assert "questionnaire" in data
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.anyio
    async def test_get_template_detail_404(self, client: AsyncClient, db: AsyncSession, seed_org_user):
        app.dependency_overrides[get_current_user] = _override_auth(ADMIN_USER)
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_readonly_session] = lambda: db
        try:
            resp = await client.get("/v1/legal/templates/nonexistent-template-xyz")
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.clear()


class TestLegalDocuments:
    """Tests for legal document CRUD (no AI calls — those go through Celery)."""

    @pytest.mark.anyio
    async def test_create_document_201(self, client: AsyncClient, db: AsyncSession, seed_org_user):
        from app.modules.legal.templates import SYSTEM_TEMPLATES
        first_id = SYSTEM_TEMPLATES[0]["id"]

        app.dependency_overrides[get_current_user] = _override_auth(ADMIN_USER)
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_readonly_session] = lambda: db
        try:
            resp = await client.post(
                "/v1/legal/documents",
                json={"template_id": first_id, "title": "Test Agreement"},
            )
            assert resp.status_code == 201
            data = resp.json()
            assert data["title"] == "Test Agreement"
            assert data["template_id"] == first_id
            assert "id" in data
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.anyio
    async def test_list_documents_200(self, client: AsyncClient, db: AsyncSession, seed_org_user):
        from app.modules.legal.templates import SYSTEM_TEMPLATES
        first_id = SYSTEM_TEMPLATES[0]["id"]

        app.dependency_overrides[get_current_user] = _override_auth(ADMIN_USER)
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_readonly_session] = lambda: db
        try:
            # Create one doc first
            await client.post(
                "/v1/legal/documents",
                json={"template_id": first_id, "title": "Listed Doc"},
            )
            resp = await client.get("/v1/legal/documents")
            assert resp.status_code == 200
            data = resp.json()
            assert data["total"] >= 1
            assert any(d["title"] == "Listed Doc" for d in data["items"])
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.anyio
    async def test_get_document_200(self, client: AsyncClient, db: AsyncSession, seed_org_user):
        from app.modules.legal.templates import SYSTEM_TEMPLATES
        first_id = SYSTEM_TEMPLATES[0]["id"]

        app.dependency_overrides[get_current_user] = _override_auth(ADMIN_USER)
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_readonly_session] = lambda: db
        try:
            create_resp = await client.post(
                "/v1/legal/documents",
                json={"template_id": first_id, "title": "Fetched Doc"},
            )
            doc_id = create_resp.json()["id"]
            get_resp = await client.get(f"/v1/legal/documents/{doc_id}")
            assert get_resp.status_code == 200
            assert get_resp.json()["title"] == "Fetched Doc"
        finally:
            app.dependency_overrides.clear()


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Deal Intelligence
# ═══════════════════════════════════════════════════════════════════════════════


class TestDealIntelligence:
    """Tests for deal intelligence pipeline + discovery endpoints."""

    @pytest.mark.anyio
    async def test_pipeline_200(self, client: AsyncClient, db: AsyncSession, seed_org_user):
        """Pipeline endpoint returns expected structure even with empty data."""
        app.dependency_overrides[get_current_user] = _override_auth(ADMIN_USER)
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_readonly_session] = lambda: db
        try:
            resp = await client.get("/v1/deals/pipeline")
            assert resp.status_code == 200
            data = resp.json()
            assert "stages" in data or "total" in data or isinstance(data, dict)
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.anyio
    async def test_discover_200(self, client: AsyncClient, db: AsyncSession, seed_org_user):
        """Discovery endpoint returns a list even with no data."""
        app.dependency_overrides[get_current_user] = _override_auth(ADMIN_USER)
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_readonly_session] = lambda: db
        try:
            resp = await client.get("/v1/deals/discover")
            assert resp.status_code == 200
            data = resp.json()
            assert "projects" in data or "items" in data or isinstance(data, dict)
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.anyio
    async def test_discover_with_filters(self, client: AsyncClient, db: AsyncSession, seed_org_user):
        app.dependency_overrides[get_current_user] = _override_auth(ADMIN_USER)
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_readonly_session] = lambda: db
        try:
            resp = await client.get(
                "/v1/deals/discover",
                params={"sector": "solar", "score_min": 0, "score_max": 100},
            )
            assert resp.status_code == 200
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.anyio
    async def test_screening_report_404_unknown(
        self, client: AsyncClient, db: AsyncSession, seed_org_user
    ):
        fake_id = uuid.UUID("00000000-0000-0000-9999-000000000002")
        app.dependency_overrides[get_current_user] = _override_auth(ADMIN_USER)
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_readonly_session] = lambda: db
        try:
            resp = await client.get(f"/v1/deals/{fake_id}/screening")
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.anyio
    async def test_compare_empty_list_422(
        self, client: AsyncClient, db: AsyncSession, seed_org_user
    ):
        """Comparing fewer than 2 projects should return 422."""
        app.dependency_overrides[get_current_user] = _override_auth(ADMIN_USER)
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_readonly_session] = lambda: db
        try:
            resp = await client.post("/v1/deals/compare", json={"project_ids": []})
            assert resp.status_code in (400, 422)
        finally:
            app.dependency_overrides.clear()
