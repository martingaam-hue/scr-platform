"""Unit tests for ValuationEngine — pure Python, no DB required."""

import pytest

from app.modules.valuation.engine import ValuationEngine
from app.modules.valuation.schemas import (
    BlendedComponent,
    BlendedParams,
    ComparableCompany,
    ComparableParams,
    DCFParams,
    ReplacementCostParams,
    SensitivityRequest,
)

engine = ValuationEngine()


# ── DCF ───────────────────────────────────────────────────────────────────────


class TestDCFValuation:
    def test_single_cashflow_gordon_growth(self):
        """Single CF=100, r=10%, g=2% → EV=1250 exactly."""
        # TV = 100 * 1.02 / 0.08 = 1275; Terminal PV = 1275 / 1.1 = 1159.09
        # Year-1 PV = 100 / 1.1 = 90.91; EV = 90.91 + 1159.09 = 1250.0
        params = DCFParams(
            cash_flows=[100.0],
            discount_rate=0.10,
            terminal_growth_rate=0.02,
            terminal_method="gordon",
        )
        result = engine.dcf_valuation(params)
        assert result.enterprise_value == pytest.approx(1250.0, rel=1e-4)
        assert result.equity_value == pytest.approx(1250.0, rel=1e-4)  # net_debt=0

    def test_year_by_year_pv_values(self):
        """Year-by-year PVs must match manual discount calculations."""
        params = DCFParams(
            cash_flows=[100.0, 200.0, 300.0],
            discount_rate=0.10,
            terminal_growth_rate=0.02,
        )
        result = engine.dcf_valuation(params)
        assert len(result.year_by_year_pv) == 3
        assert result.year_by_year_pv[0].pv == pytest.approx(100.0 / 1.1, rel=1e-3)
        assert result.year_by_year_pv[1].pv == pytest.approx(200.0 / 1.21, rel=1e-3)
        assert result.year_by_year_pv[2].pv == pytest.approx(300.0 / 1.331, rel=1e-3)

    def test_exit_multiple_terminal_value(self):
        """Exit-multiple TV = last_CF × multiple, discounted back."""
        params = DCFParams(
            cash_flows=[100.0],
            discount_rate=0.10,
            terminal_method="exit_multiple",
            exit_multiple=10.0,
        )
        result = engine.dcf_valuation(params)
        assert result.terminal_value == pytest.approx(1000.0, rel=1e-4)
        assert result.terminal_pv == pytest.approx(1000.0 / 1.1, rel=1e-3)

    def test_net_debt_reduces_equity_value(self):
        """equity_value = enterprise_value − net_debt."""
        params = DCFParams(
            cash_flows=[100.0],
            discount_rate=0.10,
            terminal_growth_rate=0.02,
            net_debt=500.0,
        )
        result = engine.dcf_valuation(params)
        assert result.equity_value == pytest.approx(result.enterprise_value - 500.0, rel=1e-6)

    def test_gordon_raises_when_r_le_g(self):
        """r ≤ g is undefined for Gordon model — must raise ValueError."""
        params = DCFParams(
            cash_flows=[100.0],
            discount_rate=0.05,
            terminal_growth_rate=0.05,
        )
        with pytest.raises(ValueError, match="must exceed terminal growth rate"):
            engine.dcf_valuation(params)

    def test_tv_pct_consistent(self):
        """tv_as_pct_of_ev must equal terminal_pv / enterprise_value × 100 (1dp)."""
        params = DCFParams(
            cash_flows=[100.0, 100.0, 100.0],
            discount_rate=0.10,
            terminal_growth_rate=0.03,
        )
        result = engine.dcf_valuation(params)
        expected = round(result.terminal_pv / result.enterprise_value * 100, 1)
        assert result.tv_as_pct_of_ev == expected

    @pytest.mark.parametrize("cfs", [[0.0], [0.0, 0.0, 0.0]])
    def test_zero_cash_flows_give_zero_ev(self, cfs):
        params = DCFParams(cash_flows=cfs, discount_rate=0.10, terminal_growth_rate=0.02)
        result = engine.dcf_valuation(params)
        assert result.enterprise_value == pytest.approx(0.0, abs=1e-6)

    def test_negative_growth_rate_valid(self):
        """r > g still holds when g is negative; TV = CF*(1+g)/(r−g)."""
        params = DCFParams(
            cash_flows=[100.0],
            discount_rate=0.10,
            terminal_growth_rate=-0.02,
        )
        result = engine.dcf_valuation(params)
        # TV = 100 * 0.98 / 0.12 = 816.67
        assert result.terminal_value == pytest.approx(816.67, rel=1e-3)

    def test_higher_discount_rate_lowers_ev(self):
        """Sensitivity: increasing r should decrease EV monotonically."""
        base_params_kw = dict(
            cash_flows=[100.0, 150.0, 200.0],
            terminal_growth_rate=0.02,
        )
        evs = [
            engine.dcf_valuation(DCFParams(discount_rate=r, **base_params_kw)).enterprise_value
            for r in [0.08, 0.10, 0.12, 0.15]
        ]
        assert evs == sorted(evs, reverse=True)


