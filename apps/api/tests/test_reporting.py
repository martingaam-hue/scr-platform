"""Comprehensive tests for the Reporting module."""

import uuid
from datetime import datetime, timezone
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
from app.modules.reporting import service
from app.modules.reporting.schemas import OutputFormat
from app.schemas.auth import CurrentUser

# ── Test Data ────────────────────────────────────────────────────────────────

ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
OTHER_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000099")
USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
VIEWER_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000003")
ANALYST_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000004")

ADMIN_USER = CurrentUser(
    user_id=USER_ID,
    org_id=ORG_ID,
    role=UserRole.ADMIN,
    email="admin@example.com",
    external_auth_id="user_test_admin",
)

VIEWER_USER = CurrentUser(
    user_id=VIEWER_USER_ID,
    org_id=ORG_ID,
    role=UserRole.VIEWER,
    email="viewer@example.com",
    external_auth_id="user_test_viewer",
)

ANALYST_USER = CurrentUser(
    user_id=ANALYST_USER_ID,
    org_id=ORG_ID,
    role=UserRole.ANALYST,
    email="analyst@example.com",
    external_auth_id="user_test_analyst",
)


# ── Fixtures ─────────────────────────────────────────────────────────────────


def _override_auth(user: CurrentUser):
    async def _override():
        return user
    return _override


@pytest.fixture
async def seed_data(db: AsyncSession) -> dict:
    """Seed org, users, and sample templates/reports."""
    org = Organization(id=ORG_ID, name="Test Org", slug="test-org", type=OrgType.INVESTOR)
    db.add(org)
    other_org = Organization(
        id=OTHER_ORG_ID, name="Other Org", slug="other-org", type=OrgType.ALLY
    )
    db.add(other_org)

    admin = User(
        id=USER_ID, org_id=ORG_ID, email="admin@example.com",
        full_name="Admin User", role=UserRole.ADMIN,
        external_auth_id="user_test_admin", is_active=True,
    )
    db.add(admin)
    viewer = User(
        id=VIEWER_USER_ID, org_id=ORG_ID, email="viewer@example.com",
        full_name="Viewer User", role=UserRole.VIEWER,
        external_auth_id="user_test_viewer", is_active=True,
    )
    db.add(viewer)
    analyst = User(
        id=ANALYST_USER_ID, org_id=ORG_ID, email="analyst@example.com",
        full_name="Analyst User", role=UserRole.ANALYST,
        external_auth_id="user_test_analyst", is_active=True,
    )
    db.add(analyst)
    await db.flush()

    # System template
    sys_tmpl = ReportTemplate(
        org_id=None,
        name="System Template",
        category=ReportCategory.PERFORMANCE,
        description="A system-wide template",
        template_config={"audience": "investor", "supported_formats": ["pdf", "xlsx"]},
        sections=[{"name": "performance_summary"}],
        is_system=True,
        version=1,
    )
    db.add(sys_tmpl)

    # Org template
    org_tmpl = ReportTemplate(
        org_id=ORG_ID,
        name="Org Template",
        category=ReportCategory.PROJECT,
        description="An org-specific template",
        template_config={"audience": "ally", "supported_formats": ["pdf"]},
        sections=[{"name": "project_overview"}],
        is_system=False,
        version=1,
    )
    db.add(org_tmpl)

    # Other org template (should not be visible)
    other_tmpl = ReportTemplate(
        org_id=OTHER_ORG_ID,
        name="Other Org Template",
        category=ReportCategory.ESG,
        description="Belongs to another org",
        template_config={},
        sections=[],
        is_system=False,
        version=1,
    )
    db.add(other_tmpl)

    await db.flush()

    # Generated report
    report = GeneratedReport(
        org_id=ORG_ID,
        template_id=sys_tmpl.id,
        title="Test Report",
        status=ReportStatus.READY,
        parameters={"output_format": "pdf"},
        s3_key="test-org/reports/test.html",
        generated_by=USER_ID,
        completed_at=datetime.utcnow(),
    )
    db.add(report)

    queued_report = GeneratedReport(
        org_id=ORG_ID,
        template_id=sys_tmpl.id,
        title="Queued Report",
        status=ReportStatus.QUEUED,
        parameters={"output_format": "xlsx"},
        generated_by=USER_ID,
    )
    db.add(queued_report)

    # Schedule
    schedule = ScheduledReport(
        org_id=ORG_ID,
        template_id=sys_tmpl.id,
        name="Weekly Report",
        frequency=ReportFrequency.WEEKLY,
        parameters={"output_format": "pdf"},
        recipients={"emails": ["test@example.com"]},
        is_active=True,
    )
    db.add(schedule)

    await db.flush()
    return {
        "sys_tmpl": sys_tmpl,
        "org_tmpl": org_tmpl,
        "other_tmpl": other_tmpl,
        "report": report,
        "queued_report": queued_report,
        "schedule": schedule,
    }


