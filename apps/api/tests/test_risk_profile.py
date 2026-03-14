"""Tests for the Risk Analysis & Compliance module — assessments, scoring, domain framework."""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import (
    AssetType,
    FundType,
    HoldingStatus,
    PortfolioStatus,
    PortfolioStrategy,
    ProjectStage,
    ProjectStatus,
    ProjectType,
    RiskAssessmentStatus,
    RiskEntityType,
    RiskProbability,
    RiskSeverity,
    RiskType,
    SFDRClassification,
)
from app.models.investors import Portfolio, PortfolioHolding, RiskAssessment
from app.models.projects import Project
from app.modules.risk import service
from app.modules.risk.schemas import RiskAssessmentCreate
from app.modules.risk.service import RiskMapper, ScenarioEngine, _risk_score
from tests.conftest import SAMPLE_ORG_ID, SAMPLE_USER_ID

pytestmark = pytest.mark.asyncio


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _make_portfolio(db: AsyncSession, org_id: uuid.UUID) -> Portfolio:
    portfolio = Portfolio(
        org_id=org_id,
        name="Risk Test Fund",
        description="",
        strategy=PortfolioStrategy.IMPACT,
        fund_type=FundType.CLOSED_END,
        target_aum=Decimal("100000000"),
        current_aum=Decimal("60000000"),
        currency="EUR",
        sfdr_classification=SFDRClassification.ARTICLE_9,
        status=PortfolioStatus.INVESTING,
    )
    db.add(portfolio)
    await db.flush()
    await db.refresh(portfolio)
    return portfolio


async def _make_project(
    db: AsyncSession,
    org_id: uuid.UUID,
    project_type: ProjectType = ProjectType.SOLAR,
    country: str = "DE",
) -> Project:
    project = Project(
        org_id=org_id,
        name=f"Project {project_type.value}",
        slug=f"project-{uuid.uuid4().hex[:8]}",
        description="",
        project_type=project_type,
        status=ProjectStatus.ACTIVE,
        stage=ProjectStage.OPERATIONAL,
        geography_country=country,
        geography_region="Europe",
        total_investment_required=Decimal("5000000"),
        currency="EUR",
    )
    db.add(project)
    await db.flush()
    return project


async def _make_holding(
    db: AsyncSession,
    portfolio_id: uuid.UUID,
    project_id: uuid.UUID | None = None,
    investment_amount: Decimal = Decimal("1000000"),
    current_value: Decimal = Decimal("1100000"),
) -> PortfolioHolding:
    holding = PortfolioHolding(
        portfolio_id=portfolio_id,
        project_id=project_id,
        asset_name=f"Asset {uuid.uuid4().hex[:6]}",
        asset_type=AssetType.EQUITY,
        investment_date=date(2023, 1, 1),
        investment_amount=investment_amount,
        current_value=current_value,
        currency="EUR",
        status=HoldingStatus.ACTIVE,
    )
    db.add(holding)
    await db.flush()
    return holding


async def _make_assessment(
    db: AsyncSession,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    entity_id: uuid.UUID,
    severity: str = "high",
    probability: str = "likely",
    risk_type: str = "market",
) -> RiskAssessment:
    data = RiskAssessmentCreate(
        entity_type="portfolio",
        entity_id=entity_id,
        risk_type=risk_type,
        severity=severity,
        probability=probability,
        description="Test risk assessment",
    )
    return await service.create_risk_assessment(db, org_id, user_id, data)


# ── Deterministic scoring formulas ────────────────────────────────────────────


def test_risk_score_severity_probability_product():
    """_risk_score returns severity_weight × probability_weight."""
    # high=3, likely=3 → 9
    assert _risk_score("high", "likely") == pytest.approx(9.0)
    # critical=4, very_likely=4 → 16
    assert _risk_score("critical", "very_likely") == pytest.approx(16.0)
    # low=1, unlikely=1 → 1
    assert _risk_score("low", "unlikely") == pytest.approx(1.0)


def test_risk_score_higher_severity_higher_score():
    """Higher severity with same probability always yields a higher score."""
    assert _risk_score("critical", "possible") > _risk_score("high", "possible")
    assert _risk_score("high", "possible") > _risk_score("medium", "possible")
    assert _risk_score("medium", "possible") > _risk_score("low", "possible")


