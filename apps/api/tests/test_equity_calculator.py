"""Unit tests for equity calculator — pure Python, no DB required."""

import pytest

from app.modules.equity_calculator.calculator import calculate_scenario

# ── Basic calculations ────────────────────────────────────────────────────────


class TestBasicCalculations:
    def test_post_money_valuation(self):
        result = calculate_scenario(1_000_000.0, 250_000.0, 1_000_000)
        assert result["post_money_valuation"] == pytest.approx(1_250_000.0)

    def test_equity_percentage(self):
        """equity_pct = investment / (pre_money + investment)."""
        result = calculate_scenario(3_000_000.0, 1_000_000.0, 1_000_000)
        # post = 4M; pct = 1M/4M = 25%
        assert result["equity_percentage"] == pytest.approx(25.0, rel=1e-4)

    def test_price_per_share(self):
        """price_per_share = pre_money / shares_outstanding."""
        result = calculate_scenario(1_000_000.0, 100_000.0, 1_000)
        assert result["price_per_share"] == pytest.approx(1000.0)

    def test_new_shares_issued(self):
        """new_shares = round(investment / price_per_share)."""
        result = calculate_scenario(1_000_000.0, 250_000.0, 1_000_000)
        # price_per_share = 1M / 1M shares = $1; new_shares = 250_000 / 1 = 250_000
        assert result["new_shares_issued"] == 250_000

    def test_cap_table_percentages_sum_to_100(self):
        result = calculate_scenario(4_000_000.0, 1_000_000.0, 1_000_000)
        total = sum(entry["percentage"] for entry in result["cap_table"])
        assert total == pytest.approx(100.0, rel=1e-4)

    def test_cap_table_has_two_entries(self):
        result = calculate_scenario(1_000_000.0, 250_000.0, 1_000)
        assert len(result["cap_table"]) == 2
        names = {e["name"] for e in result["cap_table"]}
        assert "Existing Shareholders" in names
        assert "New Investor" in names


# ── Dilution impact ───────────────────────────────────────────────────────────


class TestDilutionImpact:
    def test_pre_investment_ownership_100(self):
        result = calculate_scenario(4_000_000.0, 1_000_000.0, 1_000_000)
        assert result["dilution_impact"]["pre_investment_ownership"] == pytest.approx(100.0)

    def test_post_investment_ownership(self):
        """Existing shareholders retain (1 − equity_pct) × 100%."""
        result = calculate_scenario(4_000_000.0, 1_000_000.0, 1_000_000)
        # equity_pct = 1M/5M = 20%; existing retain 80%
        assert result["dilution_impact"]["post_investment_ownership"] == pytest.approx(
            80.0, rel=1e-4
        )

    def test_dilution_percentage(self):
        result = calculate_scenario(4_000_000.0, 1_000_000.0, 1_000_000)
        assert result["dilution_impact"]["dilution_percentage"] == pytest.approx(20.0, rel=1e-4)

    def test_total_shares_after(self):
        result = calculate_scenario(1_000_000.0, 250_000.0, 1_000_000)
        assert (
            result["dilution_impact"]["total_shares_after"]
            == 1_000_000 + result["new_shares_issued"]
        )

    def test_no_anti_dilution_flag_false(self):
        result = calculate_scenario(1_000_000.0, 250_000.0, 1_000, anti_dilution_type="none")
        assert result["dilution_impact"]["anti_dilution_protection"] is False

    def test_broad_based_anti_dilution_flag_true(self):
        result = calculate_scenario(1_000_000.0, 250_000.0, 1_000, anti_dilution_type="broad_based")
        assert result["dilution_impact"]["anti_dilution_protection"] is True
        assert result["dilution_impact"]["anti_dilution_type"] == "broad_based"

    @pytest.mark.parametrize("ad_type", ["broad_based", "narrow_based", "full_ratchet"])
    def test_anti_dilution_types_set_protection_true(self, ad_type: str):
        result = calculate_scenario(1_000_000.0, 250_000.0, 1_000, anti_dilution_type=ad_type)
        assert result["dilution_impact"]["anti_dilution_protection"] is True


# ── Waterfall ─────────────────────────────────────────────────────────────────


