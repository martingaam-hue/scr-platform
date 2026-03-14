"""Tests for the financial_templates module: template catalog, DCF computation, HTTP endpoints."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.financial_templates import FinancialTemplate
from app.models.taxonomy import IndustryTaxonomy
from app.modules.financial_templates.service import FinancialTemplateService
from tests.conftest import SAMPLE_ORG_ID

pytestmark = pytest.mark.asyncio

OTHER_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000099")


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _make_taxonomy(db: AsyncSession, code: str = "RE.SOLAR") -> IndustryTaxonomy:
    tax = IndustryTaxonomy(
        code=code,
        name="Solar PV",
        level=3,
        is_leaf=True,
    )
    db.add(tax)
    await db.flush()
    return tax


async def _make_template(
    db: AsyncSession,
    taxonomy_code: str,
    *,
    name: str = "Solar DCF Template",
    org_id: uuid.UUID | None = None,
    is_system: bool = False,
    assumptions: dict | None = None,
) -> FinancialTemplate:
    t = FinancialTemplate(
        taxonomy_code=taxonomy_code,
        org_id=org_id,
        name=name,
        description="Standard solar DCF model",
        is_system=is_system,
        assumptions=assumptions
        or {
            "capacity_mw": {"default": 50, "min": 1, "max": 500, "unit": "MW"},
            "capex_per_mw": {"default": 800_000, "min": 500_000, "max": 1_200_000, "unit": "EUR/MW"},
            "ppa_price_eur_mwh": {"default": 55, "min": 30, "max": 100, "unit": "EUR/MWh"},
            "p50_irradiance_kwh_m2": {"default": 1800, "unit": "kWh/m²/yr"},
            "performance_ratio": {"default": 0.80, "min": 0.70, "max": 0.90},
            "discount_rate": {"default": 0.07, "min": 0.04, "max": 0.15},
            "project_life_years": {"default": 25, "min": 10, "max": 40},
            "debt_pct": {"default": 0.70, "min": 0.50, "max": 0.80},
            "degradation_pct_yr": {"default": 0.005},
            "opex_per_mw": {"default": 12_000, "unit": "EUR/MW/yr"},
        },
        revenue_formula={"type": "solar_ppa"},
        cashflow_model={"type": "levered"},
    )
    db.add(t)
    await db.flush()
    await db.refresh(t)
    return t


# ── Service-level tests ───────────────────────────────────────────────────────


async def test_list_templates_returns_system_and_org_templates(
    db: AsyncSession, sample_org, sample_user
):
    """list_templates returns both system (NULL org_id) and org-specific templates."""
    tax = await _make_taxonomy(db, "RE.SOLAR.LIST")
    sys_tmpl = await _make_template(db, tax.code, name="System Template", is_system=True)
    org_tmpl = await _make_template(
        db, tax.code, name="Org Template", org_id=SAMPLE_ORG_ID, is_system=False
    )

    svc = FinancialTemplateService(db, SAMPLE_ORG_ID)
    templates = await svc.list_templates()

    ids = [t.id for t in templates]
    assert sys_tmpl.id in ids
    assert org_tmpl.id in ids


async def test_list_templates_excludes_other_org_templates(
    db: AsyncSession, sample_org, sample_user
):
    """list_templates does not return templates belonging to another org."""
    from app.models.core import Organization
    from app.models.enums import OrgType

    other_org = Organization(
        id=OTHER_ORG_ID,
        name="Other Org FT",
        slug="other-org-ft-scope",
        type=OrgType.INVESTOR,
    )
    db.add(other_org)
    await db.flush()

    tax = await _make_taxonomy(db, "RE.SOLAR.SCOPE")
    other_tmpl = await _make_template(db, tax.code, name="Other Org Template", org_id=OTHER_ORG_ID)

    svc = FinancialTemplateService(db, SAMPLE_ORG_ID)
    templates = await svc.list_templates()

    ids = [t.id for t in templates]
    assert other_tmpl.id not in ids


async def test_list_templates_filtered_by_taxonomy_code(
    db: AsyncSession, sample_org, sample_user
):
    """list_templates(taxonomy_code=...) returns only templates for that code."""
    tax_solar = await _make_taxonomy(db, "RE.SOLAR.FILT")
    tax_wind = await _make_taxonomy(db, "RE.WIND.FILT")
    solar_tmpl = await _make_template(db, tax_solar.code, name="Solar Only")
    wind_tmpl = await _make_template(db, tax_wind.code, name="Wind Only")

    svc = FinancialTemplateService(db, SAMPLE_ORG_ID)
    results = await svc.list_templates(taxonomy_code=tax_solar.code)

    ids = [t.id for t in results]
    assert solar_tmpl.id in ids
    assert wind_tmpl.id not in ids


async def test_get_template_returns_correct_template(db: AsyncSession, sample_org, sample_user):
    """get_template returns the template when accessible by org."""
    tax = await _make_taxonomy(db, "RE.SOLAR.GET")
    tmpl = await _make_template(db, tax.code, name="Retrievable Template", is_system=True)

    svc = FinancialTemplateService(db, SAMPLE_ORG_ID)
    result = await svc.get_template(tmpl.id)

    assert result is not None
    assert result.id == tmpl.id
    assert result.name == "Retrievable Template"


async def test_get_template_returns_none_for_other_org(db: AsyncSession, sample_org, sample_user):
    """get_template returns None when the template belongs to a different org."""
    from app.models.core import Organization
    from app.models.enums import OrgType

    other_org = Organization(
        id=OTHER_ORG_ID,
        name="Other Org FT",
        slug="other-org-ft-none",
        type=OrgType.INVESTOR,
    )
    db.add(other_org)
    await db.flush()

    tax = await _make_taxonomy(db, "RE.SOLAR.NONE")
    other_tmpl = await _make_template(db, tax.code, name="Hidden Template", org_id=OTHER_ORG_ID)

    svc = FinancialTemplateService(db, SAMPLE_ORG_ID)
    result = await svc.get_template(other_tmpl.id)

    assert result is None


async def test_compute_dcf_solar_produces_npv_and_cashflows(
    db: AsyncSession, sample_org, sample_user
):
    """compute_dcf returns npv, irr, and cashflow lists of correct length."""
    tax = await _make_taxonomy(db, "RE.SOLAR.DCF")
    tmpl = await _make_template(db, tax.code, name="Solar DCF Compute", is_system=True)

    svc = FinancialTemplateService(db, SAMPLE_ORG_ID)
    result = await svc.compute_dcf(
        tmpl.id,
        overrides={
            "capacity_mw": 50,
            "capex_per_mw": 800_000,
            "ppa_price_eur_mwh": 55,
            "p50_irradiance_kwh_m2": 1800,
            "performance_ratio": 0.80,
            "project_life_years": 25,
        },
    )

    assert "npv" in result
    assert isinstance(result["npv"], Decimal)
    assert "annual_cashflows" in result
    # year 0 + 25 years = 26 entries
    assert len(result["annual_cashflows"]) == 26
    assert "levered_cashflows" in result
    assert len(result["levered_cashflows"]) == 26
    # Year 0 should be negative (capex outflow)
    assert result["annual_cashflows"][0] < 0
    assert "assumptions_used" in result


async def test_compute_dcf_raises_for_unknown_template(
    db: AsyncSession, sample_org, sample_user
):
    """compute_dcf raises ValueError when template_id does not exist."""
    svc = FinancialTemplateService(db, SAMPLE_ORG_ID)

    with pytest.raises(ValueError, match="Template not found"):
        await svc.compute_dcf(uuid.uuid4(), overrides={})


# ── HTTP endpoint tests ───────────────────────────────────────────────────────


async def test_http_list_templates_returns_200(
    authenticated_client: AsyncClient, db: AsyncSession, sample_org, sample_user
):
    """GET /v1/financial-templates returns 200 with a list."""
    tax = await _make_taxonomy(db, "RE.SOLAR.HTTP")
    await _make_template(db, tax.code, name="HTTP List Template", is_system=True)

    resp = await authenticated_client.get("/v1/financial-templates")

    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    names = [t["name"] for t in data]
    assert "HTTP List Template" in names


async def test_http_get_template_returns_404_for_unknown(
    authenticated_client: AsyncClient, db: AsyncSession, sample_org, sample_user
):
    """GET /v1/financial-templates/{unknown_id} returns 404."""
    resp = await authenticated_client.get(f"/v1/financial-templates/{uuid.uuid4()}")
    assert resp.status_code == 404


async def test_http_compute_dcf_returns_npv(
    authenticated_client: AsyncClient, db: AsyncSession, sample_org, sample_user
):
    """POST /v1/financial-templates/{id}/compute returns a DCFResult with npv."""
    tax = await _make_taxonomy(db, "RE.SOLAR.COMP")
    tmpl = await _make_template(db, tax.code, name="HTTP Compute Solar", is_system=True)

    resp = await authenticated_client.post(
        f"/v1/financial-templates/{tmpl.id}/compute",
        json={
            "overrides": {
                "capacity_mw": 20,
                "capex_per_mw": 900_000,
                "ppa_price_eur_mwh": 60,
                "p50_irradiance_kwh_m2": 1700,
                "performance_ratio": 0.78,
                "project_life_years": 20,
            }
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert "npv" in data
    assert "annual_cashflows" in data
    assert len(data["annual_cashflows"]) == 21  # year 0 + 20 years
