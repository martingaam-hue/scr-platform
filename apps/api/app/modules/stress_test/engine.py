"""Monte Carlo stress test engine — pure numerical, no LLM."""

from __future__ import annotations

import uuid
from typing import Any

import numpy as np

PREDEFINED_SCENARIOS: dict[str, dict[str, Any]] = {
    "rate_shock_200": {
        "name": "Interest Rate +200bps",
        "params": {"rate_delta_bps": 200},
        "description": "Simulate a 200bp central bank rate hike and its impact on leveraged project valuations.",
    },
    "rate_shock_100": {
        "name": "Interest Rate +100bps",
        "params": {"rate_delta_bps": 100},
        "description": "Moderate 100bp rate increase scenario.",
    },
    "energy_crash_30": {
        "name": "Energy Prices -30%",
        "params": {"energy_delta_pct": -30},
        "description": "Energy price crash of 30% — impacts revenue for operational energy assets.",
    },
    "energy_crash_50": {
        "name": "Energy Prices -50%",
        "params": {"energy_delta_pct": -50},
        "description": "Severe energy price crash of 50%.",
    },
    "construction_delay": {
        "name": "6-Month Construction Delay",
        "params": {"delay_months": 6},
        "description": "6-month construction delay — increases costs and delays revenue generation.",
    },
    "fx_shock_eur_usd": {
        "name": "EUR/USD -15%",
        "params": {"fx_delta_pct": -15, "target_currency": "USD"},
        "description": "EUR weakens 15% vs USD — impacts USD-denominated assets.",
    },
    "combined_downturn": {
        "name": "Market Downturn",
        "params": {"rate_delta_bps": 150, "energy_delta_pct": -20},
        "description": "Combined rate shock and energy price decline — correlated stress scenario.",
    },
    "climate_tail": {
        "name": "Climate Tail Risk",
        "params": {"energy_delta_pct": 15, "delay_months": 3},
        "description": "Supply disruption from extreme weather — delay and temporary energy spike.",
    },
}

_ENERGY_TYPES = {"solar", "wind", "hydro", "biomass", "geothermal", "offshore_wind"}
_CONSTRUCTION_STAGES = {"construction", "development", "construction_ready", "under_construction"}


def apply_stress(project: dict[str, Any], params: dict[str, Any], rng: np.random.Generator) -> float:
    """Apply scenario shocks with randomised magnitude to a project's value.

    Returns stressed NAV value (always >= 0).
    """
    value = float(project.get("current_value", 0))
    if value <= 0:
        return 0.0

    leverage = float(project.get("leverage_ratio", 0.5))
    project_type = str(project.get("project_type", "")).lower()
    stage = str(project.get("stage", "")).lower()
    currency = str(project.get("currency", "EUR")).upper()

    if "rate_delta_bps" in params:
        rate_shock = rng.normal(params["rate_delta_bps"], abs(params["rate_delta_bps"]) * 0.2)
        # Higher leverage amplifies rate impact
        dcf_discount = (rate_shock / 10_000) * (1 + leverage * 2)
        value *= max(0, 1 - dcf_discount)

    if "energy_delta_pct" in params and project_type in _ENERGY_TYPES:
        energy_shock = rng.normal(params["energy_delta_pct"], abs(params["energy_delta_pct"]) * 0.3)
        value *= max(0, 1 + energy_shock / 100)

    if "delay_months" in params and stage in _CONSTRUCTION_STAGES:
        delay = max(0.0, float(rng.normal(params["delay_months"], 2)))
        value *= max(0, 1 - delay * 0.01)  # ~1% value reduction per month delay

    if "fx_delta_pct" in params:
        target_currency = params.get("target_currency", "USD")
        if currency == target_currency:
            fx_shock = rng.normal(params["fx_delta_pct"], abs(params["fx_delta_pct"]) * 0.3)
            value *= max(0, 1 + fx_shock / 100)

    return max(0.0, value)


def run_monte_carlo(
    projects: list[dict[str, Any]],
    params: dict[str, Any],
    simulations: int = 10_000,
    seed: int | None = None,
) -> dict[str, Any]:
    """Run Monte Carlo simulation over a list of portfolio projects.

    Projects: list of dicts with keys: id, name, current_value, project_type, stage,
              currency, leverage_ratio.
    Returns aggregated statistics and histogram data.
    """
    rng = np.random.default_rng(seed)
    base_nav = sum(float(p.get("current_value", 0)) for p in projects)
    results = np.zeros(simulations)

    for i in range(simulations):
        portfolio_nav = sum(apply_stress(p, params, rng) for p in projects)
        results[i] = portfolio_nav

    counts, edges = np.histogram(results, bins=50)

    # Per-project sensitivity (using median stressed value across simulations)
    rng2 = np.random.default_rng(seed)
    sensitivities: list[dict[str, Any]] = []
    for proj in projects:
        stressed_vals = [apply_stress(proj, params, rng2) for _ in range(1000)]
        stressed_median = float(np.median(stressed_vals))
        base_val = float(proj.get("current_value", 0))
        change_pct = ((stressed_median - base_val) / base_val * 100) if base_val > 0 else 0.0
        sensitivities.append({
            "project_id": str(proj.get("id", "")),
            "project_name": proj.get("name", "Unknown"),
            "base_value": base_val,
            "stressed_value": stressed_median,
            "change_pct": round(change_pct, 2),
        })

    mean_nav = float(np.mean(results))
    median_nav = float(np.median(results))
    p5 = float(np.percentile(results, 5))
    p95 = float(np.percentile(results, 95))

    return {
        "base_nav": round(base_nav, 2),
        "mean_nav": round(mean_nav, 2),
        "median_nav": round(median_nav, 2),
        "p5_nav": round(p5, 2),
        "p95_nav": round(p95, 2),
        "var_95": round(max(0, base_nav - p5), 2),
        "max_loss_pct": round(float((np.min(results) - base_nav) / base_nav * 100) if base_nav > 0 else 0, 2),
        "probability_of_loss": round(float(np.sum(results < base_nav) / simulations), 4),
        "histogram": counts.tolist(),
        "histogram_edges": edges.tolist(),
        "project_sensitivities": sorted(sensitivities, key=lambda x: x["change_pct"]),
    }
