"""Deterministic carbon credit estimator — no LLM involvement."""

from typing import Any

# Grid emission factors by region (tCO2e/MWh) — simplified global averages
GRID_EMISSION_FACTORS: dict[str, float] = {
    "default": 0.42,
    "Europe": 0.25,
    "US": 0.38,
    "Asia": 0.55,
    "Africa": 0.45,
    "South America": 0.30,
    "Australia": 0.72,
    "Middle East": 0.58,
}

# Capacity factors by project type
CAPACITY_FACTORS: dict[str, float] = {
    "solar_pv": 0.18,
    "onshore_wind": 0.28,
    "offshore_wind": 0.38,
    "hydro": 0.42,
    "geothermal": 0.85,
    "biomass": 0.70,
    "default": 0.25,
}

# Methodology recommendations by project type
METHODOLOGY_MAP: dict[str, tuple[str, str]] = {
    "solar_pv": ("ACM0002", "CDM/Verra ACM0002 — Grid-connected renewable electricity generation"),
    "onshore_wind": ("ACM0002", "CDM/Verra ACM0002 — Grid-connected renewable electricity generation"),
    "offshore_wind": ("ACM0002", "CDM/Verra ACM0002 — Grid-connected renewable electricity generation"),
    "hydro": ("ACM0002", "CDM/Verra ACM0002 — Grid-connected renewable electricity generation"),
    "geothermal": ("ACM0002", "CDM/Verra ACM0002 — Grid-connected renewable electricity generation"),
    "biomass": ("AMS-I.D", "CDM AMS-I.D — Grid-connected renewable electricity generation"),
    "green_building": ("AMS-II.C", "CDM AMS-II.C — Demand-side energy efficiency activities"),
    "energy_efficiency": ("AMS-II.A", "CDM AMS-II.A — Supply-side energy efficiency improvements"),
    "default": ("VM0041", "Verra VM0041 — Avoiding the Planned Burning of Non-Renewable Biomass"),
}

AVAILABLE_METHODOLOGIES = [
    {
        "id": "ACM0002",
        "name": "ACM0002 — Grid-connected Renewable Electricity",
        "registry": "CDM / Verra",
        "applicable_project_types": ["solar_pv", "onshore_wind", "offshore_wind", "hydro", "geothermal"],
        "description": "Applicable to projects displacing grid electricity with renewable sources.",
        "verification_complexity": "medium",
    },
    {
        "id": "GS_RE",
        "name": "Gold Standard — Renewable Energy",
        "registry": "Gold Standard",
        "applicable_project_types": ["solar_pv", "onshore_wind", "offshore_wind", "hydro"],
        "description": "Gold Standard methodology for renewable energy projects with strong co-benefits.",
        "verification_complexity": "high",
    },
    {
        "id": "AMS-II.A",
        "name": "AMS-II.A — Supply-side Energy Efficiency",
        "registry": "CDM",
        "applicable_project_types": ["energy_efficiency"],
        "description": "For projects improving efficiency in electricity generation and distribution.",
        "verification_complexity": "medium",
    },
    {
        "id": "AMS-II.C",
        "name": "AMS-II.C — Demand-side Energy Efficiency",
        "registry": "CDM",
        "applicable_project_types": ["green_building", "energy_efficiency"],
        "description": "For projects reducing electricity consumption in buildings and industry.",
        "verification_complexity": "low",
    },
    {
        "id": "VM0041",
        "name": "VM0041 — Sustainable Agriculture",
        "registry": "Verra",
        "applicable_project_types": ["agriculture", "land_use"],
        "description": "For sustainable land management and agriculture projects.",
        "verification_complexity": "high",
    },
]


def estimate_credits(
    project_type: str,
    capacity_mw: float | None,
    geography_country: str,
    *,
    savings_pct: float = 0.0,
    baseline_consumption_mwh: float = 0.0,
) -> dict:
    """
    Deterministic carbon credit estimation.

    Returns estimated annual tCO2e, methodology, and assumptions.
    """
    # Determine emission factor from geography
    region = "default"
    for r in ["Europe", "US", "Asia", "Africa", "South America", "Australia", "Middle East"]:
        if r.lower() in geography_country.lower():
            region = r
            break

    emission_factor = GRID_EMISSION_FACTORS.get(region, 0.42)
    methodology_id, methodology_label = METHODOLOGY_MAP.get(
        project_type, METHODOLOGY_MAP["default"]
    )

    # Estimate based on project type
    annual_mwh = 0.0
    assumptions: dict[str, Any] = {}
    confidence = "medium"

    if project_type in {"solar_pv", "onshore_wind", "offshore_wind", "hydro", "geothermal", "biomass"}:
        if capacity_mw and capacity_mw > 0:
            cf = CAPACITY_FACTORS.get(project_type, CAPACITY_FACTORS["default"])
            annual_mwh = capacity_mw * cf * 8760  # hours/year
            annual_tons_co2e = annual_mwh * emission_factor
            confidence = "high"
            assumptions = {
                "capacity_mw": capacity_mw,
                "capacity_factor_pct": round(cf * 100, 1),
                "grid_emission_factor_tco2e_mwh": emission_factor,
                "annual_generation_mwh": round(annual_mwh, 0),
                "region": region,
            }
        else:
            # Rough estimate for no capacity data
            annual_tons_co2e = 5000.0
            confidence = "low"
            assumptions = {"note": "Capacity not specified — using placeholder estimate"}

    elif project_type in {"green_building", "energy_efficiency"}:
        if baseline_consumption_mwh > 0 and savings_pct > 0:
            saved_mwh = baseline_consumption_mwh * (savings_pct / 100)
            annual_tons_co2e = saved_mwh * emission_factor
            confidence = "medium"
            assumptions = {
                "baseline_consumption_mwh": baseline_consumption_mwh,
                "savings_pct": savings_pct,
                "saved_mwh": round(saved_mwh, 0),
                "grid_emission_factor": emission_factor,
            }
        else:
            annual_tons_co2e = 2500.0
            confidence = "low"
            assumptions = {"note": "Insufficient data — using placeholder estimate"}
    else:
        annual_tons_co2e = 3000.0
        confidence = "low"
        assumptions = {"note": "Project type not directly supported — estimate based on similar projects"}

    return {
        "annual_tons_co2e": round(annual_tons_co2e, 1),
        "methodology": methodology_id,
        "methodology_label": methodology_label,
        "assumptions": assumptions,
        "confidence": confidence,
        "notes": (
            f"Estimated using {methodology_id} methodology. "
            f"Grid emission factor: {emission_factor} tCO2e/MWh ({region}). "
            "This is a preliminary estimate only — formal verification required."
        ),
    }


def revenue_projection(
    annual_tons: float,
    price_scenarios: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Project revenue at different carbon price scenarios."""
    if price_scenarios is None:
        price_scenarios = {
            "conservative": 8.0,   # voluntary market low
            "base_case": 15.0,     # voluntary market mid
            "optimistic": 25.0,    # high-quality/Gold Standard
            "eu_ets": 65.0,        # EU ETS reference
        }

    return {
        "annual_tons": annual_tons,
        "scenarios": {
            name: {
                "price_per_ton_usd": price,
                "annual_revenue_usd": round(annual_tons * price, 0),
                "10yr_revenue_usd": round(annual_tons * price * 10, 0),
            }
            for name, price in price_scenarios.items()
        },
    }