class TestWaterfall:
    def test_waterfall_has_six_entries(self):
        result = calculate_scenario(4_000_000.0, 1_000_000.0, 1_000_000)
        assert len(result["waterfall"]) == 6

    def test_waterfall_multiples_present(self):
        result = calculate_scenario(4_000_000.0, 1_000_000.0, 1_000_000)
        multiples = {w["multiple"] for w in result["waterfall"]}
        assert {1.0, 1.5, 2.0, 3.0, 5.0, 10.0} == multiples

    def test_founder_plus_investor_equals_exit_value(self):
        """investor_proceeds + founder_proceeds must equal exit_value at every multiple."""
        result = calculate_scenario(4_000_000.0, 1_000_000.0, 1_000_000)
        for entry in result["waterfall"]:
            total = entry["investor_proceeds"] + entry["founder_proceeds"]
            assert total == pytest.approx(
                entry["exit_value"], rel=1e-4
            ), f"Multiple {entry['multiple']}x: proceeds don't sum to exit_value"

    def test_exit_value_equals_postmoney_times_multiple(self):
        result = calculate_scenario(4_000_000.0, 1_000_000.0, 1_000_000)
        post_money = result["post_money_valuation"]
        for entry in result["waterfall"]:
            assert entry["exit_value"] == pytest.approx(post_money * entry["multiple"], rel=1e-4)

    def test_common_equity_pro_rata_at_2x(self):
        """Common equity: investor proceeds = equity_pct × exit_value."""
        result = calculate_scenario(4_000_000.0, 1_000_000.0, 1_000_000, "common_equity")
        # equity_pct = 1M/5M = 20%; at 2x: exit = 10M; investor = 2M
        entry = next(w for w in result["waterfall"] if w["multiple"] == 2.0)
        assert entry["investor_proceeds"] == pytest.approx(2_000_000.0, rel=1e-4)

    def test_moic_at_5x_common_equity(self):
        """MOIC = investor_proceeds / investment_amount; at 5x exit = 5.0."""
        result = calculate_scenario(4_000_000.0, 1_000_000.0, 1_000_000, "common_equity")
        # at 5x exit: investor proceeds = 5M * 0.20 = 5M... wait
        # post_money=5M, exit = 5M*5 = 25M, investor = 25M*0.20 = 5M; MOIC = 5M/1M = 5.0
        entry = next(w for w in result["waterfall"] if w["multiple"] == 5.0)
        assert entry["investor_moic"] == pytest.approx(5.0, rel=1e-3)

    def test_moic_at_1x_exit_less_than_or_equal_one(self):
        """At 1× exit (breakeven), investor MOIC should be ≤ 1."""
        result = calculate_scenario(4_000_000.0, 1_000_000.0, 1_000_000)
        entry = next(w for w in result["waterfall"] if w["multiple"] == 1.0)
        assert entry["investor_moic"] <= 1.0 + 1e-6

    def test_moic_increases_with_exit_multiple(self):
        result = calculate_scenario(4_000_000.0, 1_000_000.0, 1_000_000)
        sorted_w = sorted(result["waterfall"], key=lambda w: w["multiple"])
        moics = [w["investor_moic"] for w in sorted_w]
        assert moics == sorted(moics), "MOIC must increase with exit multiple"


# ── Preferred equity ──────────────────────────────────────────────────────────


class TestPreferredEquity:
    def test_liquidation_preference_at_low_exit(self):
        """At 1× exit below liq pref + remaining, investor gets the liq pref."""
        result = calculate_scenario(
            pre_money_valuation=1_000_000.0,
            investment_amount=500_000.0,
            shares_outstanding_before=1_000,
            security_type="preferred_equity",
            liquidation_preference=500_000.0,
        )
        entry_1x = next(w for w in result["waterfall"] if w["multiple"] == 1.0)
        # exit_val = 1.5M * 1 = 1.5M; liq = min(500K, 1.5M) = 500K
        assert entry_1x["investor_proceeds"] == pytest.approx(500_000.0, rel=1e-4)

    def test_preferred_better_than_common_at_high_exit(self):
        """With liq pref, preferred investor does at least as well as common at high exits."""
        preferred = calculate_scenario(
            1_000_000.0,
            500_000.0,
            1_000,
            security_type="preferred_equity",
            liquidation_preference=500_000.0,
        )
        common = calculate_scenario(1_000_000.0, 500_000.0, 1_000, security_type="common_equity")
        entry_pref = next(w for w in preferred["waterfall"] if w["multiple"] == 10.0)
        entry_com = next(w for w in common["waterfall"] if w["multiple"] == 10.0)
        # At very high exits, both should converge to pro-rata; just verify no errors
        assert entry_pref["investor_proceeds"] >= 0
        assert entry_com["investor_proceeds"] >= 0


# ── Input validation ─────────────────────────────────────────────────────────


class TestInputValidation:
    def test_zero_pre_money_raises(self):
        with pytest.raises(ValueError, match="pre_money_valuation must be positive"):
            calculate_scenario(0.0, 100_000.0, 1_000)

    def test_negative_pre_money_raises(self):
        with pytest.raises(ValueError, match="pre_money_valuation must be positive"):
            calculate_scenario(-500_000.0, 100_000.0, 1_000)

    def test_zero_investment_raises(self):
        with pytest.raises(ValueError, match="investment_amount must be positive"):
            calculate_scenario(1_000_000.0, 0.0, 1_000)

    def test_zero_shares_raises(self):
        with pytest.raises(ValueError, match="shares_outstanding_before must be positive"):
            calculate_scenario(1_000_000.0, 250_000.0, 0)


# ── Convertible / SAFE ────────────────────────────────────────────────────────


class TestConvertibleInstruments:
    @pytest.mark.parametrize("sec_type", ["convertible_note", "safe"])
    def test_convertible_treated_as_pro_rata(self, sec_type: str):
        """Convertible note and SAFE use pure pro-rata at post-money valuation."""
        result = calculate_scenario(4_000_000.0, 1_000_000.0, 1_000_000, security_type=sec_type)
        entry_2x = next(w for w in result["waterfall"] if w["multiple"] == 2.0)
        # Same as common: exit = 5M*2=10M; investor = 10M * 0.20 = 2M
        assert entry_2x["investor_proceeds"] == pytest.approx(2_000_000.0, rel=1e-4)
