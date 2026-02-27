"""Pure deterministic financial calculators. No LLM, no DB calls."""


def calculate_irr(cash_flows: list[float], max_iter: int = 1000, tol: float = 1e-6) -> float | None:
    """Newton-Raphson IRR calculation. Returns percentage (e.g. 15.3 for 15.3%).

    cash_flows[0] is negative (initial investment), rest are positive.
    """
    rate = 0.1
    for _ in range(max_iter):
        npv = sum(cf / (1 + rate) ** i for i, cf in enumerate(cash_flows))
        dnpv = sum(-i * cf / (1 + rate) ** (i + 1) for i, cf in enumerate(cash_flows))
        if abs(dnpv) < 1e-12:
            break
        rate_new = rate - npv / dnpv
        if abs(rate_new - rate) < tol:
            return round(rate_new * 100, 2)
        rate = rate_new
    return None


def calculate_npv(cash_flows: list[float], discount_rate: float) -> float:
    """NPV at given discount rate."""
    return sum(cf / (1 + discount_rate) ** i for i, cf in enumerate(cash_flows))


def calculate_payback(capex: float, annual_net_cash_flow: float) -> float | None:
    """Simple payback period in years."""
    if annual_net_cash_flow <= 0:
        return None
    return round(capex / annual_net_cash_flow, 1)


def calculate_dscr(ebitda: float, annual_debt_service: float) -> float | None:
    """Debt Service Coverage Ratio = EBITDA / Annual Debt Service."""
    if annual_debt_service <= 0:
        return None
    return round(ebitda / annual_debt_service, 2)


def calculate_lcoe(
    capex: float,
    opex_annual: float,
    energy_output_mwh_annual: float,
    discount_rate: float,
    project_lifetime: int,
) -> float | None:
    """Levelized Cost of Energy in $/MWh."""
    if energy_output_mwh_annual <= 0:
        return None
    # LCOE = (sum of discounted costs) / (sum of discounted energy)
    total_cost = 0.0
    total_energy = 0.0
    for year in range(1, project_lifetime + 1):
        disc = (1 + discount_rate) ** year
        total_cost += opex_annual / disc
    total_cost += capex  # CAPEX at year 0
    for year in range(1, project_lifetime + 1):
        disc = (1 + discount_rate) ** year
        total_energy += energy_output_mwh_annual / disc
    return round(total_cost / total_energy, 4) if total_energy > 0 else None


# Capacity factors by project type
CAPACITY_FACTORS: dict[str, float] = {
    "solar": 0.22,
    "solar_pv": 0.22,
    "wind": 0.35,
    "wind_onshore": 0.35,
    "wind_offshore": 0.45,
    "hydro": 0.50,
    "biomass": 0.75,
    "geothermal": 0.85,
    "default": 0.30,
}

# Grid emission factors tCO2e/MWh by region
GRID_EMISSION_FACTORS: dict[str, float] = {
    "US": 0.386,
    "EU": 0.275,
    "UK": 0.233,
    "AU": 0.656,
    "IN": 0.708,
    "CN": 0.581,
    "BR": 0.074,
    "default": 0.450,
}


def estimate_jobs_created(capacity_mw: float | None, project_type: str) -> int:
    """Estimate jobs created: construction + operations FTEs."""
    if not capacity_mw:
        return 25
    construction_jobs_per_mw: dict[str, float] = {
        "solar": 1.8,
        "solar_pv": 1.8,
        "wind": 0.5,
        "wind_onshore": 0.5,
        "default": 1.0,
    }
    ops_jobs_per_mw: dict[str, float] = {
        "solar": 0.2,
        "solar_pv": 0.2,
        "wind": 0.3,
        "wind_onshore": 0.3,
        "default": 0.25,
    }
    cf = construction_jobs_per_mw.get(project_type, 1.0)
    of = ops_jobs_per_mw.get(project_type, 0.25)
    return round((cf + of * 20) * capacity_mw)  # Construction + 20yr ops
