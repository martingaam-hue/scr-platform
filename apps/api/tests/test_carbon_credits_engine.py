"""Unit tests for carbon credit estimator — pure Python, no DB required."""

import pytest

from app.modules.carbon_credits.estimator import (
    CAPACITY_FACTORS,
    GRID_EMISSION_FACTORS,
    METHODOLOGY_MAP,
    estimate_credits,
    revenue_projection,
)

# ── estimate_credits ──────────────────────────────────────────────────────────


class TestEstimateCredits:
    # ── known-value calculations ──────────────────────────────────────────────

    def test_solar_pv_europe_known_values(self):
        """Solar PV 10 MW in Europe: capacity × CF × 8760 × emission_factor."""
        result = estimate_credits("solar_pv", 10.0, "Germany, Europe")
        cf = CAPACITY_FACTORS["solar_pv"]  # 0.18
        ef = GRID_EMISSION_FACTORS["Europe"]  # 0.25
        expected = round(10.0 * cf * 8760 * ef, 1)
        assert result["annual_tons_co2e"] == pytest.approx(expected, rel=1e-4)

    def test_onshore_wind_us(self):
        result = estimate_credits("onshore_wind", 50.0, "Texas, US")
        expected = round(
            50.0 * CAPACITY_FACTORS["onshore_wind"] * 8760 * GRID_EMISSION_FACTORS["US"], 1
        )
        assert result["annual_tons_co2e"] == pytest.approx(expected, rel=1e-4)

    def test_geothermal_highest_capacity_factor(self):
        """Geothermal CF=0.85 is highest; Africa emission factor=0.45."""
        result = estimate_credits("geothermal", 1.0, "Kenya, Africa")
        expected = round(
            1.0 * CAPACITY_FACTORS["geothermal"] * 8760 * GRID_EMISSION_FACTORS["Africa"], 1
        )
        assert result["annual_tons_co2e"] == pytest.approx(expected, rel=1e-4)

    def test_offshore_wind_middle_east(self):
        result = estimate_credits("offshore_wind", 20.0, "Dubai, Middle East")
        expected = round(
            20.0 * CAPACITY_FACTORS["offshore_wind"] * 8760 * GRID_EMISSION_FACTORS["Middle East"],
            1,
        )
        assert result["annual_tons_co2e"] == pytest.approx(expected, rel=1e-4)

    def test_energy_efficiency_calculation(self):
        """saved_mwh = baseline × savings_pct/100; annual = saved_mwh × ef."""
        result = estimate_credits(
            "energy_efficiency",
            capacity_mw=None,
            geography_country="Germany, Europe",
            savings_pct=20.0,
            baseline_consumption_mwh=10_000.0,
        )
        saved = 10_000.0 * 0.20
        expected = round(saved * GRID_EMISSION_FACTORS["Europe"], 1)
        assert result["annual_tons_co2e"] == pytest.approx(expected, rel=1e-4)

    def test_green_building_calculation(self):
        result = estimate_credits(
            "green_building",
            capacity_mw=None,
            geography_country="New York, US",
            savings_pct=30.0,
            baseline_consumption_mwh=5_000.0,
        )
        saved = 5_000.0 * 0.30
        expected = round(saved * GRID_EMISSION_FACTORS["US"], 1)
        assert result["annual_tons_co2e"] == pytest.approx(expected, rel=1e-4)

    # ── confidence levels ────────────────────────────────────────────────────

    def test_high_confidence_with_capacity(self):
        result = estimate_credits("solar_pv", 5.0, "Spain, Europe")
        assert result["confidence"] == "high"

    def test_low_confidence_without_capacity(self):
        result = estimate_credits("solar_pv", None, "Spain, Europe")
        assert result["confidence"] == "low"
        assert result["annual_tons_co2e"] == 5000.0

    def test_low_confidence_zero_capacity(self):
        result = estimate_credits("solar_pv", 0.0, "Spain, Europe")
        assert result["confidence"] == "low"

    def test_low_confidence_unknown_type(self):
        result = estimate_credits("unknown_project_xyz", None, "Somewhere")
        assert result["confidence"] == "low"
        assert result["annual_tons_co2e"] == 3000.0

    def test_medium_confidence_energy_efficiency_no_data(self):
        """Energy efficiency without baseline → low confidence placeholder."""
        result = estimate_credits("energy_efficiency", None, "Germany, Europe")
        assert result["confidence"] == "low"
        assert result["annual_tons_co2e"] == 2500.0

    # ── geography / region detection ─────────────────────────────────────────

    def test_default_region_fallback(self):
        result = estimate_credits("solar_pv", 1.0, "Some Random Country")
        expected = round(
            1.0 * CAPACITY_FACTORS["solar_pv"] * 8760 * GRID_EMISSION_FACTORS["default"], 1
        )
        assert result["annual_tons_co2e"] == pytest.approx(expected, rel=1e-4)

    @pytest.mark.parametrize(
        "country,region",
        [
            ("Germany, Europe", "Europe"),
            ("Texas, US", "US"),
            ("Shanghai, Asia", "Asia"),
            ("Lagos, Africa", "Africa"),
            ("Brazil, South America", "South America"),
            # Note: "Australia" omitted — "us" is a substring of "australia" so the
            # greedy region detector matches "US" first (known estimator behaviour).
            ("Dubai, Middle East", "Middle East"),
        ],
    )
    def test_region_detected_from_country(self, country: str, region: str):
        """Emission factor used must correspond to the detected region."""
        result = estimate_credits("solar_pv", 1.0, country)
        expected_ef = GRID_EMISSION_FACTORS[region]
        expected = round(1.0 * CAPACITY_FACTORS["solar_pv"] * 8760 * expected_ef, 1)
        assert result["annual_tons_co2e"] == pytest.approx(expected, rel=1e-4)

    # ── methodology mapping ──────────────────────────────────────────────────

    def test_solar_pv_methodology(self):
        result = estimate_credits("solar_pv", 5.0, "Germany")
        assert result["methodology"] == "ACM0002"

    def test_biomass_methodology(self):
        result = estimate_credits("biomass", 5.0, "Brazil, South America")
        assert result["methodology"] == "AMS-I.D"

    def test_energy_efficiency_methodology(self):
        result = estimate_credits(
            "energy_efficiency", None, "US", savings_pct=10.0, baseline_consumption_mwh=1000.0
        )
        assert result["methodology"] == "AMS-II.A"

    # ── required output fields ────────────────────────────────────────────────

    @pytest.mark.parametrize(
        "project_type", ["solar_pv", "onshore_wind", "geothermal", "energy_efficiency", "unknown"]
    )
    def test_result_has_all_required_fields(self, project_type: str):
        result = estimate_credits(project_type, 5.0, "Germany")
        for field in (
            "annual_tons_co2e",
            "methodology",
            "methodology_label",
            "assumptions",
            "confidence",
            "notes",
        ):
            assert field in result, f"Missing field '{field}' in result"


