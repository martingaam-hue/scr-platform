"""Tests for the Reporting module REST API endpoints."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.main import app
from app.models.core import Organization, User
from app.models.enums import (
    OrgType,
    ReportCategory,
    ReportFrequency,
    ReportStatus,
    UserRole,
)
from app.models.reporting import GeneratedReport, ReportTemplate, ScheduledReport
from app.schemas.auth import CurrentUser

pytestmark = pytest.mark.anyio

# ── Unique IDs for this module ──────────────────────────────────────────────

RP_ORG_ID = uuid.UUID("00000000-0000-0005-0000-000000000001")
RP_USER_ID = uuid.UUID("00000000-0000-0005-0000-000000000002")

RP_CURRENT_USER = CurrentUser(
    user_id=RP_USER_ID,
    org_id=RP_ORG_ID,
    role=UserRole.ADMIN,
    email="rp_test@example.com",
    external_auth_id="clerk_rp_test",
)


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
async def rp_org(db: AsyncSession) -> Organization:
    org = Organization(
        id=RP_ORG_ID,
        name="RP Test Org",
        slug="rp-test-org",
        type=OrgType.INVESTOR,
    )
    db.add(org)
    await db.flush()
    return org


@pytest.fixture
async def rp_user(db: AsyncSession, rp_org: Organization) -> User:
    user = User(
        id=RP_USER_ID,
        org_id=RP_ORG_ID,
        email="rp_test@example.com",
        full_name="RP Test User",
        role=UserRole.ADMIN,
        external_auth_id="clerk_rp_test",
        is_active=True,
    )
    db.add(user)
    await db.flush()
    return user


@pytest.fixture
async def rp_template(db: AsyncSession, rp_org: Organization) -> ReportTemplate:
    """Create an org-owned report template for tests that need one."""
    tmpl = ReportTemplate(
        org_id=RP_ORG_ID,
        name="RP Portfolio Report",
        category=ReportCategory.PORTFOLIO,
        description="Portfolio summary report for RP tests",
        template_config={"audience": "investor", "supported_formats": ["pdf", "xlsx"]},
        sections=[{"name": "portfolio_summary"}],
        is_system=False,
        version=1,
    )
    db.add(tmpl)
    await db.flush()
    return tmpl


@pytest.fixture
async def rp_system_template(db: AsyncSession) -> ReportTemplate:
    """Create a system report template (no org_id) visible to all orgs."""
    tmpl = ReportTemplate(
        org_id=None,
        name="RP System ESG Template",
        category=ReportCategory.ESG,
        description="System ESG report template for RP tests",
        template_config={"audience": "all", "supported_formats": ["pdf"]},
        sections=[{"name": "esg_summary"}],
        is_system=True,
        version=1,
    )
    db.add(tmpl)
    await db.flush()
    return tmpl


@pytest.fixture
async def rp_report(db: AsyncSession, rp_org: Organization, rp_template: ReportTemplate, rp_user: User) -> GeneratedReport:
    """A queued generated report for delete/get tests."""
    report = GeneratedReport(
        org_id=RP_ORG_ID,
        template_id=rp_template.id,
        title="RP Queued Report",
        status=ReportStatus.QUEUED,
        parameters={"output_format": "pdf"},
        generated_by=RP_USER_ID,
    )
    db.add(report)
    await db.flush()
    return report


@pytest.fixture
async def rp_client(db: AsyncSession, rp_user: User) -> AsyncClient:
    app.dependency_overrides[get_current_user] = lambda: RP_CURRENT_USER
    app.dependency_overrides[get_db] = lambda: db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db, None)


# ── Tests ─────────────────────────────────────────────────────────────────────


class TestReportTemplateEndpoints:
    """Tests for /v1/reports/templates."""

    async def test_list_templates_returns_200(
        self, rp_client: AsyncClient, rp_template: ReportTemplate
    ) -> None:
        """GET /v1/reports/templates returns 200 with items structure."""
        resp = await rp_client.get("/v1/reports/templates")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)

    async def test_list_templates_includes_org_template(
        self, rp_client: AsyncClient, rp_template: ReportTemplate
    ) -> None:
        """Org-owned template appears in the list."""
        resp = await rp_client.get("/v1/reports/templates")
        assert resp.status_code == 200
        names = [t["name"] for t in resp.json()["items"]]
        assert "RP Portfolio Report" in names

    async def test_list_templates_includes_system_template(
        self, rp_client: AsyncClient, rp_system_template: ReportTemplate
    ) -> None:
        """System templates are visible to all orgs."""
        resp = await rp_client.get("/v1/reports/templates")
        assert resp.status_code == 200
        names = [t["name"] for t in resp.json()["items"]]
        assert "RP System ESG Template" in names

    async def test_list_templates_filter_by_category(
        self, rp_client: AsyncClient, rp_template: ReportTemplate
    ) -> None:
        """GET /v1/reports/templates?category=portfolio filters correctly."""
        resp = await rp_client.get("/v1/reports/templates?category=portfolio")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert all(t["category"] == "portfolio" for t in items)

    async def test_get_template_by_id_200(
        self, rp_client: AsyncClient, rp_template: ReportTemplate
    ) -> None:
        """GET /v1/reports/templates/{id} returns 200 for an accessible template."""
        resp = await rp_client.get(f"/v1/reports/templates/{rp_template.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "RP Portfolio Report"
        assert data["category"] == "portfolio"

    async def test_get_template_not_found_404(
        self, rp_client: AsyncClient, rp_user: User
    ) -> None:
        """GET /v1/reports/templates/{id} for unknown template returns 404."""
        resp = await rp_client.get(f"/v1/reports/templates/{uuid.uuid4()}")
        assert resp.status_code == 404


class TestGenerateReportEndpoint:
    """Tests for POST /v1/reports/generate."""

    async def test_generate_report_invalid_template_404(
        self, rp_client: AsyncClient, rp_user: User
    ) -> None:
        """POST /v1/reports/generate with unknown template_id returns 404."""
        resp = await rp_client.post(
            "/v1/reports/generate",
            json={
                "template_id": str(uuid.uuid4()),
                "parameters": {},
                "output_format": "pdf",
            },
        )
        assert resp.status_code == 404

    async def test_generate_report_valid_template_202(
        self, rp_client: AsyncClient, rp_template: ReportTemplate
    ) -> None:
        """POST /v1/reports/generate with valid template_id returns 202."""
        with patch("app.modules.reporting.tasks.generate_report_task") as mock_task:
            mock_task.delay = MagicMock()
            resp = await rp_client.post(
                "/v1/reports/generate",
                json={
                    "template_id": str(rp_template.id),
                    "parameters": {"date_from": "2025-01-01"},
                    "output_format": "xlsx",
                },
            )
        assert resp.status_code == 202, resp.text
        data = resp.json()
        assert "report_id" in data
        assert data["status"] == "queued"

    async def test_generate_report_missing_template_id_422(
        self, rp_client: AsyncClient, rp_user: User
    ) -> None:
        """POST /v1/reports/generate without template_id returns 422."""
        resp = await rp_client.post(
            "/v1/reports/generate",
            json={"parameters": {}},
        )
        assert resp.status_code == 422


class TestGeneratedReportListAndGet:
    """Tests for GET /v1/reports and GET /v1/reports/{id}."""

    async def test_list_reports_empty_returns_200(
        self, rp_client: AsyncClient, rp_user: User
    ) -> None:
        """GET /v1/reports returns 200 with paginated structure when empty."""
        resp = await rp_client.get("/v1/reports")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "total_pages" in data

    async def test_list_reports_includes_created_report(
        self, rp_client: AsyncClient, rp_report: GeneratedReport
    ) -> None:
        """GET /v1/reports includes a seeded report in the list."""
        resp = await rp_client.get("/v1/reports")
        assert resp.status_code == 200
        ids = [r["id"] for r in resp.json()["items"]]
        assert str(rp_report.id) in ids

    async def test_get_report_by_id_200(
        self, rp_client: AsyncClient, rp_report: GeneratedReport
    ) -> None:
        """GET /v1/reports/{id} returns 200 for an existing report."""
        resp = await rp_client.get(f"/v1/reports/{rp_report.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "RP Queued Report"
        assert data["status"] == "queued"

    async def test_get_report_not_found_404(
        self, rp_client: AsyncClient, rp_user: User
    ) -> None:
        """GET /v1/reports/{id} for unknown report returns 404."""
        resp = await rp_client.get(
            "/v1/reports/00000000-0000-0000-0000-000000000099"
        )
        assert resp.status_code == 404

    async def test_delete_report_204(
        self, rp_client: AsyncClient, rp_report: GeneratedReport
    ) -> None:
        """DELETE /v1/reports/{id} returns 204 and subsequent GET returns 404."""
        del_resp = await rp_client.delete(f"/v1/reports/{rp_report.id}")
        assert del_resp.status_code == 204

        get_resp = await rp_client.get(f"/v1/reports/{rp_report.id}")
        assert get_resp.status_code == 404

    async def test_delete_report_not_found_404(
        self, rp_client: AsyncClient, rp_user: User
    ) -> None:
        """DELETE /v1/reports/{id} for unknown report returns 404."""
        resp = await rp_client.delete(
            f"/v1/reports/{uuid.uuid4()}"
        )
        assert resp.status_code == 404


class TestScheduleEndpoints:
    """Tests for /v1/reports/schedules."""

    async def test_list_schedules_empty_200(
        self, rp_client: AsyncClient, rp_user: User
    ) -> None:
        """GET /v1/reports/schedules returns 200 with items structure."""
        resp = await rp_client.get("/v1/reports/schedules")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    async def test_create_schedule_201(
        self, rp_client: AsyncClient, rp_template: ReportTemplate
    ) -> None:
        """POST /v1/reports/schedules with valid data returns 201."""
        resp = await rp_client.post(
            "/v1/reports/schedules",
            json={
                "template_id": str(rp_template.id),
                "name": "Weekly Portfolio Report",
                "frequency": "weekly",
                "parameters": {},
                "recipients": ["investor@example.com"],
                "output_format": "pdf",
            },
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["name"] == "Weekly Portfolio Report"
        assert data["frequency"] == "weekly"
        assert data["is_active"] is True

    async def test_create_schedule_invalid_template_404(
        self, rp_client: AsyncClient, rp_user: User
    ) -> None:
        """POST /v1/reports/schedules with unknown template returns 404."""
        resp = await rp_client.post(
            "/v1/reports/schedules",
            json={
                "template_id": str(uuid.uuid4()),
                "name": "Ghost Schedule",
                "frequency": "monthly",
            },
        )
        assert resp.status_code == 404

    async def test_delete_schedule_not_found_404(
        self, rp_client: AsyncClient, rp_user: User
    ) -> None:
        """DELETE /v1/reports/schedules/{id} for unknown schedule returns 404."""
        resp = await rp_client.delete(
            f"/v1/reports/schedules/{uuid.uuid4()}"
        )
        assert resp.status_code == 404

    async def test_create_then_delete_schedule_204(
        self, rp_client: AsyncClient, rp_template: ReportTemplate
    ) -> None:
        """Create a schedule and DELETE it returns 204."""
        create_resp = await rp_client.post(
            "/v1/reports/schedules",
            json={
                "template_id": str(rp_template.id),
                "name": "Delete Me Schedule",
                "frequency": "monthly",
                "parameters": {},
                "recipients": [],
                "output_format": "pdf",
            },
        )
        assert create_resp.status_code == 201
        schedule_id = create_resp.json()["id"]

        del_resp = await rp_client.delete(f"/v1/reports/schedules/{schedule_id}")
        assert del_resp.status_code == 204
