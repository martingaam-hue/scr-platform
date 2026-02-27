"""
ValuationEngine — all financial calculations are deterministic Python.
No LLMs are used here. See ai_assistant.py for narrative / assumption suggestions.
"""

from __future__ import annotations

from app.modules.valuation.schemas import (
    BlendedBreakdownItem,
    BlendedParams,
    BlendedResult,
    ComparableParams,
    ComparableResult,
    DCFParams,
    DCFResult,
    MultipleResult,
    ReplacementCostParams,
    ReplacementResult,
    SensitivityMatrix,
    SensitivityRequest,
    YearlyPV,
)


class ValuationEngine:
    """Pure-Python deterministic valuation calculations."""

    # ── DCF ──────────────────────────────────────────────────────────────────

    def dcf_valuation(self, params: DCFParams) -> DCFResult:
        """
        Discounted Cash Flow valuation.

        Year-by-year PV is summed to obtain NPV.
        Terminal value uses Gordon Growth Model (TV = CF_n × (1+g) / (r−g))
        or Exit Multiple (TV = CF_n × multiple), discounted back to year 0.
        """
        r = float(params.discount_rate)
        g = float(params.terminal_growth_rate)
        cash_flows = [float(cf) for cf in params.cash_flows]
        n = len(cash_flows)

        # Year-by-year present values
        year_pvs: list[YearlyPV] = []
        npv = 0.0
        for t, cf in enumerate(cash_flows, start=1):
            pv = cf / (1 + r) ** t
            year_pvs.append(YearlyPV(year=t, cash_flow=round(cf, 2), pv=round(pv, 2)))
            npv += pv

        # Terminal value
        last_cf = cash_flows[-1]
        if params.terminal_method == "gordon":
            if r <= g:
                raise ValueError(
                    f"Discount rate ({r:.1%}) must exceed terminal growth rate ({g:.1%}) "
                    "for the Gordon Growth Model."
                )
            tv = last_cf * (1 + g) / (r - g)
        else:  # exit_multiple — validated in schema
            tv = last_cf * float(params.exit_multiple)  # type: ignore[arg-type]

        terminal_pv = tv / (1 + r) ** n

        ev = npv + terminal_pv
        eq = ev - float(params.net_debt)
        tv_pct = round(terminal_pv / ev * 100, 1) if ev else 0.0

        return DCFResult(
            enterprise_value=round(ev, 2),
            equity_value=round(eq, 2),
            npv=round(npv, 2),
            terminal_value=round(tv, 2),
            terminal_pv=round(terminal_pv, 2),
            tv_as_pct_of_ev=tv_pct,
            year_by_year_pv=year_pvs,
            discount_rate=r,
            terminal_growth_rate=g,
        )

    # ── Comparables ──────────────────────────────────────────────────────────

    def comparable_valuation(self, params: ComparableParams) -> ComparableResult:
        """
        Comparable transactions analysis.

        For each requested multiple type, computes implied EV from subject
        metric × comp median multiple. Weighted average across all valid
        multiple types gives the central estimate.
        """
        by_multiple: dict[str, MultipleResult] = {}

        subject_map = {
            "ev_ebitda":  params.subject_ebitda,
            "ev_mw":      params.subject_capacity_mw,
            "ev_revenue": params.subject_revenue,
        }

        for mtype in params.multiple_types:
            subject_metric = subject_map.get(mtype)
            if subject_metric is None:
                continue

            implied: list[float] = []
            for comp in params.comparables:
                multiple = getattr(comp, mtype, None)
                if multiple is not None and multiple > 0:
                    implied.append(subject_metric * multiple)

            if not implied:
                continue

            implied_sorted = sorted(implied)
            mid = len(implied_sorted) // 2
            median = (
                implied_sorted[mid]
                if len(implied_sorted) % 2 == 1
                else (implied_sorted[mid - 1] + implied_sorted[mid]) / 2
            )
            by_multiple[mtype] = MultipleResult(
                implied_values=[round(v, 2) for v in implied],
                mean=round(sum(implied) / len(implied), 2),
                median=round(median, 2),
                min_val=round(min(implied), 2),
                max_val=round(max(implied), 2),
            )

        if not by_multiple:
            raise ValueError(
                "No implied values could be computed. Ensure subject metrics "
                "and comparable multiples are provided for at least one multiple type."
            )

        # Weighted average: equal weight per multiple type, then mean of means
        all_values = [v for r in by_multiple.values() for v in r.implied_values]
        wav = sum(r.mean for r in by_multiple.values()) / len(by_multiple)
        ev = round(wav, 2)
        eq = round(ev - float(params.net_debt), 2)

        return ComparableResult(
            enterprise_value=ev,
            equity_value=eq,
            by_multiple=by_multiple,
            weighted_average_value=ev,
            range_min=round(min(all_values), 2),
            range_max=round(max(all_values), 2),
        )

    # ── Replacement Cost ─────────────────────────────────────────────────────

    def replacement_cost(self, params: ReplacementCostParams) -> ReplacementResult:
        """
        Replacement cost / asset-based approach.

        Gross cost = sum(components) + land + development.
        Depreciated value = gross × (1 − depreciation_pct/100).
        """
        component_sum = sum(params.component_costs.values())
        gross = component_sum + params.land_value + params.development_costs
        dep_factor = 1.0 - float(params.depreciation_pct) / 100.0
        depreciated = gross * dep_factor

        ev = round(depreciated, 2)
        eq = round(ev - float(params.net_debt), 2)

        return ReplacementResult(
            enterprise_value=ev,
            equity_value=eq,
            gross_replacement_cost=round(gross, 2),
            depreciated_value=ev,
            component_breakdown={k: round(v, 2) for k, v in params.component_costs.items()},
        )

    # ── Blended ──────────────────────────────────────────────────────────────

    def blended_valuation(self, params: BlendedParams) -> BlendedResult:
        """
        Weighted average of multiple valuation results.

        Weights are normalised to sum to 1.0 before computing the blend.
        """
        total_weight = sum(float(c.weight) for c in params.components)
        if total_weight <= 0:
            raise ValueError("Total weight must be positive")

        breakdown: list[BlendedBreakdownItem] = []
        blended_ev = 0.0

        for comp in params.components:
            w = float(comp.weight) / total_weight
            wv = comp.enterprise_value * w
            blended_ev += wv
            breakdown.append(
                BlendedBreakdownItem(
                    method=comp.method,
                    enterprise_value=round(comp.enterprise_value, 2),
                    weight=round(w, 4),
                    weighted_value=round(wv, 2),
                )
            )

        evs = [c.enterprise_value for c in params.components]
        eq = round(blended_ev - float(params.net_debt), 2)

        return BlendedResult(
            enterprise_value=round(blended_ev, 2),
            equity_value=eq,
            blended_value=round(blended_ev, 2),
            range_min=round(min(evs), 2),
            range_max=round(max(evs), 2),
            breakdown=breakdown,
        )

    # ── Sensitivity ──────────────────────────────────────────────────────────

    def sensitivity_analysis(self, req: SensitivityRequest) -> SensitivityMatrix:
        """
        Two-variable sensitivity matrix (typically discount rate vs growth rate).

        Runs the DCF model for every (row_value, col_value) combination.
        Cells where r ≤ g (invalid Gordon model) are set to None.
        """
        base_ev = self.dcf_valuation(req.base_params).enterprise_value

        matrix: list[list[float | None]] = []
        all_vals: list[float] = []

        for rv in req.row_values:
            row: list[float | None] = []
            for cv in req.col_values:
                p = req.base_params.model_copy()
                setattr(p, req.row_variable, rv)
                setattr(p, req.col_variable, cv)
                try:
                    result = self.dcf_valuation(p)
                    val = round(result.enterprise_value, 2)
                    row.append(val)
                    all_vals.append(val)
                except ValueError:
                    row.append(None)
            matrix.append(row)

        return SensitivityMatrix(
            row_variable=req.row_variable,
            col_variable=req.col_variable,
            row_values=req.row_values,
            col_values=req.col_values,
            matrix=matrix,
            base_value=round(base_ev, 2),
            min_value=round(min(all_vals), 2) if all_vals else 0.0,
            max_value=round(max(all_vals), 2) if all_vals else 0.0,
        )