@pytest.fixture
async def test_client(db: AsyncSession, seed_data) -> AsyncClient:
    app.dependency_overrides[get_current_user] = _override_auth(ADMIN_USER)
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
async def analyst_client(db: AsyncSession, seed_data) -> AsyncClient:
    app.dependency_overrides[get_current_user] = _override_auth(ANALYST_USER)
    app.dependency_overrides[get_db] = lambda: db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


# ── Template Service Tests ──────────────────────────────────────────────────


class TestTemplateService:
    async def test_list_templates_includes_system_and_org(self, db: AsyncSession, seed_data):
        templates = await service.list_templates(db, ORG_ID)
        names = {t.name for t in templates}
        assert "System Template" in names
        assert "Org Template" in names
        assert "Other Org Template" not in names

    async def test_list_templates_filter_by_category(self, db: AsyncSession, seed_data):
        templates = await service.list_templates(db, ORG_ID, ReportCategory.PERFORMANCE)
        assert all(t.category == ReportCategory.PERFORMANCE for t in templates)
        assert any(t.name == "System Template" for t in templates)

    async def test_get_template_system(self, db: AsyncSession, seed_data):
        tmpl = seed_data["sys_tmpl"]
        result = await service.get_template(db, tmpl.id, ORG_ID)
        assert result is not None
        assert result.name == "System Template"

    async def test_get_template_org_owned(self, db: AsyncSession, seed_data):
        tmpl = seed_data["org_tmpl"]
        result = await service.get_template(db, tmpl.id, ORG_ID)
        assert result is not None
        assert result.name == "Org Template"

    async def test_get_template_other_org_returns_none(self, db: AsyncSession, seed_data):
        tmpl = seed_data["other_tmpl"]
        result = await service.get_template(db, tmpl.id, ORG_ID)
        assert result is None

    async def test_tenant_isolation(self, db: AsyncSession, seed_data):
        """Other org should not see our org template."""
        templates = await service.list_templates(db, OTHER_ORG_ID)
        names = {t.name for t in templates}
        assert "System Template" in names  # system is visible to all
        assert "Org Template" not in names  # org-specific not visible


# ── Generated Report Service Tests ──────────────────────────────────────────


class TestGeneratedReportService:
    async def test_create_report(self, db: AsyncSession, seed_data):
        tmpl = seed_data["sys_tmpl"]
        report = await service.create_generated_report(
            db, ADMIN_USER, tmpl.id, "New Report", {"key": "val"}, OutputFormat.XLSX,
        )
        assert report.status == ReportStatus.QUEUED
        assert report.org_id == ORG_ID
        assert report.title == "New Report"

    async def test_list_reports(self, db: AsyncSession, seed_data):
        reports, total = await service.list_generated_reports(db, ORG_ID)
        assert total >= 2
        assert all(r.org_id == ORG_ID for r in reports)

    async def test_list_reports_filter_status(self, db: AsyncSession, seed_data):
        reports, total = await service.list_generated_reports(
            db, ORG_ID, status=ReportStatus.READY,
        )
        assert total >= 1
        assert all(r.status == ReportStatus.READY for r in reports)

    async def test_list_reports_pagination(self, db: AsyncSession, seed_data):
        reports, total = await service.list_generated_reports(
            db, ORG_ID, page=1, page_size=1,
        )
        assert len(reports) == 1
        assert total >= 2

    async def test_get_report(self, db: AsyncSession, seed_data):
        report = seed_data["report"]
        result = await service.get_generated_report(db, report.id, ORG_ID)
        assert result is not None
        assert result.title == "Test Report"

    async def test_soft_delete(self, db: AsyncSession, seed_data):
        report = seed_data["report"]
        deleted = await service.delete_generated_report(db, report.id, ORG_ID)
        assert deleted is True
        # Should no longer be found
        result = await service.get_generated_report(db, report.id, ORG_ID)
        assert result is None

    @patch("app.modules.reporting.service._get_s3_client")
    async def test_download_url(self, mock_s3, db: AsyncSession, seed_data):
        mock_client = MagicMock()
        mock_client.generate_presigned_url.return_value = "https://s3.example.com/file"
        mock_s3.return_value = mock_client

        url = service.generate_download_url("test-key")
        assert "https://s3.example.com/file" == url


# ── Schedule Service Tests ───────────────────────────────────────────────────