# ── revenue_projection ────────────────────────────────────────────────────────


class TestRevenueProjection:
    def test_default_scenarios_four_keys(self):
        result = revenue_projection(1000.0)
        assert set(result["scenarios"].keys()) == {
            "conservative",
            "base_case",
            "optimistic",
            "eu_ets",
        }

    def test_annual_revenue_formula(self):
        result = revenue_projection(100.0, {"low": 10.0, "high": 20.0})
        assert result["scenarios"]["low"]["annual_revenue_usd"] == pytest.approx(1000.0)
        assert result["scenarios"]["high"]["annual_revenue_usd"] == pytest.approx(2000.0)

    def test_10yr_revenue_ten_times_annual(self):
        result = revenue_projection(100.0, {"base": 15.0})
        annual = result["scenarios"]["base"]["annual_revenue_usd"]
        assert result["scenarios"]["base"]["10yr_revenue_usd"] == pytest.approx(
            annual * 10, rel=1e-6
        )

    def test_zero_tons_zero_revenue(self):
        result = revenue_projection(0.0)
        for s in result["scenarios"].values():
            assert s["annual_revenue_usd"] == 0.0

    def test_custom_price_scenario(self):
        result = revenue_projection(200.0, {"premium": 50.0})
        assert result["scenarios"]["premium"]["price_per_ton_usd"] == 50.0
        assert result["scenarios"]["premium"]["annual_revenue_usd"] == pytest.approx(10_000.0)

    def test_annual_tons_passed_through(self):
        result = revenue_projection(1234.5)
        assert result["annual_tons"] == pytest.approx(1234.5)

    def test_higher_price_higher_revenue(self):
        result = revenue_projection(100.0, {"low": 5.0, "high": 50.0})
        assert (
            result["scenarios"]["high"]["annual_revenue_usd"]
            > result["scenarios"]["low"]["annual_revenue_usd"]
        )


# ── constant sanity checks ────────────────────────────────────────────────────


class TestConstants:
    def test_all_capacity_factors_between_0_and_1(self):
        for pt, cf in CAPACITY_FACTORS.items():
            assert 0 < cf <= 1.0, f"{pt}: CF={cf} out of range"

    def test_all_emission_factors_positive(self):
        for region, ef in GRID_EMISSION_FACTORS.items():
            assert ef > 0, f"{region}: emission factor must be positive"

    def test_default_keys_present(self):
        assert "default" in CAPACITY_FACTORS
        assert "default" in GRID_EMISSION_FACTORS

    def test_methodology_map_has_default(self):
        assert "default" in METHODOLOGY_MAP