def test_risk_score_inverted_scale_interpretation():
    """A lower score = less risk. Score range is 1-16; high severity + very likely = max 16."""
    min_score = _risk_score("low", "unlikely")
    max_score = _risk_score("critical", "very_likely")
    assert min_score == 1.0
    assert max_score == 16.0


# ── create_risk_assessment service ────────────────────────────────────────────


async def test_create_risk_assessment_persists_correctly(
    db: AsyncSession, sample_org, sample_user
):
    """create_risk_assessment stores all fields with correct enum values."""
    entity_id = uuid.uuid4()
    data = RiskAssessmentCreate(
        entity_type="project",
        entity_id=entity_id,
        risk_type="climate",
        severity="high",
        probability="likely",
        description="Flood risk for hydro project",
        mitigation="Flood barriers installed",
    )
    assessment = await service.create_risk_assessment(db, sample_org.id, sample_user.id, data)

    assert assessment.id is not None
    assert assessment.entity_type == RiskEntityType.PROJECT
    assert assessment.risk_type == RiskType.CLIMATE
    assert assessment.severity == RiskSeverity.HIGH
    assert assessment.probability == RiskProbability.LIKELY
    assert assessment.description == "Flood risk for hydro project"
    assert assessment.status == RiskAssessmentStatus.IDENTIFIED
    assert assessment.assessed_by == sample_user.id
    assert assessment.org_id == sample_org.id


async def test_create_risk_assessment_invalid_enum_raises(
    db: AsyncSession, sample_org, sample_user
):
    """Invalid enum values for severity/probability/entity_type raise ValueError."""
    with pytest.raises(ValueError):
        await service.create_risk_assessment(
            db,
            sample_org.id,
            sample_user.id,
            RiskAssessmentCreate(
                entity_type="project",
                entity_id=uuid.uuid4(),
                risk_type="market",
                severity="catastrophic",  # invalid
                probability="likely",
                description="Bad severity value",
            ),
        )


async def test_get_risk_assessments_org_scoped(db: AsyncSession, sample_org, sample_user):
    """get_risk_assessments returns only assessments belonging to the caller's org."""
    from app.models.core import Organization
    from app.models.enums import OrgType

    # Create the other org so FK constraint is satisfied
    other_org_id = uuid.uuid4()
    other_org = Organization(
        id=other_org_id,
        name="Other Risk Org",
        slug=f"other-risk-org-{other_org_id.hex[:6]}",
        type=OrgType.INVESTOR,
    )
    db.add(other_org)
    await db.flush()

    entity_id = uuid.uuid4()

    # Own assessment
    await _make_assessment(db, sample_org.id, sample_user.id, entity_id)

    # Another org's assessment directly inserted
    other_assessment = RiskAssessment(
        org_id=other_org_id,
        entity_type=RiskEntityType.PROJECT,
        entity_id=entity_id,
        risk_type=RiskType.MARKET,
        severity=RiskSeverity.LOW,
        probability=RiskProbability.UNLIKELY,
        description="Other org risk",
        status=RiskAssessmentStatus.IDENTIFIED,
        assessed_by=SAMPLE_USER_ID,
    )
    db.add(other_assessment)
    await db.flush()

    results = await service.get_risk_assessments(db, sample_org.id, None, None)
    result_ids = {r.id for r in results}
    assert other_assessment.id not in result_ids
    for r in results:
        assert r.org_id == sample_org.id


async def test_get_risk_assessments_filtered_by_entity(
    db: AsyncSession, sample_org, sample_user
):
    """get_risk_assessments with entity_type + entity_id filter narrows results."""
    pid1 = uuid.uuid4()
    pid2 = uuid.uuid4()

    await _make_assessment(db, sample_org.id, sample_user.id, pid1, risk_type="climate")
    await _make_assessment(db, sample_org.id, sample_user.id, pid2, risk_type="market")
    await db.flush()

    results = await service.get_risk_assessments(db, sample_org.id, "portfolio", pid1)
    assert all(r.entity_id == pid1 for r in results)
    assert len(results) == 1


