"""Value Quantifier service — pure deterministic financial KPI computation."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.financial import CarbonCredit
from app.models.projects import Project
from app.modules.value_quantifier import calculator as calc
from app.modules.value_quantifier.schemas import (
    ValueKPI,
    ValueQuantifierRequest,
    ValueQuantifierResponse,
)


def _fmt_currency(value: float) -> str:
    """Format a dollar value with M/B suffix."""
    if abs(value) >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B"
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:.2f}M"
    if abs(value) >= 1_000:
        return f"${value / 1_000:.1f}K"
    return f"${value:.0f}"


async def calculate_value(
    db: AsyncSession,
    org_id: uuid.UUID,
    req: ValueQuantifierRequest,
) -> ValueQuantifierResponse:
    """Run deterministic financial KPI calculations for a project."""
    # 1. Load project
    stmt = select(Project).where(
        Project.id == req.project_id,
        Project.org_id == org_id,
        Project.is_deleted.is_(False),
    )
    project: Project | None = (await db.execute(stmt)).scalar_one_or_none()
    if not project:
        raise LookupError("Project not found")

    # 2. Load latest CarbonCredit
    cc_stmt = (
        select(CarbonCredit)
        .where(
            CarbonCredit.project_id == req.project_id,
            CarbonCredit.org_id == org_id,
        )
        .order_by(CarbonCredit.created_at.desc())
        .limit(1)
    )
    carbon_credit: CarbonCredit | None = (await db.execute(cc_stmt)).scalar_one_or_none()

    # 3. Compute inputs
    capacity_mw = float(project.capacity_mw or 10.0)
    project_type = project.project_type.value if project.project_type else "default"

    capacity_factor = req.capacity_factor or calc.CAPACITY_FACTORS.get(
        project_type, calc.CAPACITY_FACTORS["default"]
    )
    energy_mwh_annual = capacity_mw * capacity_factor * 8760  # MW * CF * hours/year

    capex = (
        req.capex_usd
        or float(project.total_investment_required or 0)
        or capacity_mw * 1_200_000
    )
    opex_annual = req.opex_annual_usd or capex * 0.015  # 1.5% of capex

    # Revenue: energy_mwh_annual * $/kWh * 1000 kWh/MWh
    revenue_annual = req.revenue_annual_usd or (
        energy_mwh_annual * req.electricity_price_kwh * 1000
    )

    ebitda = revenue_annual - opex_annual

    # Annual debt service (annuity formula)
    r = req.interest_rate
    n = req.loan_term_years
    debt_principal = capex * req.debt_ratio
    if r > 0 and n > 0:
        annual_debt_service = debt_principal * (r * (1 + r) ** n) / ((1 + r) ** n - 1)
    else:
        annual_debt_service = debt_principal / n if n > 0 else 0.0

    # 4. Build cash flows
    annual_net = revenue_annual - opex_annual
    cash_flows = [-capex] + [annual_net] * req.project_lifetime_years

    # 5. Compute financial metrics
    irr = calc.calculate_irr(cash_flows)
    npv = calc.calculate_npv(cash_flows, req.discount_rate)
    payback = calc.calculate_payback(capex, annual_net)
    dscr = calc.calculate_dscr(ebitda, annual_debt_service)
    lcoe = calc.calculate_lcoe(
        capex=capex,
        opex_annual=opex_annual,
        energy_output_mwh_annual=energy_mwh_annual,
        discount_rate=req.discount_rate,
        project_lifetime=req.project_lifetime_years,
    )

    # 6. Carbon savings
    if carbon_credit:
        carbon_savings = float(carbon_credit.quantity_tons)
    else:
        country = (project.geography_country or "").upper()
        region_key = country[:2] if len(country) >= 2 else "default"
        emission_factor = calc.GRID_EMISSION_FACTORS.get(
            region_key, calc.GRID_EMISSION_FACTORS["default"]
        )
        carbon_savings = round(energy_mwh_annual * emission_factor, 1)

    # 7. Jobs
    jobs = req.jobs_created or calc.estimate_jobs_created(capacity_mw, project_type)

    # 8. Build KPI list with quality ratings
    kpis: list[ValueKPI] = []

    # IRR
    irr_quality = "neutral"
    if irr is not None:
        if irr > 12:
            irr_quality = "good"
        elif irr >= 8:
            irr_quality = "warning"
        else:
            irr_quality = "bad"
    kpis.append(ValueKPI(
        label="IRR",
        value=f"{irr:.1f}%" if irr is not None else "N/A",
        raw_value=irr,
        unit="%",
        description="Internal Rate of Return — annualised % return on investment",
        quality=irr_quality,
    ))

    # NPV
    npv_quality = "good" if npv > 0 else "bad"
    kpis.append(ValueKPI(
        label="NPV",
        value=_fmt_currency(npv),
        raw_value=round(npv, 2),
        unit="USD",
        description=f"Net Present Value at {req.discount_rate * 100:.0f}% discount rate",
        quality=npv_quality,
    ))

    # Payback
    payback_quality = "neutral"
    if payback is not None:
        if payback < 8:
            payback_quality = "good"
        elif payback <= 15:
            payback_quality = "warning"
        else:
            payback_quality = "bad"
    kpis.append(ValueKPI(
        label="Payback Period",
        value=f"{payback:.1f} yrs" if payback is not None else "N/A",
        raw_value=payback,
        unit="years",
        description="Simple payback period (CAPEX / annual net cash flow)",
        quality=payback_quality,
    ))

    # DSCR
    dscr_quality = "neutral"
    if dscr is not None:
        if dscr > 1.25:
            dscr_quality = "good"
        elif dscr >= 1.0:
            dscr_quality = "warning"
        else:
            dscr_quality = "bad"
    kpis.append(ValueKPI(
        label="DSCR",
        value=f"{dscr:.2f}x" if dscr is not None else "N/A",
        raw_value=dscr,
        unit="x",
        description="Debt Service Coverage Ratio — EBITDA / annual debt service",
        quality=dscr_quality,
    ))

    # LCOE ($/MWh)
    lcoe_quality = "neutral"
    lcoe_mwh = round(lcoe * 1000, 2) if lcoe is not None else None  # convert $/kWh → $/MWh
    if lcoe_mwh is not None:
        if lcoe_mwh < 50:
            lcoe_quality = "good"
        elif lcoe_mwh <= 80:
            lcoe_quality = "warning"
        else:
            lcoe_quality = "bad"
    kpis.append(ValueKPI(
        label="LCOE",
        value=f"${lcoe_mwh:.1f}/MWh" if lcoe_mwh is not None else "N/A",
        raw_value=lcoe_mwh,
        unit="$/MWh",
        description="Levelized Cost of Energy — lifetime discounted cost per MWh produced",
        quality=lcoe_quality,
    ))

    # Carbon savings
    kpis.append(ValueKPI(
        label="Carbon Savings",
        value=f"{carbon_savings:,.0f} tCO₂e/yr",
        raw_value=carbon_savings,
        unit="tCO₂e/yr",
        description="Annual greenhouse gas emissions avoided vs. grid baseline",
        quality="good" if carbon_savings > 0 else "neutral",
    ))

    # 9. Assumptions summary
    assumptions: dict[str, float | int | str] = {
        "capacity_mw": capacity_mw,
        "capacity_factor": capacity_factor,
        "energy_mwh_annual": round(energy_mwh_annual, 0),
        "capex_usd": round(capex, 0),
        "opex_annual_usd": round(opex_annual, 0),
        "revenue_annual_usd": round(revenue_annual, 0),
        "discount_rate_pct": req.discount_rate * 100,
        "debt_ratio_pct": req.debt_ratio * 100,
        "interest_rate_pct": req.interest_rate * 100,
        "loan_term_years": req.loan_term_years,
        "project_lifetime_years": req.project_lifetime_years,
        "electricity_price_kwh": req.electricity_price_kwh,
        "project_type": project_type,
    }

    return ValueQuantifierResponse(
        project_id=project.id,
        project_name=project.name,
        irr=irr,
        npv=round(npv, 2),
        payback_years=payback,
        dscr=dscr,
        lcoe=lcoe_mwh,
        carbon_savings_tons=carbon_savings,
        jobs_created=jobs,
        total_investment=round(capex, 2),
        kpis=kpis,
        assumptions=assumptions,
    )