class TestScheduleService:
    async def test_create_schedule(self, db: AsyncSession, seed_data):
        tmpl = seed_data["sys_tmpl"]
        schedule = await service.create_schedule(
            db, ADMIN_USER, tmpl.id, "Daily Report",
            ReportFrequency.DAILY, {}, ["a@b.com"], OutputFormat.PDF,
        )
        assert schedule.name == "Daily Report"
        assert schedule.is_active is True

    async def test_list_schedules(self, db: AsyncSession, seed_data):
        schedules = await service.list_schedules(db, ORG_ID)
        assert len(schedules) >= 1
        assert all(s.org_id == ORG_ID for s in schedules)

    async def test_update_schedule(self, db: AsyncSession, seed_data):
        schedule = seed_data["schedule"]
        updated = await service.update_schedule(
            db, schedule.id, ORG_ID, name="Updated Name", is_active=False,
        )
        assert updated is not None
        assert updated.name == "Updated Name"
        assert updated.is_active is False

    async def test_delete_schedule(self, db: AsyncSession, seed_data):
        schedule = seed_data["schedule"]
        deleted = await service.delete_schedule(db, schedule.id, ORG_ID)
        assert deleted is True

    async def test_tenant_isolation(self, db: AsyncSession, seed_data):
        schedule = seed_data["schedule"]
        result = await service.update_schedule(db, schedule.id, OTHER_ORG_ID, name="Hacked")
        assert result is None


# ── API Endpoint Tests ──────────────────────────────────────────────────────