# ── Comparables ───────────────────────────────────────────────────────────────


class TestComparableValuation:
    def test_ev_mw_single_multiple(self):
        """100 MW × 1 000 000 $/MW median = 100 000 000 EV."""
        params = ComparableParams(
            comparables=[
                ComparableCompany(name="A", ev_mw=1_000_000.0),
                ComparableCompany(name="B", ev_mw=1_000_000.0),
            ],
            subject_capacity_mw=100.0,
            multiple_types=["ev_mw"],
        )
        result = engine.comparable_valuation(params)
        assert result.enterprise_value == pytest.approx(100_000_000.0, rel=1e-4)

    def test_median_odd_count(self):
        """Median of [8, 10, 12] → 10; implied EV = 10 × 100 = 1000."""
        params = ComparableParams(
            comparables=[
                ComparableCompany(name="A", ev_ebitda=8.0),
                ComparableCompany(name="B", ev_ebitda=10.0),
                ComparableCompany(name="C", ev_ebitda=12.0),
            ],
            subject_ebitda=100.0,
            multiple_types=["ev_ebitda"],
        )
        result = engine.comparable_valuation(params)
        assert result.by_multiple["ev_ebitda"].median == pytest.approx(1000.0, rel=1e-4)

    def test_median_even_count(self):
        """Median of [8, 10, 12, 14] → 11; implied EV = 11 × 100 = 1100."""
        params = ComparableParams(
            comparables=[
                ComparableCompany(name="A", ev_ebitda=8.0),
                ComparableCompany(name="B", ev_ebitda=10.0),
                ComparableCompany(name="C", ev_ebitda=12.0),
                ComparableCompany(name="D", ev_ebitda=14.0),
            ],
            subject_ebitda=100.0,
            multiple_types=["ev_ebitda"],
        )
        result = engine.comparable_valuation(params)
        assert result.by_multiple["ev_ebitda"].median == pytest.approx(1100.0, rel=1e-4)

    def test_no_valid_multiples_raises(self):
        """Missing subject metric → no implied values → ValueError."""
        params = ComparableParams(
            comparables=[ComparableCompany(name="A", ev_mw=1_000_000.0)],
            subject_capacity_mw=None,  # can't compute ev_mw without capacity
            multiple_types=["ev_mw"],
        )
        with pytest.raises(ValueError, match="No implied values"):
            engine.comparable_valuation(params)

    def test_net_debt_subtracted(self):
        params = ComparableParams(
            comparables=[ComparableCompany(name="A", ev_ebitda=10.0)],
            subject_ebitda=100.0,
            net_debt=200.0,
            multiple_types=["ev_ebitda"],
        )
        result = engine.comparable_valuation(params)
        assert result.equity_value == pytest.approx(result.enterprise_value - 200.0, rel=1e-6)

    def test_range_min_max_bounds(self):
        """range_min ≤ weighted_average_value ≤ range_max."""
        params = ComparableParams(
            comparables=[
                ComparableCompany(name="A", ev_ebitda=5.0),
                ComparableCompany(name="B", ev_ebitda=10.0),
                ComparableCompany(name="C", ev_ebitda=15.0),
            ],
            subject_ebitda=100.0,
            multiple_types=["ev_ebitda"],
        )
        result = engine.comparable_valuation(params)
        assert result.range_min <= result.weighted_average_value <= result.range_max


