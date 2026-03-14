"""Tests for the impact measurement module: SDG mapping, KPIs, carbon credits, additionality."""

from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import CarbonVerificationStatus, ProjectStage, ProjectStatus, ProjectType
from app.models.financial import CarbonCredit
from app.models.projects import Project
from app.modules.impact import service as impact_service
from app.modules.impact.schemas import (
    ImpactKPIUpdateRequest,
    SDGMappingRequest,
)
from tests.conftest import SAMPLE_ORG_ID, SAMPLE_USER_ID

pytestmark = pytest.mark.asyncio


# ── RBAC bypass ───────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def bypass_rbac():
    """Bypass RBAC permission checks in all impact tests."""
    with patch("app.auth.dependencies.check_permission", return_value=True):
        yield


# ── Fixtures ──────────────────────────────────────────────────────────────────

OTHER_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000099")


async def _make_project(
    db: AsyncSession,
    org_id: uuid.UUID,
    *,
    name: str = "Solar Test Project",
    project_type: ProjectType = ProjectType.SOLAR,
    stage: ProjectStage = ProjectStage.DEVELOPMENT,
    country: str = "Kenya",
    capacity_mw: Decimal | None = Decimal("10.5"),
) -> Project:
    proj = Project(
        org_id=org_id,
        name=name,
        slug=name.lower().replace(" ", "-") + "-" + str(uuid.uuid4())[:8],
        description="Test project",
        project_type=project_type,
        status=ProjectStatus.ACTIVE,
        stage=stage,
        geography_country=country,
        geography_region="East Africa",
        total_investment_required=Decimal("5000000"),
        capacity_mw=capacity_mw,
        technology_details={},
    )
    db.add(proj)
    await db.flush()
    await db.refresh(proj)
    return proj


# ── Service-level tests ───────────────────────────────────────────────────────


async def test_get_project_impact_returns_kpi_catalogue(db: AsyncSession, sample_org):
    """Service returns all KPI catalogue entries even when no values are set."""
    proj = await _make_project(db, SAMPLE_ORG_ID)

    result = await impact_service.get_project_impact(db, proj.id, SAMPLE_ORG_ID)

    assert result.project_id == proj.id
    assert result.project_name == "Solar Test Project"
    # KPI catalogue has 15 entries; all should be present
    assert len(result.kpis) == 15
    # With capacity_mw set on the project, that KPI should be seeded automatically
    capacity_kpi = next((k for k in result.kpis if k.key == "capacity_mw"), None)
    assert capacity_kpi is not None
    assert capacity_kpi.value == pytest.approx(10.5)


async def test_update_impact_kpis_persists_values(db: AsyncSession, sample_org):
    """Updating KPIs stores them and includes them in the response."""
    proj = await _make_project(db, SAMPLE_ORG_ID)

    result = await impact_service.update_impact_kpis(
        db,
        proj.id,
        SAMPLE_ORG_ID,
        {"co2_reduction_tco2e": 25_000.0, "jobs_created_direct": 50.0},
    )

    co2_kpi = next(k for k in result.kpis if k.key == "co2_reduction_tco2e")
    jobs_kpi = next(k for k in result.kpis if k.key == "jobs_created_direct")
    assert co2_kpi.value == pytest.approx(25_000.0)
    assert jobs_kpi.value == pytest.approx(50.0)
    assert co2_kpi.category == "environment"
    assert jobs_kpi.category == "social"


async def test_update_kpi_with_none_clears_value(db: AsyncSession, sample_org):
    """Setting a KPI value to None removes it from the stored data."""
    proj = await _make_project(db, SAMPLE_ORG_ID)
    # First set a value
    await impact_service.update_impact_kpis(db, proj.id, SAMPLE_ORG_ID, {"water_saved_m3": 1000.0})
    # Then clear it
    result = await impact_service.update_impact_kpis(
        db, proj.id, SAMPLE_ORG_ID, {"water_saved_m3": None}
    )

    water_kpi = next(k for k in result.kpis if k.key == "water_saved_m3")
    assert water_kpi.value is None


async def test_update_sdg_mapping_and_retrieve(db: AsyncSession, sample_org):
    """SDG goals are stored and returned with full metadata."""
    proj = await _make_project(db, SAMPLE_ORG_ID)

    body = SDGMappingRequest(
        goals=[
            {"number": 7, "contribution_level": "primary", "description": "Clean energy"},
            {"number": 13, "contribution_level": "secondary", "description": "Climate action"},
        ]
    )
    result = await impact_service.update_sdg_mapping(db, proj.id, SAMPLE_ORG_ID, body)

    assert len(result.goals) == 2
    goal_numbers = {g.number for g in result.goals}
    assert goal_numbers == {7, 13}
    sdg7 = next(g for g in result.goals if g.number == 7)
    assert sdg7.label == "Affordable Energy"
    assert sdg7.contribution_level == "primary"