class TestTemplateEndpoints:
    async def test_list_templates(self, test_client: AsyncClient):
        resp = await test_client.get("/reports/templates")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 2
        names = {t["name"] for t in data["items"]}
        assert "System Template" in names
        assert "Org Template" in names

    async def test_list_templates_filter(self, test_client: AsyncClient):
        resp = await test_client.get("/reports/templates?category=performance")
        assert resp.status_code == 200
        data = resp.json()
        assert all(t["category"] == "performance" for t in data["items"])

    async def test_get_template(self, test_client: AsyncClient, seed_data):
        tmpl_id = str(seed_data["sys_tmpl"].id)
        resp = await test_client.get(f"/reports/templates/{tmpl_id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "System Template"

    async def test_get_template_not_found(self, test_client: AsyncClient):
        fake_id = str(uuid.uuid4())
        resp = await test_client.get(f"/reports/templates/{fake_id}")
        assert resp.status_code == 404


class TestGenerateEndpoint:
    @patch("app.modules.reporting.router.generate_report_task", create=True)
    async def test_generate_report_202(self, mock_task, test_client: AsyncClient, seed_data):
        mock_task.delay = MagicMock()
        tmpl_id = str(seed_data["sys_tmpl"].id)
        resp = await test_client.post("/reports/generate", json={
            "template_id": tmpl_id,
            "parameters": {"date_from": "2025-01-01"},
            "output_format": "xlsx",
        })
        assert resp.status_code == 202
        data = resp.json()
        assert data["status"] == "queued"
        assert "report_id" in data

    async def test_generate_invalid_template(self, test_client: AsyncClient):
        resp = await test_client.post("/reports/generate", json={
            "template_id": str(uuid.uuid4()),
            "parameters": {},
        })
        assert resp.status_code == 404


class TestReportEndpoints:
    async def test_list_reports(self, test_client: AsyncClient):
        resp = await test_client.get("/reports")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 2
        assert "page" in data
        assert "total_pages" in data

    async def test_list_reports_pagination(self, test_client: AsyncClient):
        resp = await test_client.get("/reports?page=1&page_size=1")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 1

    @patch("app.modules.reporting.service._get_s3_client")
    async def test_get_report_detail(self, mock_s3, test_client: AsyncClient, seed_data):
        mock_client = MagicMock()
        mock_client.generate_presigned_url.return_value = "https://s3.example.com/dl"
        mock_s3.return_value = mock_client

        report_id = str(seed_data["report"].id)
        resp = await test_client.get(f"/reports/{report_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Test Report"
        assert data["download_url"] == "https://s3.example.com/dl"

    async def test_delete_report(self, test_client: AsyncClient, seed_data):
        report_id = str(seed_data["queued_report"].id)
        resp = await test_client.delete(f"/reports/{report_id}")
        assert resp.status_code == 204

    async def test_delete_report_not_found(self, test_client: AsyncClient):
        resp = await test_client.delete(f"/reports/{uuid.uuid4()}")
        assert resp.status_code == 404


class TestScheduleEndpoints:
    async def test_list_schedules(self, test_client: AsyncClient):
        resp = await test_client.get("/reports/schedules")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    async def test_create_schedule(self, test_client: AsyncClient, seed_data):
        tmpl_id = str(seed_data["sys_tmpl"].id)
        resp = await test_client.post("/reports/schedules", json={
            "template_id": tmpl_id,
            "name": "Monthly ESG",
            "frequency": "monthly",
            "parameters": {},
            "recipients": ["a@b.com"],
            "output_format": "pdf",
        })
        assert resp.status_code == 201
        assert resp.json()["name"] == "Monthly ESG"

    async def test_update_schedule(self, test_client: AsyncClient, seed_data):
        schedule_id = str(seed_data["schedule"].id)
        resp = await test_client.put(f"/reports/schedules/{schedule_id}", json={
            "name": "Renamed Schedule",
            "is_active": False,
        })
        assert resp.status_code == 200
        assert resp.json()["name"] == "Renamed Schedule"
        assert resp.json()["is_active"] is False

    async def test_delete_schedule(self, test_client: AsyncClient, seed_data):
        schedule_id = str(seed_data["schedule"].id)
        resp = await test_client.delete(f"/reports/schedules/{schedule_id}")
        assert resp.status_code == 204

    async def test_delete_schedule_not_found(self, test_client: AsyncClient):
        resp = await test_client.delete(f"/reports/schedules/{uuid.uuid4()}")
        assert resp.status_code == 404


# ── RBAC Tests ───────────────────────────────────────────────────────────────


class TestRBAC:
    async def test_viewer_can_list_templates(self, viewer_client: AsyncClient):
        resp = await viewer_client.get("/reports/templates")
        assert resp.status_code == 200

    async def test_viewer_can_list_reports(self, viewer_client: AsyncClient):
        resp = await viewer_client.get("/reports")
        assert resp.status_code == 200

    async def test_viewer_cannot_generate(self, viewer_client: AsyncClient, seed_data):
        tmpl_id = str(seed_data["sys_tmpl"].id)
        resp = await viewer_client.post("/reports/generate", json={
            "template_id": tmpl_id,
            "parameters": {},
        })
        assert resp.status_code == 403

    async def test_viewer_cannot_delete(self, viewer_client: AsyncClient, seed_data):
        report_id = str(seed_data["report"].id)
        resp = await viewer_client.delete(f"/reports/{report_id}")
        assert resp.status_code == 403

    async def test_analyst_can_generate(self, analyst_client: AsyncClient, seed_data):
        tmpl_id = str(seed_data["sys_tmpl"].id)
        with patch("app.modules.reporting.tasks.generate_report_task") as mock_task:
            mock_task.delay = MagicMock()
            resp = await analyst_client.post("/reports/generate", json={
                "template_id": tmpl_id,
                "parameters": {},
                "output_format": "pdf",
            })
        assert resp.status_code == 202

    async def test_analyst_cannot_delete(self, analyst_client: AsyncClient, seed_data):
        report_id = str(seed_data["report"].id)
        resp = await analyst_client.delete(f"/reports/{report_id}")
        assert resp.status_code == 403


# ── Generator Unit Tests ────────────────────────────────────────────────────


class TestGenerators:
    def test_xlsx_generator(self):
        from app.modules.reporting.generators import XLSXGenerator

        gen = XLSXGenerator({"audience": "investor"})
        data = {
            "title": "Test XLSX",
            "parameters": {},
            "holdings_detail": [
                {"name": "Solar Alpha", "value": "1000000", "status": "active"},
                {"name": "Wind Beta", "value": "2000000", "status": "active"},
            ],
        }
        sections = [{"name": "holdings_detail"}]
        file_bytes, content_type = gen.generate(data, sections)
        assert len(file_bytes) > 0
        assert "spreadsheetml" in content_type
        # Verify it's a valid XLSX (ZIP magic bytes)
        assert file_bytes[:2] == b"PK"

    def test_pptx_generator(self):
        from app.modules.reporting.generators import PPTXGenerator

        gen = PPTXGenerator({"audience": "investor"})
        data = {
            "title": "Test PPTX",
            "parameters": {},
            "overview": {"metric1": "value1", "metric2": "value2"},
        }
        sections = [{"name": "overview"}]
        file_bytes, content_type = gen.generate(data, sections)
        assert len(file_bytes) > 0
        assert "presentationml" in content_type
        assert file_bytes[:2] == b"PK"

    def test_pdf_generator(self):
        from app.modules.reporting.generators import PDFGenerator

        gen = PDFGenerator({"audience": "investor"}, {"org_name": "Test Org"})
        data = {
            "title": "Test PDF",
            "parameters": {},
            "summary": {"total_investment": "$10M", "irr": "12.5%"},
        }
        sections = [{"name": "summary"}]
        file_bytes, content_type = gen.generate(data, sections)
        assert len(file_bytes) > 0
        assert content_type == "text/html"
        html = file_bytes.decode("utf-8")
        assert "Test PDF" in html
        assert "Test Org" in html
