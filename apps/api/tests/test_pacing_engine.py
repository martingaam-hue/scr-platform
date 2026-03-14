"""Unit tests for pacing J-curve math — no DB required.

We import the module-level constants and replicate the
_generate_projections arithmetic without touching any ORM or async session.
"""

from decimal import Decimal

import pytest

from app.modules.pacing.service import (
    _DEFAULT_DEPLOYMENT_PCT,
    _DEFAULT_DISTRIBUTION_PCT,
)

# ── Helper: pure J-curve calculator ──────────────────────────────────────────


def _compute_projections(
    capital: Decimal,
    fund_years: int,
    invest_years: int,
    modifier: Decimal = Decimal("1.0"),
) -> list[dict]:
    """Replicate _generate_projections math without the DB session."""
    rows: list[dict] = []
    cumulative_nav = Decimal("0")
    for year in range(1, fund_years + 1):
        if year <= invest_years:
            deploy_pct = _DEFAULT_DEPLOYMENT_PCT.get(year, Decimal("0"))
        else:
            deploy_pct = Decimal("0")
        contributions = (capital * deploy_pct).quantize(Decimal("0.0001"))

        dist_pct = _DEFAULT_DISTRIBUTION_PCT.get(year, Decimal("0"))
        distributions = (capital * dist_pct * modifier).quantize(Decimal("0.0001"))

        net_cashflow = (distributions - contributions).quantize(Decimal("0.0001"))
        cumulative_nav = (cumulative_nav + contributions - distributions).quantize(
            Decimal("0.0001")
        )
        nav = max(cumulative_nav, Decimal("0"))

        rows.append(
            {
                "year": year,
                "contributions": contributions,
                "distributions": distributions,
                "net_cashflow": net_cashflow,
                "nav": nav,
            }
        )
    return rows


# ── Schedule constant invariants ─────────────────────────────────────────────


class TestScheduleConstants:
    def test_deployment_sums_to_100_pct(self):
        total = sum(_DEFAULT_DEPLOYMENT_PCT.values())
        assert total == Decimal("1.00")

    def test_distribution_sums_to_100_pct(self):
        total = sum(_DEFAULT_DISTRIBUTION_PCT.values())
        assert total == Decimal("1.00")

    def test_deployment_keys_are_years_1_to_5(self):
        assert set(_DEFAULT_DEPLOYMENT_PCT.keys()) == {1, 2, 3, 4, 5}

    def test_distribution_starts_year_3(self):
        """J-curve: no distributions in years 1–2."""
        assert 1 not in _DEFAULT_DISTRIBUTION_PCT
        assert 2 not in _DEFAULT_DISTRIBUTION_PCT

    def test_all_deployment_pcts_positive(self):
        assert all(v > Decimal("0") for v in _DEFAULT_DEPLOYMENT_PCT.values())

    def test_all_distribution_pcts_positive(self):
        assert all(v > Decimal("0") for v in _DEFAULT_DISTRIBUTION_PCT.values())


# ── J-curve math ─────────────────────────────────────────────────────────────


CAPITAL = Decimal("10000000")
FUND_YEARS = 10
INVEST_YEARS = 5


class TestJCurveMath:
    def test_early_years_have_negative_net_cashflow(self):
        """Years 1–2 have no distributions → net cashflow is negative."""
        rows = _compute_projections(CAPITAL, FUND_YEARS, INVEST_YEARS)
        for row in rows[:2]:
            assert row["net_cashflow"] < 0, f"Year {row['year']} should be negative"

    def test_later_year_positive_net_cashflow(self):
        """Year 8 has distributions but no contributions → positive net cashflow."""
        rows = _compute_projections(CAPITAL, FUND_YEARS, INVEST_YEARS)
        year8 = next(r for r in rows if r["year"] == 8)
        assert year8["net_cashflow"] > 0

    def test_total_contributions_equal_committed_capital(self):
        """Sum of all contributions must equal committed capital (full deployment)."""
        rows = _compute_projections(CAPITAL, FUND_YEARS, INVEST_YEARS)
        total = sum(r["contributions"] for r in rows)
        assert total == CAPITAL.quantize(Decimal("0.0001"))

    def test_nav_never_negative(self):
        rows = _compute_projections(CAPITAL, FUND_YEARS, INVEST_YEARS)
        for row in rows:
            assert row["nav"] >= 0, f"Year {row['year']} NAV is negative: {row['nav']}"

    def test_trough_in_early_years(self):
        """Most-negative net cashflow must occur in years 1–3."""
        rows = _compute_projections(CAPITAL, FUND_YEARS, INVEST_YEARS)
        trough = min(rows, key=lambda r: r["net_cashflow"])
        assert trough["year"] <= 3, f"Trough should be in years 1–3, got year {trough['year']}"

    def test_optimistic_higher_distributions(self):
        """modifier=1.2 gives higher distributions than modifier=1.0 at every dist year."""
        base = _compute_projections(CAPITAL, FUND_YEARS, INVEST_YEARS, modifier=Decimal("1.0"))
        opt = _compute_projections(CAPITAL, FUND_YEARS, INVEST_YEARS, modifier=Decimal("1.2"))
        for b, o in zip(base, opt, strict=False):
            if b["distributions"] > 0:
                assert o["distributions"] > b["distributions"], (
                    f"Year {b['year']}: optimistic dist {o['distributions']} "
                    f"not > base {b['distributions']}"
                )

    def test_pessimistic_lower_distributions(self):
        """modifier=0.8 gives lower distributions than base at every dist year."""
        base = _compute_projections(CAPITAL, FUND_YEARS, INVEST_YEARS, modifier=Decimal("1.0"))
        pess = _compute_projections(CAPITAL, FUND_YEARS, INVEST_YEARS, modifier=Decimal("0.8"))
        for b, p in zip(base, pess, strict=False):
            if b["distributions"] > 0:
                assert p["distributions"] < b["distributions"]

    def test_scenario_ordering_at_distribution_years(self):
        """downside < base < upside at every year with non-zero distributions."""
        base = _compute_projections(CAPITAL, FUND_YEARS, INVEST_YEARS, Decimal("1.0"))
        opt = _compute_projections(CAPITAL, FUND_YEARS, INVEST_YEARS, Decimal("1.2"))
        pess = _compute_projections(CAPITAL, FUND_YEARS, INVEST_YEARS, Decimal("0.8"))
        for b, o, p in zip(base, opt, pess, strict=False):
            if b["distributions"] > 0:
                assert p["distributions"] < b["distributions"] < o["distributions"]

    def test_zero_capital_all_zeros(self):
        rows = _compute_projections(Decimal("0"), FUND_YEARS, INVEST_YEARS)
        assert all(r["contributions"] == 0 for r in rows)
        assert all(r["distributions"] == 0 for r in rows)
        assert all(r["nav"] == 0 for r in rows)

    def test_no_contribution_after_invest_period(self):
        """Years beyond invest_years must have zero contributions."""
        rows = _compute_projections(CAPITAL, FUND_YEARS, invest_years=3)
        for row in rows:
            if row["year"] > 3:
                assert row["contributions"] == 0

    def test_deployment_never_exceeds_capital_per_year(self):
        rows = _compute_projections(CAPITAL, FUND_YEARS, INVEST_YEARS)
        for row in rows:
            assert row["contributions"] <= CAPITAL
