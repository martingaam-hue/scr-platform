"""Deterministic risk scoring. No AI calls needed."""

from __future__ import annotations

EXPERIENCE_SCORES: dict[str, int] = {
    "none": 10,
    "limited": 30,
    "moderate": 60,
    "extensive": 90,
}

HORIZON_SCORES: dict[int, int] = {1: 10, 3: 30, 5: 50, 7: 70, 10: 90}

LOSS_TOLERANCE_SCORES: dict[int, int] = {5: 10, 10: 25, 20: 50, 30: 75, 50: 95}

LIQUIDITY_SCORES: dict[str, int] = {"high": 15, "moderate": 50, "low": 85}

CONCENTRATION_SCORES: dict[int, int] = {5: 10, 10: 25, 20: 50, 30: 75, 50: 90}

DRAWDOWN_SCORES: dict[int, int] = {5: 10, 10: 25, 20: 50, 30: 75, 50: 95}

ALLOCATIONS: dict[str, dict[str, int]] = {
    "conservative": {
        "private_credit": 40,
        "infrastructure": 30,
        "real_estate": 20,
        "natural_resources": 10,
    },
    "moderate": {
        "private_credit": 30,
        "infrastructure": 25,
        "real_estate": 25,
        "natural_resources": 10,
        "private_equity": 10,
    },
    "balanced": {
        "infrastructure": 25,
        "real_estate": 20,
        "private_equity": 20,
        "private_credit": 15,
        "natural_resources": 10,
        "impact": 10,
    },
    "growth": {
        "private_equity": 30,
        "infrastructure": 20,
        "real_estate": 15,
        "impact": 15,
        "natural_resources": 10,
        "digital_assets": 10,
    },
    "aggressive": {
        "private_equity": 35,
        "digital_assets": 15,
        "impact": 15,
        "infrastructure": 15,
        "natural_resources": 10,
        "specialty": 10,
    },
}

STAGE_RISK: dict[str, int] = {
    "early_stage": 85,
    "development": 70,
    "construction": 55,
    "operational": 30,
    "brownfield": 40,
}

TYPE_RISK: dict[str, int] = {
    "private_credit": 25,
    "infrastructure": 35,
    "real_estate": 40,
    "natural_resources": 50,
    "private_equity": 65,
    "impact": 55,
    "digital_assets": 80,
    "specialty": 70,
}


def _closest_key(mapping: dict[int, int], value: int) -> int:
    """Return the value from mapping whose key is closest to the given value."""
    return mapping[min(mapping.keys(), key=lambda k: abs(k - value))]


def calculate_risk_scores(answers: dict) -> dict:
    """Calculate sophistication and risk appetite scores from assessment answers."""
    sophistication = EXPERIENCE_SCORES.get(answers["experience_level"], 30)

    horizon_score = _closest_key(HORIZON_SCORES, min(answers["investment_horizon_years"], 10))
    loss_score = _closest_key(LOSS_TOLERANCE_SCORES, answers["loss_tolerance_percentage"])
    liquidity_score = LIQUIDITY_SCORES.get(answers["liquidity_needs"], 50)
    concentration_score = _closest_key(CONCENTRATION_SCORES, answers["concentration_max_percentage"])
    drawdown_score = _closest_key(DRAWDOWN_SCORES, answers["max_drawdown_tolerance"])

    risk_appetite = (
        horizon_score * 0.25
        + loss_score * 0.25
        + liquidity_score * 0.20
        + concentration_score * 0.15
        + drawdown_score * 0.15
    )

    if risk_appetite < 25:
        category = "conservative"
    elif risk_appetite < 40:
        category = "moderate"
    elif risk_appetite < 60:
        category = "balanced"
    elif risk_appetite < 80:
        category = "growth"
    else:
        category = "aggressive"

    return {
        "sophistication_score": round(sophistication, 1),
        "risk_appetite_score": round(risk_appetite, 1),
        "risk_category": category,
        "recommended_allocation": ALLOCATIONS[category],
    }


def calculate_risk_compatibility(investor_profile: dict, project: dict) -> float:
    """Calculate risk compatibility between investor and project (0-100)."""
    investor_appetite = investor_profile.get("risk_appetite_score", 50)

    project_risk = (
        STAGE_RISK.get(project.get("stage", "development"), 50) * 0.6
        + TYPE_RISK.get(project.get("project_type", "infrastructure"), 50) * 0.4
    )

    difference = abs(investor_appetite - project_risk)

    if difference <= 10:
        return 95.0
    elif difference <= 20:
        return 80.0
    elif difference <= 30:
        return 65.0
    elif difference <= 40:
        return 45.0
    else:
        return max(20.0, 100.0 - difference * 1.5)
