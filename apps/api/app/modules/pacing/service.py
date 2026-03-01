"""Cashflow pacing service — J-curve projection logic."""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pacing import CashflowAssumption, CashflowProjection
from app.modules.pacing.schemas import (
    AssumptionSummary,
    CreateAssumptionRequest,
    PacingResponse,
    ProjectionRow,
    UpdateActualsRequest,
)

# Default deployment schedule: percentage of committed capital called each year.
# Years beyond investment_period_years deploy 0%.
_DEFAULT_DEPLOYMENT_PCT: dict[int, Decimal] = {
    1: Decimal("0.30"),
    2: Decimal("0.30"),
    3: Decimal("0.25"),
    4: Decimal("0.10"),
    5: Decimal("0.05"),
}

# Default distribution schedule: percentage of committed capital returned each year.
# Distributions start from year 3 and escalate.
_DEFAULT_DISTRIBUTION_PCT: dict[int, Decimal] = {
    3: Decimal("0.05"),
    4: Decimal("0.10"),
    5: Decimal("0.15"),
    6: Decimal("0.20"),
    7: Decimal("0.20"),
    8: Decimal("0.15"),
    9: Decimal("0.10"),
    10: Decimal("0.05"),
}


class PacingService:
    def __init__(self, db: AsyncSession, org_id: uuid.UUID) -> None:
        self.db = db
        self.org_id = org_id

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    async def create_assumption(self, req: CreateAssumptionRequest) -> PacingResponse:
        """Create a new CashflowAssumption and auto-generate projections for 3 scenarios."""
        # Deactivate any existing active assumption for this portfolio
        existing = await self._get_active_assumption(req.portfolio_id)
        if existing is not None:
            existing.is_active = False
            await self.db.flush()

        assumption = CashflowAssumption(
            portfolio_id=req.portfolio_id,
            org_id=self.org_id,
            committed_capital=req.committed_capital,
            investment_period_years=req.investment_period_years,
            fund_life_years=req.fund_life_years,
            optimistic_modifier=req.optimistic_modifier,
            pessimistic_modifier=req.pessimistic_modifier,
            label=req.label,
            is_active=True,
            deployment_schedule={},
            distribution_schedule={},
        )
        self.db.add(assumption)
        await self.db.flush()
        await self.db.refresh(assumption)

        projections = await self._generate_projections(assumption)
        return self._build_response(assumption, projections)

    async def get_pacing(self, portfolio_id: uuid.UUID) -> PacingResponse:
        """Load the active assumption and all projections for a portfolio."""
        assumption = await self._get_active_assumption(portfolio_id)
        if assumption is None:
            raise LookupError(f"No active pacing assumption found for portfolio {portfolio_id}")

        projections = await self._load_projections(assumption.id)
        return self._build_response(assumption, projections)

    async def update_actuals(
        self, assumption_id: uuid.UUID, req: UpdateActualsRequest, scenario: str = "base"
    ) -> ProjectionRow:
        """Update actual cashflow fields on a specific projection row."""
        assumption = await self._get_assumption_by_id(assumption_id)

        result = await self.db.execute(
            select(CashflowProjection).where(
                CashflowProjection.assumption_id == assumption_id,
                CashflowProjection.org_id == self.org_id,
                CashflowProjection.scenario == scenario,
                CashflowProjection.year == req.year,
                CashflowProjection.is_deleted.is_(False),
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise LookupError(
                f"Projection row not found for assumption {assumption_id}, "
                f"scenario={scenario}, year={req.year}"
            )

        if req.actual_contributions is not None:
            row.actual_contributions = req.actual_contributions
        if req.actual_distributions is not None:
            row.actual_distributions = req.actual_distributions
        if req.actual_nav is not None:
            row.actual_nav = req.actual_nav

        # Recompute actual_net_cashflow
        contribs = row.actual_contributions or Decimal("0")
        distribs = row.actual_distributions or Decimal("0")
        row.actual_net_cashflow = distribs - contribs

        await self.db.flush()
        await self.db.refresh(row)
        return ProjectionRow.model_validate(row)

    async def list_assumptions(self, portfolio_id: uuid.UUID) -> list[AssumptionSummary]:
        """List all (non-deleted) assumptions for a portfolio."""
        result = await self.db.execute(
            select(CashflowAssumption).where(
                CashflowAssumption.portfolio_id == portfolio_id,
                CashflowAssumption.org_id == self.org_id,
                CashflowAssumption.is_deleted.is_(False),
            )
        )
        assumptions = list(result.scalars().all())
        return [
            AssumptionSummary(
                assumption_id=str(a.id),
                portfolio_id=str(a.portfolio_id),
                committed_capital=a.committed_capital,
                fund_life_years=a.fund_life_years,
                investment_period_years=a.investment_period_years,
                optimistic_modifier=a.optimistic_modifier,
                pessimistic_modifier=a.pessimistic_modifier,
                label=a.label,
                is_active=a.is_active,
            )
            for a in assumptions
        ]

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _get_active_assumption(
        self, portfolio_id: uuid.UUID
    ) -> CashflowAssumption | None:
        result = await self.db.execute(
            select(CashflowAssumption).where(
                CashflowAssumption.portfolio_id == portfolio_id,
                CashflowAssumption.org_id == self.org_id,
                CashflowAssumption.is_active.is_(True),
                CashflowAssumption.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def _get_assumption_by_id(self, assumption_id: uuid.UUID) -> CashflowAssumption:
        result = await self.db.execute(
            select(CashflowAssumption).where(
                CashflowAssumption.id == assumption_id,
                CashflowAssumption.org_id == self.org_id,
                CashflowAssumption.is_deleted.is_(False),
            )
        )
        assumption = result.scalar_one_or_none()
        if assumption is None:
            raise LookupError(f"Assumption {assumption_id} not found")
        return assumption

    async def _load_projections(
        self, assumption_id: uuid.UUID
    ) -> list[CashflowProjection]:
        result = await self.db.execute(
            select(CashflowProjection)
            .where(
                CashflowProjection.assumption_id == assumption_id,
                CashflowProjection.org_id == self.org_id,
                CashflowProjection.is_deleted.is_(False),
            )
            .order_by(CashflowProjection.scenario, CashflowProjection.year)
        )
        return list(result.scalars().all())

    async def _generate_projections(
        self, assumption: CashflowAssumption
    ) -> list[CashflowProjection]:
        """Generate base, optimistic, and pessimistic projection rows.

        J-curve mechanics:
        - Contributions (capital calls) are NEGATIVE cashflows (money going out).
        - Distributions are POSITIVE cashflows (money coming in).
        - Net cashflow = distributions - contributions (negative early, positive later).
        - NAV = cumulative contributions deployed minus cumulative distributions returned.
        """
        capital = assumption.committed_capital
        fund_years = assumption.fund_life_years
        invest_years = assumption.investment_period_years

        scenarios = {
            "base": Decimal("1.0"),
            "optimistic": assumption.optimistic_modifier,
            "pessimistic": assumption.pessimistic_modifier,
        }

        rows: list[CashflowProjection] = []

        for scenario, modifier in scenarios.items():
            cumulative_nav = Decimal("0")

            for year in range(1, fund_years + 1):
                # --- Contributions (capital deployment) ---
                if year <= invest_years:
                    deploy_pct = _DEFAULT_DEPLOYMENT_PCT.get(year, Decimal("0"))
                else:
                    deploy_pct = Decimal("0")
                contributions = (capital * deploy_pct).quantize(Decimal("0.0001"))

                # --- Distributions ---
                dist_pct = _DEFAULT_DISTRIBUTION_PCT.get(year, Decimal("0"))
                base_distributions = (capital * dist_pct).quantize(Decimal("0.0001"))

                # Apply scenario modifier to distributions only (captures upside/downside
                # in realisation quality rather than commitment timing).
                distributions = (base_distributions * modifier).quantize(Decimal("0.0001"))

                # --- Net cashflow (investor perspective: out = negative) ---
                net_cashflow = (distributions - contributions).quantize(Decimal("0.0001"))

                # --- NAV: deployed capital not yet distributed ---
                cumulative_nav = (cumulative_nav + contributions - distributions).quantize(
                    Decimal("0.0001")
                )
                # NAV cannot go negative
                nav = max(cumulative_nav, Decimal("0"))

                proj = CashflowProjection(
                    assumption_id=assumption.id,
                    org_id=self.org_id,
                    scenario=scenario,
                    year=year,
                    projected_contributions=contributions,
                    projected_distributions=distributions,
                    projected_nav=nav,
                    projected_net_cashflow=net_cashflow,
                    actual_contributions=None,
                    actual_distributions=None,
                    actual_nav=None,
                    actual_net_cashflow=None,
                )
                self.db.add(proj)
                rows.append(proj)

        await self.db.flush()
        return rows

    def _build_response(
        self,
        assumption: CashflowAssumption,
        projections: list[CashflowProjection],
    ) -> PacingResponse:
        """Build PacingResponse, computing trough year from base scenario."""
        base_rows = [p for p in projections if p.scenario == "base"]

        trough_year: int | None = None
        trough_value: Decimal | None = None

        if base_rows:
            # Trough = year with the most negative (lowest) projected net cashflow
            min_row = min(
                base_rows,
                key=lambda r: r.projected_net_cashflow
                if r.projected_net_cashflow is not None
                else Decimal("0"),
            )
            if (
                min_row.projected_net_cashflow is not None
                and min_row.projected_net_cashflow < Decimal("0")
            ):
                trough_year = min_row.year
                trough_value = min_row.projected_net_cashflow

        projection_rows = [
            ProjectionRow(
                scenario=p.scenario,
                year=p.year,
                projected_contributions=p.projected_contributions,
                projected_distributions=p.projected_distributions,
                projected_nav=p.projected_nav,
                projected_net_cashflow=p.projected_net_cashflow,
                actual_contributions=p.actual_contributions,
                actual_distributions=p.actual_distributions,
                actual_nav=p.actual_nav,
                actual_net_cashflow=p.actual_net_cashflow,
            )
            for p in sorted(projections, key=lambda r: (r.scenario, r.year))
        ]

        return PacingResponse(
            assumption_id=str(assumption.id),
            portfolio_id=str(assumption.portfolio_id),
            committed_capital=assumption.committed_capital,
            fund_life_years=assumption.fund_life_years,
            trough_year=trough_year,
            trough_value=trough_value,
            projections=projection_rows,
        )