async def test_portfolio_impact_aggregates_across_projects(db: AsyncSession, sample_org):
    """Portfolio aggregation sums metrics from all org projects."""
    p1 = await _make_project(db, SAMPLE_ORG_ID, name="Project Alpha")
    p2 = await _make_project(db, SAMPLE_ORG_ID, name="Project Beta", country="Nigeria")

    await impact_service.update_impact_kpis(
        db, p1.id, SAMPLE_ORG_ID, {"co2_reduction_tco2e": 10_000.0, "jobs_created_direct": 30.0}
    )
    await impact_service.update_impact_kpis(
        db, p2.id, SAMPLE_ORG_ID, {"co2_reduction_tco2e": 20_000.0, "jobs_created_direct": 40.0}
    )

    portfolio = await impact_service.get_portfolio_impact(db, SAMPLE_ORG_ID)

    assert portfolio.total_projects >= 2
    assert portfolio.total_co2_reduction_tco2e >= 30_000.0
    assert portfolio.total_jobs_created >= 70


async def test_additionality_score_high_need_geography_solar(db: AsyncSession, sample_org):
    """Solar project in Kenya (high-need country) gets a high additionality score."""
    proj = await _make_project(db, SAMPLE_ORG_ID, country="Kenya")
    await impact_service.update_impact_kpis(
        db,
        proj.id,
        SAMPLE_ORG_ID,
        {"co2_reduction_tco2e": 60_000.0, "jobs_created_direct": 150.0},
    )

    result = await impact_service.get_additionality(db, proj.id, SAMPLE_ORG_ID)

    assert result.project_id == proj.id
    assert result.score >= 70
    assert result.rating == "high"
    assert "geographic_need" in result.breakdown
    assert result.breakdown["geographic_need"]["score"] == 25


async def test_org_scoped_access_raises_for_other_org_project(db: AsyncSession, sample_org):
    """Service raises LookupError when project belongs to a different org."""
    proj = await _make_project(db, SAMPLE_ORG_ID)

    with pytest.raises(LookupError):
        await impact_service.get_project_impact(db, proj.id, OTHER_ORG_ID)


# ── HTTP endpoint tests ───────────────────────────────────────────────────────


async def test_http_get_project_impact_returns_200(
    authenticated_client: AsyncClient, db: AsyncSession, sample_org, sample_user
):
    """GET /v1/impact/projects/{id} returns 200 with correct response shape."""
    proj = await _make_project(db, SAMPLE_ORG_ID)

    resp = await authenticated_client.get(f"/v1/impact/projects/{proj.id}")

    assert resp.status_code == 200
    data = resp.json()
    assert data["project_id"] == str(proj.id)
    assert "kpis" in data
    assert "sdg_goals" in data
    assert "additionality_score" in data
    assert isinstance(data["kpis"], list)


async def test_http_get_portfolio_impact_returns_200(
    authenticated_client: AsyncClient, db: AsyncSession, sample_org, sample_user
):
    """GET /v1/impact/portfolio returns 200 with aggregated structure."""
    await _make_project(db, SAMPLE_ORG_ID, name="Portfolio Test Project")

    resp = await authenticated_client.get("/v1/impact/portfolio")

    assert resp.status_code == 200
    data = resp.json()
    assert "total_projects" in data
    assert "total_co2_reduction_tco2e" in data
    assert "sdg_coverage" in data
    assert isinstance(data["projects"], list)


async def test_http_carbon_credit_create_and_list(
    authenticated_client: AsyncClient, db: AsyncSession, sample_org, sample_user
):
    """POST then GET /v1/impact/carbon-credits round-trips correctly."""
    proj = await _make_project(db, SAMPLE_ORG_ID)

    payload = {
        "project_id": str(proj.id),
        "registry": "Verra",
        "methodology": "VM0015",
        "vintage_year": 2024,
        "quantity_tons": "500.00",
        "verification_status": "estimated",
    }
    create_resp = await authenticated_client.post("/v1/impact/carbon-credits", json=payload)
    assert create_resp.status_code == 201
    created = create_resp.json()
    assert created["registry"] == "Verra"
    assert created["verification_status"] == "estimated"

    list_resp = await authenticated_client.get("/v1/impact/carbon-credits")
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert list_data["total"] >= 1
    credit_ids = [c["id"] for c in list_data["items"]]
    assert created["id"] in credit_ids


async def test_http_project_impact_404_for_unknown(
    authenticated_client: AsyncClient, db: AsyncSession, sample_org, sample_user
):
    """GET /v1/impact/projects/{unknown} returns 404."""
    resp = await authenticated_client.get(f"/v1/impact/projects/{uuid.uuid4()}")
    assert resp.status_code == 404
