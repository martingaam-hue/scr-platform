"""Investor Signal Score — deterministic 6-dimension scorer.

All logic is pure Python — no LLM, no database calls.
"""

DIMENSION_WEIGHTS: dict[str, float] = {
    "financial_capacity": 0.25,
    "risk_management": 0.20,
    "investment_strategy": 0.20,
    "team_experience": 0.15,
    "esg_commitment": 0.10,
    "platform_readiness": 0.10,
}


def _score_financial_capacity(mandate) -> tuple[float, list[str], list[str]]:
    """
    Score: ticket_size_min set=30, ticket_size_max set=20, target_irr set=30, fund_size/is_active set=20
    Max = 100.
    """
    score = 0.0
    gaps: list[str] = []
    recs: list[str] = []

    # ticket_size_min (30 pts)
    if getattr(mandate, "ticket_size_min", None) is not None and float(mandate.ticket_size_min) > 0:
        score += 30
    else:
        gaps.append("Minimum ticket size not specified")
        recs.append("Define your minimum ticket size to improve deal matching accuracy")

    # ticket_size_max (20 pts)
    if getattr(mandate, "ticket_size_max", None) is not None and float(mandate.ticket_size_max) > 0:
        score += 20
    else:
        gaps.append("Maximum ticket size not specified")
        recs.append("Set a maximum ticket size to filter oversized opportunities")

    # target_irr_min (30 pts)
    if getattr(mandate, "target_irr_min", None) is not None:
        score += 30
    else:
        gaps.append("Target IRR not specified")
        recs.append("Add target IRR range to attract deals matching your return expectations")

    # fund active / is_active (20 pts)
    if getattr(mandate, "is_active", False):
        score += 20
    else:
        gaps.append("Mandate is inactive")
        recs.append("Activate your mandate to participate in deal flow")

    return min(100.0, score), gaps, recs


def _score_risk_management(mandate) -> tuple[float, list[str], list[str]]:
    """
    Score: risk_tolerance set=40, stages len>0=30, geographies len>0=30
    Max = 100.
    """
    score = 0.0
    gaps: list[str] = []
    recs: list[str] = []

    # risk_tolerance (40 pts)
    if getattr(mandate, "risk_tolerance", None) is not None:
        score += 40
    else:
        gaps.append("Risk tolerance not specified")
        recs.append("Specify your risk tolerance level to improve deal quality scoring")

    # stages (30 pts)
    stages = getattr(mandate, "stages", None) or []
    if stages and len(stages) > 0:
        score += 30
    else:
        gaps.append("Preferred investment stages not set")
        recs.append("Define target investment stages (e.g. development, construction-ready) to narrow deal funnel")

    # geographies (30 pts)
    geos = getattr(mandate, "geographies", None) or []
    if geos and len(geos) > 0:
        score += 30
    else:
        gaps.append("Target geographies not specified")
        recs.append("Add target geographies to receive regionally filtered deal opportunities")

    return min(100.0, score), gaps, recs


def _score_investment_strategy(mandate) -> tuple[float, list[str], list[str]]:
    """
    Score: sectors len>0=40, stages len>0=30, mandate active=30
    Max = 100.
    """
    score = 0.0
    gaps: list[str] = []
    recs: list[str] = []

    # sectors (40 pts)
    sectors = getattr(mandate, "sectors", None) or []
    if sectors and len(sectors) > 0:
        score += 40
        if len(sectors) >= 3:
            score = min(100.0, score + 10)  # bonus for diversified sector coverage
    else:
        gaps.append("Target sectors not defined")
        recs.append("Select target sectors to receive sector-aligned deal recommendations")

    # stages (30 pts)
    stages = getattr(mandate, "stages", None) or []
    if stages and len(stages) > 0:
        score += 30
    else:
        gaps.append("Investment stage preference missing")
        recs.append("Specify preferred project stages to refine matching criteria")

    # active mandate (30 pts)
    if getattr(mandate, "is_active", False):
        score += 30
    else:
        gaps.append("Mandate not activated")
        recs.append("Activate mandate to start receiving deal matches")

    return min(100.0, score), gaps, recs


