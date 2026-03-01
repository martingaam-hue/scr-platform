"""Financial template service — DCF computation using numpy-financial."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.financial_templates import FinancialTemplate

try:
    import numpy_financial as npf
    _HAS_NPF = True
except ImportError:
    _HAS_NPF = False


class FinancialTemplateService:
    def __init__(self, db: AsyncSession, org_id: uuid.UUID):
        self.db = db
        self.org_id = org_id

    async def list_templates(self, taxonomy_code: str | None = None) -> list[FinancialTemplate]:
        stmt = select(FinancialTemplate).where(
            FinancialTemplate.is_deleted.is_(False),
            or_(
                FinancialTemplate.org_id.is_(None),
                FinancialTemplate.org_id == self.org_id,
            ),
        )
        if taxonomy_code:
            stmt = stmt.where(FinancialTemplate.taxonomy_code == taxonomy_code)
        stmt = stmt.order_by(FinancialTemplate.is_system.desc(), FinancialTemplate.name)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_template(self, template_id: uuid.UUID) -> FinancialTemplate | None:
        result = await self.db.execute(
            select(FinancialTemplate).where(
                FinancialTemplate.id == template_id,
                FinancialTemplate.is_deleted.is_(False),
                or_(
                    FinancialTemplate.org_id.is_(None),
                    FinancialTemplate.org_id == self.org_id,
                ),
            )
        )
        return result.scalar_one_or_none()

    async def compute_dcf(self, template_id: uuid.UUID, overrides: dict[str, Any]) -> dict:
        template = await self.get_template(template_id)
        if not template:
            raise ValueError("Template not found")

        # Merge defaults with overrides
        assumptions = {}
        for key, spec in (template.assumptions or {}).items():
            if isinstance(spec, dict):
                assumptions[key] = overrides.get(key, spec.get("default"))
            else:
                assumptions[key] = overrides.get(key, spec)

        project_life = int(assumptions.get("project_life_years", 25))
        discount_rate = float(assumptions.get("discount_rate", 0.07))
        debt_pct = float(assumptions.get("debt_pct", 0.70))
        capex_total = self._compute_capex(assumptions)

        # Build annual revenue, opex, net cashflow
        annual_cashflows = self._build_cashflows(assumptions, template, project_life, capex_total)

        # Equity cashflows (subtract debt service from levered perspective)
        equity_investment = capex_total * (1 - debt_pct)
        debt_amount = capex_total * debt_pct
        # Simplified: assume 5% interest, 15-year debt tenor, annuity
        debt_service = self._annuity(debt_amount, 0.05, min(15, project_life))

        levered_cashflows = [-float(equity_investment)]
        for i, cf in enumerate(annual_cashflows[1:], start=1):
            lev = cf - (debt_service if i <= min(15, project_life) else 0)
            levered_cashflows.append(lev)

        npv_val = self._npv(discount_rate, annual_cashflows)
        irr_val = self._irr(levered_cashflows)

        return {
            "npv": Decimal(str(round(npv_val, 2))),
            "irr": Decimal(str(round(irr_val, 6))) if irr_val is not None else None,
            "annual_cashflows": [Decimal(str(round(cf, 2))) for cf in annual_cashflows],
            "levered_cashflows": [Decimal(str(round(cf, 2))) for cf in levered_cashflows],
            "assumptions_used": assumptions,
        }

    def _compute_capex(self, assumptions: dict) -> float:
        # Try capacity_mw * capex_per_mw, or capacity_mwh * capex_per_mwh
        if "capacity_mw" in assumptions and "capex_per_mw" in assumptions:
            return float(assumptions["capacity_mw"]) * float(assumptions["capex_per_mw"])
        if "capacity_mwh" in assumptions and "capex_per_mwh" in assumptions:
            return float(assumptions["capacity_mwh"]) * float(assumptions["capex_per_mwh"])
        return 0.0

    def _build_cashflows(self, assumptions: dict, template: FinancialTemplate, years: int, capex: float) -> list[float]:
        """Build year 0..N cashflow list. Year 0 = -capex, years 1..N = revenue - opex."""
        cashflows = [-capex]  # year 0 capex outflow

        base_revenue = self._compute_annual_revenue(assumptions)

        # Opex
        capacity_mw = float(assumptions.get("capacity_mw", assumptions.get("capacity_mwh", 1)))
        opex_field = next((k for k in assumptions if "opex" in k), None)
        annual_opex = float(assumptions.get(opex_field, 0)) * capacity_mw if opex_field else base_revenue * 0.1

        degradation = float(assumptions.get("degradation_pct_yr", 0.005))

        for year in range(1, years + 1):
            rev = base_revenue * ((1 - degradation) ** (year - 1))
            net = rev - annual_opex
            cashflows.append(net)

        return cashflows

    def _compute_annual_revenue(self, assumptions: dict) -> float:
        """Simple heuristic-based revenue from assumptions dict."""
        # Solar utility: capacity_mw * 1000 * irradiance / 1000 * performance_ratio * ppa_price
        if all(k in assumptions for k in ["capacity_mw", "p50_irradiance_kwh_m2", "performance_ratio", "ppa_price_eur_mwh"]):
            return (float(assumptions["capacity_mw"]) * 1000
                    * float(assumptions["p50_irradiance_kwh_m2"]) / 1000
                    * float(assumptions["performance_ratio"])
                    * float(assumptions["ppa_price_eur_mwh"]))
        # Wind: capacity_mw * 8760 * capacity_factor * ppa_price
        if all(k in assumptions for k in ["capacity_mw", "capacity_factor", "ppa_price_eur_mwh"]):
            return (float(assumptions["capacity_mw"]) * 8760
                    * float(assumptions["capacity_factor"])
                    * float(assumptions["ppa_price_eur_mwh"]))
        # BESS: capacity_mwh * cycles_per_day * 365 * revenue_per_mwh_cycle
        if all(k in assumptions for k in ["capacity_mwh", "cycles_per_day", "revenue_per_mwh_cycle"]):
            return (float(assumptions["capacity_mwh"])
                    * float(assumptions["cycles_per_day"]) * 365
                    * float(assumptions["revenue_per_mwh_cycle"]))
        return 0.0

    def _annuity(self, principal: float, rate: float, years: int) -> float:
        if rate == 0:
            return principal / years
        return principal * rate / (1 - (1 + rate) ** -years)

    def _npv(self, rate: float, cashflows: list[float]) -> float:
        if _HAS_NPF:
            return float(npf.npv(rate, cashflows))
        # Manual NPV
        return sum(cf / (1 + rate) ** i for i, cf in enumerate(cashflows))

    def _irr(self, cashflows: list[float]) -> float | None:
        if _HAS_NPF:
            try:
                val = npf.irr(cashflows)
                import math
                if math.isnan(val) or math.isinf(val):
                    return None
                return float(val)
            except Exception:
                return None
        return None
