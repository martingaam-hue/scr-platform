"""Tests for the LP Reporting module — metrics calculation, report lifecycle, HTML generation."""

from __future__ import annotations

import uuid
from datetime import date
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db, get_readonly_db, get_readonly_session
from app.main import app
from app.models.core import Organization, User
from app.models.enums import OrgType, UserRole
from app.models.lp_report import LPReport
from app.modules.lp_reporting import service
from app.schemas.auth import CurrentUser

# ── Constants ─────────────────────────────────────────────────────────────────

ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")

CURRENT_USER = CurrentUser(
    user_id=USER_ID,
    org_id=ORG_ID,
    role=UserRole.ADMIN,
    email="lp@example.com",
    external_auth_id="user_lp_001",
)

_MOCK_NARRATIVE = {
    "executive_summary": "Strong quarter with TVPI of 1.5x.",
    "portfolio_commentary": "Portfolio companies performing well.",
    "market_outlook": "Positive macro environment.",
    "esg_highlights": "All companies meeting ESG targets.",
}


# ── Helpers ───────────────────────────────────────────────────────────────────


def _override_auth(user: CurrentUser):
    async def _override():
        return user

    return _override


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
async def seed_data(db: AsyncSession) -> None:
    org = Organization(id=ORG_ID, name="Fund Manager", slug="fund-manager", type=OrgType.INVESTOR)
    user = User(
        id=USER_ID,
        org_id=ORG_ID,
        email="lp@example.com",
        full_name="LP Manager",
        role=UserRole.ADMIN,
        external_auth_id="user_lp_001",
        is_active=True,
    )
    db.add_all([org, user])
    await db.flush()


@pytest.fixture
async def test_client(db: AsyncSession, seed_data: None) -> AsyncClient:
    app.dependency_overrides[get_current_user] = _override_auth(CURRENT_USER)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_readonly_db] = lambda: db
    app.dependency_overrides[get_readonly_session] = lambda: db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def draft_report(db: AsyncSession, seed_data: None) -> LPReport:
    """A persisted draft report with no financial data."""
    report = LPReport(
        org_id=ORG_ID,
        report_period="Q1 2025",
        period_start=date(2025, 1, 1),
        period_end=date(2025, 3, 31),
        status="draft",
        tvpi=1.5,
        dpi=0.5,
        rvpi=1.0,
        total_invested=10_000_000.0,
        total_returned=5_000_000.0,
        total_nav=10_000_000.0,
        narrative=_MOCK_NARRATIVE,
        investments_data=[],
    )
    db.add(report)
    await db.flush()
    await db.refresh(report)
    return report


@pytest.fixture
async def review_report(db: AsyncSession, seed_data: None) -> LPReport:
    """A persisted report in review status."""
    report = LPReport(
        org_id=ORG_ID,
        report_period="Q2 2025",
        period_start=date(2025, 4, 1),
        period_end=date(2025, 6, 30),
        status="review",
        total_invested=8_000_000.0,
        narrative=_MOCK_NARRATIVE,
    )
    db.add(report)
    await db.flush()
    await db.refresh(report)
    return report


# ── Tests: Financial metric calculations ──────────────────────────────────────


def test_calculate_fund_metrics_tvpi_dpi_rvpi() -> None:
    """TVPI = (returned + NAV) / invested, DPI = returned / invested, RVPI = NAV / invested."""
    cash_flows = [
        {"date": "2023-01-01", "amount": -10_000_000.0},  # invested
        {"date": "2023-06-01", "amount": 2_000_000.0},    # distribution
    ]
    metrics = service.calculate_fund_metrics(
        cash_flows=cash_flows,
        total_invested=10_000_000.0,
        total_returned=2_000_000.0,
        total_nav=8_000_000.0,
    )
    assert metrics["tvpi"] == pytest.approx(1.0, abs=0.01)   # (2M + 8M) / 10M
    assert metrics["dpi"] == pytest.approx(0.2, abs=0.01)    # 2M / 10M
    assert metrics["rvpi"] == pytest.approx(0.8, abs=0.01)   # 8M / 10M
    assert metrics["moic"] == metrics["tvpi"]


def test_calculate_fund_metrics_no_invested_capital() -> None:
    """With zero invested capital, multiples must be None (no division by zero)."""
    metrics = service.calculate_fund_metrics(
        cash_flows=[],
        total_invested=0.0,
        total_returned=0.0,
        total_nav=0.0,
    )
    assert metrics["tvpi"] is None
    assert metrics["dpi"] is None
    assert metrics["rvpi"] is None


