"""Matching Algorithm — pure deterministic scoring, no LLM.

All calculations are reproducible Python arithmetic. Score breakdown is
stored in MatchResult.score_breakdown for full auditability.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from app.models.investors import InvestorMandate
from app.models.projects import Project, SignalScore


# ── Adjacent sector groupings ─────────────────────────────────────────────────

_ADJACENT_SECTORS: dict[str, set[str]] = {
    "solar":                   {"wind", "geothermal", "hydro"},
    "wind":                    {"solar", "geothermal"},
    "hydro":                   {"solar", "geothermal"},
    "geothermal":              {"solar", "wind", "hydro"},
    "energy_efficiency":       {"green_building"},
    "green_building":          {"energy_efficiency"},
    "biomass":                 {"sustainable_agriculture"},
    "sustainable_agriculture": {"biomass"},
    "other":                   set(),
}

# ── Adjacent stage ordering ───────────────────────────────────────────────────

_STAGE_ORDER = [
    "concept",
    "pre_development",
    "development",
    "construction_ready",
    "under_construction",
    "operational",
]

# ── Geography region grouping ─────────────────────────────────────────────────

_REGIONS: dict[str, set[str]] = {
    "Africa":        {"NG", "KE", "GH", "ZA", "ET", "TZ", "UG", "SN", "CI", "CM"},
    "Asia":          {"IN", "CN", "ID", "PH", "BD", "VN", "TH", "PK", "MM", "KH"},
    "Latin America": {"BR", "MX", "CO", "AR", "CL", "PE", "EC", "VE", "UY", "PY"},
    "Europe":        {"DE", "FR", "GB", "ES", "IT", "PL", "NL", "SE", "NO", "DK"},
    "Middle East":   {"SA", "AE", "QA", "KW", "BH", "JO", "LB", "EG", "MA", "TN"},
    "North America": {"US", "CA", "MX"},
    "Southeast Asia":{"ID", "PH", "VN", "TH", "MY", "SG", "MM", "KH", "LA", "BN"},
    "Oceania":       {"AU", "NZ", "FJ", "PG"},
}


def _country_region(country: str) -> str | None:
    for region, countries in _REGIONS.items():
        if country in countries:
            return region
    return None


@dataclass
class AlignmentScore:
    overall: int
    sector: int
    geography: int
    ticket_size: int
    stage: int
    risk_return: int
    esg: int
    breakdown: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall": self.overall,
            "sector": self.sector,
            "geography": self.geography,
            "ticket_size": self.ticket_size,
            "stage": self.stage,
            "risk_return": self.risk_return,
            "esg": self.esg,
            "breakdown": self.breakdown,
        }


class MatchingAlgorithm:
    """
    Deterministic alignment scoring between an InvestorMandate and a Project.

    Total: 100 points across 6 dimensions.
    """

    def calculate_alignment(
        self,
        mandate: InvestorMandate,
        project: Project,
        signal_score: SignalScore | None = None,
    ) -> AlignmentScore:
        sector_pts, sector_detail = self._score_sector(mandate, project)
        geo_pts, geo_detail = self._score_geography(mandate, project)
        ticket_pts, ticket_detail = self._score_ticket_size(mandate, project)
        stage_pts, stage_detail = self._score_stage(mandate, project)
        rr_pts, rr_detail = self._score_risk_return(mandate, project, signal_score)
        esg_pts, esg_detail = self._score_esg(mandate, project)

        overall = sector_pts + geo_pts + ticket_pts + stage_pts + rr_pts + esg_pts

        return AlignmentScore(
            overall=overall,
            sector=sector_pts,
            geography=geo_pts,
            ticket_size=ticket_pts,
            stage=stage_pts,
            risk_return=rr_pts,
            esg=esg_pts,
            breakdown={
                "sector": sector_detail,
                "geography": geo_detail,
                "ticket_size": ticket_detail,
                "stage": stage_detail,
                "risk_return": rr_detail,
                "esg": esg_detail,
            },
        )

    # ── Dimension scorers ──────────────────────────────────────────────────

    def _score_sector(
        self, mandate: InvestorMandate, project: Project
    ) -> tuple[int, dict]:
        sectors = mandate.sectors or []
        pt = project.project_type.value

        if pt in sectors:
            return 25, {"result": "exact_match", "project_type": pt}

        for s in sectors:
            if pt in _ADJACENT_SECTORS.get(s, set()):
                return 15, {"result": "adjacent_match", "project_type": pt, "matched_via": s}

        return 0, {"result": "no_match", "project_type": pt, "mandate_sectors": sectors}

    def _score_geography(
        self, mandate: InvestorMandate, project: Project
    ) -> tuple[int, dict]:
        geos = mandate.geographies or []
        country = project.geography_country

        if not geos:
            return 10, {"result": "global_mandate"}

        if country in geos:
            return 20, {"result": "exact_country", "country": country}

        project_region = _country_region(country)
        if project_region:
            for g in geos:
                mandate_region = _country_region(g)
                if mandate_region == project_region:
                    return 15, {"result": "same_region", "region": project_region}

        return 0, {"result": "no_match", "country": country}

    def _score_ticket_size(
        self, mandate: InvestorMandate, project: Project
    ) -> tuple[int, dict]:
        investment = project.total_investment_required
        lo = mandate.ticket_size_min
        hi = mandate.ticket_size_max

        if lo <= investment <= hi:
            return 20, {"result": "within_range", "investment": str(investment)}

        # Within 20% outside range
        tolerance_20 = (hi - lo) * Decimal("0.20")
        if (lo - tolerance_20) <= investment <= (hi + tolerance_20):
            return 15, {"result": "within_20pct", "investment": str(investment)}

        # Within 50% outside range
        tolerance_50 = (hi - lo) * Decimal("0.50")
        if (lo - tolerance_50) <= investment <= (hi + tolerance_50):
            return 10, {"result": "within_50pct", "investment": str(investment)}

        return 0, {"result": "outside_range", "investment": str(investment),
                   "range": f"{lo}–{hi}"}

    def _score_stage(
        self, mandate: InvestorMandate, project: Project
    ) -> tuple[int, dict]:
        stages = mandate.stages or []
        ps = project.stage.value

        if not stages:
            return 10, {"result": "all_stages_accepted"}

        if ps in stages:
            return 15, {"result": "exact_match", "stage": ps}

        # Adjacent stage (±1 in order)
        if ps in _STAGE_ORDER:
            idx = _STAGE_ORDER.index(ps)
            neighbors = set()
            if idx > 0:
                neighbors.add(_STAGE_ORDER[idx - 1])
            if idx < len(_STAGE_ORDER) - 1:
                neighbors.add(_STAGE_ORDER[idx + 1])
            if any(s in stages for s in neighbors):
                return 10, {"result": "adjacent_match", "stage": ps}

        return 0, {"result": "no_match", "stage": ps, "mandate_stages": stages}

    def _score_risk_return(
        self,
        mandate: InvestorMandate,
        project: Project,
        signal_score: SignalScore | None,
    ) -> tuple[int, dict]:
        if signal_score is None:
            return 5, {"result": "no_signal_score", "note": "Default partial score"}

        ss = signal_score.overall_score
        tolerance = mandate.risk_tolerance.value

        # Risk tolerance thresholds for signal score
        thresholds = {
            "conservative": 75,
            "moderate": 60,
            "aggressive": 40,
        }
        threshold = thresholds.get(tolerance, 60)

        if ss >= threshold:
            return 10, {"result": "above_threshold", "signal_score": ss, "threshold": threshold}
        elif ss >= threshold - 20:
            return 5, {"result": "within_range", "signal_score": ss, "threshold": threshold}
        else:
            return 0, {"result": "below_threshold", "signal_score": ss, "threshold": threshold}

    def _score_esg(
        self, mandate: InvestorMandate, project: Project
    ) -> tuple[int, dict]:
        esg_req = mandate.esg_requirements or {}
        if not esg_req:
            # No explicit ESG requirements — renewable/green projects get full marks
            green_types = {
                "solar", "wind", "hydro", "geothermal",
                "energy_efficiency", "green_building",
            }
            if project.project_type.value in green_types:
                return 10, {"result": "inherently_green"}
            return 5, {"result": "partial_no_requirements"}

        exclusions = mandate.exclusions or {}
        excluded_sectors = exclusions.get("sectors", [])
        if project.project_type.value in excluded_sectors:
            return 0, {"result": "excluded_sector"}

        min_esg_score = esg_req.get("min_score", 0)
        # Without an ESG score on the project, we assume partial compliance
        return 5, {"result": "partial_meets", "min_required": min_esg_score}

    # ── Batch helpers ──────────────────────────────────────────────────────

    def rank_projects(
        self,
        mandate: InvestorMandate,
        projects_with_scores: list[tuple[Project, SignalScore | None]],
    ) -> list[tuple[Project, SignalScore | None, AlignmentScore]]:
        """Score all projects against a mandate and return sorted by overall desc."""
        results = [
            (p, ss, self.calculate_alignment(mandate, p, ss))
            for p, ss in projects_with_scores
        ]
        results.sort(key=lambda x: x[2].overall, reverse=True)
        return results