# ── Replacement Cost ──────────────────────────────────────────────────────────


class TestReplacementCost:
    def test_gross_aggregation_no_depreciation(self):
        """Gross = sum(components) + land + development; EV = gross when dep=0."""
        params = ReplacementCostParams(
            component_costs={"turbines": 5_000_000.0, "civil_works": 2_000_000.0},
            land_value=500_000.0,
            development_costs=300_000.0,
            depreciation_pct=0.0,
        )
        result = engine.replacement_cost(params)
        assert result.gross_replacement_cost == pytest.approx(7_800_000.0, rel=1e-6)
        assert result.enterprise_value == pytest.approx(7_800_000.0, rel=1e-6)

    def test_depreciation_reduces_ev(self):
        """20% depreciation on 1 000 000 → EV = 800 000."""
        params = ReplacementCostParams(
            component_costs={"asset": 1_000_000.0},
            depreciation_pct=20.0,
        )
        result = engine.replacement_cost(params)
        assert result.enterprise_value == pytest.approx(800_000.0, rel=1e-6)

    def test_full_depreciation_ev_zero(self):
        params = ReplacementCostParams(
            component_costs={"asset": 500_000.0},
            depreciation_pct=100.0,
        )
        result = engine.replacement_cost(params)
        assert result.enterprise_value == pytest.approx(0.0, abs=1.0)

    def test_component_breakdown_preserved(self):
        params = ReplacementCostParams(
            component_costs={"a": 100.0, "b": 200.0},
        )
        result = engine.replacement_cost(params)
        assert result.component_breakdown["a"] == pytest.approx(100.0)
        assert result.component_breakdown["b"] == pytest.approx(200.0)

    def test_net_debt_subtracted(self):
        params = ReplacementCostParams(
            component_costs={"x": 1_000_000.0},
            net_debt=300_000.0,
        )
        result = engine.replacement_cost(params)
        assert result.equity_value == pytest.approx(result.enterprise_value - 300_000.0)


# ── Blended ───────────────────────────────────────────────────────────────────


class TestBlendedValuation:
    def test_equal_weights_is_average(self):
        params = BlendedParams(
            components=[
                BlendedComponent(method="dcf", enterprise_value=1_000_000.0, weight=1.0),
                BlendedComponent(method="comps", enterprise_value=2_000_000.0, weight=1.0),
            ],
        )
        result = engine.blended_valuation(params)
        assert result.enterprise_value == pytest.approx(1_500_000.0, rel=1e-6)

    def test_weights_normalised(self):
        """Doubling all weights should produce the same blend."""
        params_a = BlendedParams(
            components=[
                BlendedComponent(method="a", enterprise_value=100.0, weight=1.0),
                BlendedComponent(method="b", enterprise_value=300.0, weight=3.0),
            ],
        )
        params_b = BlendedParams(
            components=[
                BlendedComponent(method="a", enterprise_value=100.0, weight=10.0),
                BlendedComponent(method="b", enterprise_value=300.0, weight=30.0),
            ],
        )
        assert engine.blended_valuation(params_a).enterprise_value == pytest.approx(
            engine.blended_valuation(params_b).enterprise_value, rel=1e-9
        )

    def test_breakdown_weights_sum_to_one(self):
        params = BlendedParams(
            components=[
                BlendedComponent(method="a", enterprise_value=100.0, weight=2.0),
                BlendedComponent(method="b", enterprise_value=200.0, weight=3.0),
                BlendedComponent(method="c", enterprise_value=300.0, weight=5.0),
            ],
        )
        result = engine.blended_valuation(params)
        total_w = sum(item.weight for item in result.breakdown)
        assert total_w == pytest.approx(1.0, rel=1e-6)

    def test_range_min_max_match_inputs(self):
        params = BlendedParams(
            components=[
                BlendedComponent(method="a", enterprise_value=100.0, weight=1.0),
                BlendedComponent(method="b", enterprise_value=500.0, weight=1.0),
                BlendedComponent(method="c", enterprise_value=300.0, weight=1.0),
            ],
        )
        result = engine.blended_valuation(params)
        assert result.range_min == pytest.approx(100.0)
        assert result.range_max == pytest.approx(500.0)

    def test_net_debt_subtracted(self):
        params = BlendedParams(
            components=[
                BlendedComponent(method="a", enterprise_value=1_000_000.0, weight=1.0),
                BlendedComponent(method="b", enterprise_value=2_000_000.0, weight=1.0),
            ],
            net_debt=400_000.0,
        )
        result = engine.blended_valuation(params)
        assert result.equity_value == pytest.approx(result.enterprise_value - 400_000.0)