def test_calculate_fund_metrics_gross_irr_computed() -> None:
    """IRR should be computed from cash flows when at least two data points exist."""
    cash_flows = [
        {"date": "2020-01-01", "amount": -1_000_000.0},
        {"date": "2021-01-01", "amount": 200_000.0},
        {"date": "2022-01-01", "amount": 200_000.0},
        {"date": "2023-01-01", "amount": 200_000.0},
    ]
    metrics = service.calculate_fund_metrics(
        cash_flows=cash_flows,
        total_nav=700_000.0,
    )
    # IRR should be a finite float
    assert metrics["gross_irr"] is not None
    assert isinstance(metrics["gross_irr"], float)
    # Net IRR should be gross minus 2%
    assert metrics["net_irr"] == pytest.approx(metrics["gross_irr"] - 0.02, abs=1e-6)


# ── Tests: HTTP endpoints ──────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_create_report_happy_path_mocked_narrative(
    test_client: AsyncClient,
) -> None:
    """POST /lp-reports creates a draft report with mocked AI narrative."""
    with patch(
        "app.modules.lp_reporting.service.generate_narrative",
        new=AsyncMock(return_value=_MOCK_NARRATIVE),
    ):
        resp = await test_client.post(
            "/v1/lp-reports",
            json={
                "report_period": "Q3 2025",
                "period_start": "2025-07-01",
                "period_end": "2025-09-30",
                "total_invested": 5_000_000.0,
                "total_returned": 1_000_000.0,
                "total_nav": 4_500_000.0,
            },
        )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "draft"
    assert data["org_id"] == str(ORG_ID)
    assert data["report_period"] == "Q3 2025"
    assert data["narrative"] is not None


@pytest.mark.anyio
async def test_list_reports_org_scoped_and_paginated(
    test_client: AsyncClient,
    draft_report: LPReport,
    review_report: LPReport,
) -> None:
    """GET /lp-reports lists only this org's reports and respects pagination."""
    resp = await test_client.get("/v1/lp-reports?page=1&page_size=10")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 2
    assert data["page"] == 1
    ids = [item["id"] for item in data["items"]]
    assert str(draft_report.id) in ids
    assert str(review_report.id) in ids


@pytest.mark.anyio
async def test_get_report_returns_200_for_existing(
    test_client: AsyncClient,
    draft_report: LPReport,
) -> None:
    """GET /lp-reports/{id} returns 200 for a report owned by the current org."""
    resp = await test_client.get(f"/v1/lp-reports/{draft_report.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(draft_report.id)


@pytest.mark.anyio
async def test_get_report_returns_404_for_missing(test_client: AsyncClient) -> None:
    """GET /lp-reports/{id} returns 404 when the report does not exist."""
    resp = await test_client.get(f"/v1/lp-reports/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_approve_report_transitions_status(
    test_client: AsyncClient,
    review_report: LPReport,
    db: AsyncSession,
) -> None:
    """POST /lp-reports/{id}/approve changes status to 'approved' and records approver."""
    resp = await test_client.post(f"/v1/lp-reports/{review_report.id}/approve")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "approved"
    assert data["approved_by"] == str(USER_ID)
    assert data["approved_at"] is not None


@pytest.mark.anyio
async def test_update_report_allowed_in_draft_status(
    test_client: AsyncClient,
    draft_report: LPReport,
) -> None:
    """PUT /lp-reports/{id} succeeds when report is in draft status."""
    resp = await test_client.put(
        f"/v1/lp-reports/{draft_report.id}",
        json={
            "narrative": {
                "executive_summary": "Updated summary text.",
                "portfolio_commentary": "",
                "market_outlook": "",
                "esg_highlights": "",
            }
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["narrative"]["executive_summary"] == "Updated summary text."


@pytest.mark.anyio
async def test_update_report_rejected_when_approved(
    test_client: AsyncClient,
    db: AsyncSession,
    seed_data: None,
) -> None:
    """PUT /lp-reports/{id} returns 400 when report is in approved status (immutable)."""
    approved_report = LPReport(
        org_id=ORG_ID,
        report_period="Q4 2024",
        period_start=date(2024, 10, 1),
        period_end=date(2024, 12, 31),
        status="approved",
        narrative=_MOCK_NARRATIVE,
    )
    db.add(approved_report)
    await db.flush()

    resp = await test_client.put(
        f"/v1/lp-reports/{approved_report.id}",
        json={"narrative": {"executive_summary": "Trying to mutate approved report."}},
    )
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_generate_html_report_returns_download_url(
    test_client: AsyncClient,
    draft_report: LPReport,
) -> None:
    """POST /lp-reports/{id}/generate-pdf returns a presigned S3 URL when S3 is mocked."""
    with (
        patch(
            "app.modules.lp_reporting.service._get_s3_client"
        ) as mock_s3_factory,
    ):
        mock_s3 = mock_s3_factory.return_value
        mock_s3.put_object.return_value = {}
        mock_s3.generate_presigned_url.return_value = (
            "https://s3.example.com/lp-reports/test.html?X-Amz-Signature=abc"
        )

        resp = await test_client.post(f"/v1/lp-reports/{draft_report.id}/generate-pdf")

    assert resp.status_code == 200
    data = resp.json()
    assert "download_url" in data
    assert data["pdf_s3_key"] != ""
    assert data["generated_at"] is not None