# ── Auto risk identification ───────────────────────────────────────────────────


async def test_risk_mapper_detects_sector_concentration(db: AsyncSession, sample_org):
    """RiskMapper flags concentration risk when one sector > 25% of portfolio."""
    portfolio = await _make_portfolio(db, sample_org.id)
    solar_project = await _make_project(db, sample_org.id, ProjectType.SOLAR)

    # 70% in solar
    h1 = await _make_holding(
        db, portfolio.id, solar_project.id,
        investment_amount=Decimal("700000"), current_value=Decimal("700000"),
    )
    wind_project = await _make_project(db, sample_org.id, ProjectType.WIND)
    h2 = await _make_holding(
        db, portfolio.id, wind_project.id,
        investment_amount=Decimal("300000"), current_value=Decimal("300000"),
    )
    await db.flush()

    holdings = [h1, h2]
    projects = {solar_project.id: solar_project, wind_project.id: wind_project}

    mapper = RiskMapper()
    risks = mapper.identify_risks(holdings, projects)

    concentration_risks = [r for r in risks if r.risk_type == "concentration"]
    assert len(concentration_risks) >= 1
    descriptions = " ".join(r.description for r in concentration_risks)
    assert "solar" in descriptions.lower()


async def test_risk_mapper_detects_liquidity_risk(db: AsyncSession, sample_org):
    """RiskMapper flags liquidity risk for infrastructure-heavy portfolios."""
    portfolio = await _make_portfolio(db, sample_org.id)
    holdings = []
    for _ in range(5):
        h = await _make_holding(db, portfolio.id)
        holdings.append(h)
    await db.flush()

    mapper = RiskMapper()
    risks = mapper.identify_risks(holdings, {})

    liquidity_risks = [r for r in risks if r.risk_type == "liquidity"]
    assert len(liquidity_risks) >= 1


# ── Scenario engine (deterministic) ───────────────────────────────────────────


async def test_scenario_interest_rate_shock_reduces_nav(db: AsyncSession, sample_org):
    """Interest rate shock scenario reduces NAV by approximately duration × rate change."""
    portfolio = await _make_portfolio(db, sample_org.id)
    h = await _make_holding(
        db, portfolio.id,
        investment_amount=Decimal("1000000"), current_value=Decimal("1000000"),
    )
    await db.flush()

    engine = ScenarioEngine()
    result = engine.run_scenario(
        [h],
        None,
        "interest_rate_shock",
        {"basis_points": 200, "duration_years": 10},
    )

    assert result.nav_after < result.nav_before
    assert result.nav_delta < 0
    assert "interest rate shock" in result.narrative.lower()


# ── HTTP endpoint tests ────────────────────────────────────────────────────────


async def test_api_create_risk_assessment_returns_201(
    authenticated_client, sample_org, sample_user
):
    """POST /v1/risk/assess returns 201 with the created assessment."""
    payload = {
        "entity_type": "project",
        "entity_id": str(uuid.uuid4()),
        "risk_type": "regulatory",
        "severity": "medium",
        "probability": "possible",
        "description": "Pending permitting decision",
    }
    resp = await authenticated_client.post("/v1/risk/assess", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    assert body["severity"] == "medium"
    assert body["risk_type"] == "regulatory"
    assert body["status"] == "identified"


async def test_api_list_risk_assessments_returns_200(
    authenticated_client, db: AsyncSession, sample_org, sample_user
):
    """GET /v1/risk/assessments returns a list of assessments for the org."""
    entity_id = uuid.uuid4()
    await _make_assessment(db, sample_org.id, sample_user.id, entity_id)
    await db.flush()

    resp = await authenticated_client.get("/v1/risk/assessments")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert len(resp.json()) >= 1


async def test_api_risk_dashboard_404_for_unknown_portfolio(authenticated_client):
    """GET /v1/risk/dashboard/{id} returns 404 for a portfolio that doesn't exist."""
    resp = await authenticated_client.get(f"/v1/risk/dashboard/{uuid.uuid4()}")
    assert resp.status_code == 404