# ── Sensitivity ───────────────────────────────────────────────────────────────


class TestSensitivityAnalysis:
    def _base(self, **kw) -> DCFParams:
        defaults = dict(
            cash_flows=[100.0, 100.0, 100.0],
            discount_rate=0.10,
            terminal_growth_rate=0.02,
        )
        defaults.update(kw)
        return DCFParams(**defaults)

    def test_matrix_dimensions(self):
        req = SensitivityRequest(
            base_params=self._base(),
            row_variable="discount_rate",
            col_variable="terminal_growth_rate",
            row_values=[0.08, 0.10, 0.12],
            col_values=[0.01, 0.02, 0.03, 0.04],
        )
        result = engine.sensitivity_analysis(req)
        assert len(result.matrix) == 3
        assert all(len(row) == 4 for row in result.matrix)

    def test_invalid_gordon_cells_are_none(self):
        """r ≤ g cells must be None in the matrix."""
        req = SensitivityRequest(
            base_params=self._base(discount_rate=0.10),
            row_variable="discount_rate",
            col_variable="terminal_growth_rate",
            row_values=[0.05],
            col_values=[0.05, 0.06],  # both ≥ r
        )
        result = engine.sensitivity_analysis(req)
        assert result.matrix[0][0] is None
        assert result.matrix[0][1] is None

    def test_higher_discount_rate_lowers_ev(self):
        req = SensitivityRequest(
            base_params=self._base(),
            row_variable="discount_rate",
            col_variable="terminal_growth_rate",
            row_values=[0.08, 0.10, 0.12, 0.15],
            col_values=[0.02],
        )
        result = engine.sensitivity_analysis(req)
        evs = [row[0] for row in result.matrix if row[0] is not None]
        assert evs == sorted(evs, reverse=True)

    def test_base_value_matches_direct_dcf(self):
        base = self._base()
        direct = engine.dcf_valuation(base)
        req = SensitivityRequest(
            base_params=base,
            row_variable="discount_rate",
            col_variable="terminal_growth_rate",
            row_values=[0.08, 0.12],
            col_values=[0.01, 0.03],
        )
        result = engine.sensitivity_analysis(req)
        assert result.base_value == pytest.approx(direct.enterprise_value, rel=1e-4)

    def test_min_max_consistent_with_matrix(self):
        req = SensitivityRequest(
            base_params=self._base(),
            row_variable="discount_rate",
            col_variable="terminal_growth_rate",
            row_values=[0.08, 0.10, 0.12],
            col_values=[0.01, 0.02, 0.03],
        )
        result = engine.sensitivity_analysis(req)
        all_vals = [v for row in result.matrix for v in row if v is not None]
        assert result.min_value == pytest.approx(min(all_vals), rel=1e-6)
        assert result.max_value == pytest.approx(max(all_vals), rel=1e-6)