def _score_team_experience(_mandate) -> tuple[float, list[str], list[str]]:
    """
    Stub score: returns 70 by default.
    Future: integrate team profile data from user records.
    """
    score = 70.0
    gaps: list[str] = []
    recs: list[str] = [
        "Complete your team profiles to improve this score",
        "Add LinkedIn profiles and investment track records for team members",
    ]
    return score, gaps, recs


def _score_esg_commitment(mandate) -> tuple[float, list[str], list[str]]:
    """
    Score: esg_requirements set=60, exclusions set=40
    Max = 100.
    """
    score = 0.0
    gaps: list[str] = []
    recs: list[str] = []

    esg_reqs = getattr(mandate, "esg_requirements", None)
    if esg_reqs and (isinstance(esg_reqs, dict) and len(esg_reqs) > 0):
        score += 60
    else:
        gaps.append("ESG requirements not defined")
        recs.append("Define ESG requirements to attract impact-aligned projects and improve investor credibility")

    exclusions = getattr(mandate, "exclusions", None)
    if exclusions and (isinstance(exclusions, dict) and len(exclusions) > 0):
        score += 40
    else:
        gaps.append("ESG exclusion criteria not set")
        recs.append("Add ESG exclusions (e.g. fossil fuels, controversial weapons) to strengthen your impact mandate")

    return min(100.0, score), gaps, recs


def _score_platform_readiness(mandate) -> tuple[float, list[str], list[str]]:
    """
    Score: mandate complete=50, active=30, name set=20
    Max = 100.
    """
    score = 0.0
    gaps: list[str] = []
    recs: list[str] = []

    # Mandate name / completeness (20 pts)
    name = getattr(mandate, "name", None) or ""
    if len(name) >= 3:
        score += 20
    else:
        gaps.append("Mandate name not set")
        recs.append("Give your mandate a descriptive name to improve discoverability")

    # Mandate is active (30 pts)
    if getattr(mandate, "is_active", False):
        score += 30
    else:
        gaps.append("Mandate is inactive — will not appear in matching")
        recs.append("Activate your mandate to participate in the platform matching pipeline")

    # Basic completeness: has sectors + geographies (50 pts split)
    sectors = getattr(mandate, "sectors", None) or []
    geos = getattr(mandate, "geographies", None) or []
    if sectors:
        score += 25
    else:
        gaps.append("Sectors missing from mandate")
    if geos:
        score += 25
    else:
        gaps.append("Geographies missing from mandate")

    return min(100.0, score), gaps, recs


def score_investor(mandate, portfolio_data: dict | None = None) -> dict:
    """
    Compute all 6 dimension scores and overall weighted score.

    Returns:
        {
          "overall_score": float,
          "dimensions": {
            "financial_capacity": {"score": float, "weight": float, "gaps": [...], "recommendations": [...]},
            ...
          },
          "gaps": [str, ...],  # all gaps combined
          "recommendations": [str, ...],  # all recommendations combined
        }
    """
    scorers = {
        "financial_capacity": _score_financial_capacity,
        "risk_management": _score_risk_management,
        "investment_strategy": _score_investment_strategy,
        "team_experience": _score_team_experience,
        "esg_commitment": _score_esg_commitment,
        "platform_readiness": _score_platform_readiness,
    }

    dimensions: dict[str, dict] = {}
    all_gaps: list[str] = []
    all_recommendations: list[str] = []

    for dim_key, scorer_fn in scorers.items():
        score_val, gaps, recs = scorer_fn(mandate)
        dimensions[dim_key] = {
            "score": round(score_val, 2),
            "weight": DIMENSION_WEIGHTS[dim_key],
            "gaps": gaps,
            "recommendations": recs,
        }
        all_gaps.extend(gaps)
        all_recommendations.extend(recs)

    overall = compute_overall({k: v["score"] for k, v in dimensions.items()})

    return {
        "overall_score": round(overall, 2),
        "dimensions": dimensions,
        "gaps": all_gaps,
        "recommendations": all_recommendations,
    }


def compute_overall(dimension_scores: dict[str, float]) -> float:
    """Weighted average across all 6 dimensions."""
    return sum(
        dimension_scores.get(dim, 0.0) * weight
        for dim, weight in DIMENSION_WEIGHTS.items()
    )
