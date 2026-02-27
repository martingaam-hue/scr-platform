"""
ValuationAIAssistant — calls AI Gateway for assumptions and narrative generation.
All financial calculations remain in engine.py (deterministic Python).
"""

from __future__ import annotations

import json
import re
from typing import Any

import httpx
import structlog

from app.core.config import settings
from app.modules.valuation.schemas import AssumptionSuggestion

logger = structlog.get_logger()


class ValuationAIAssistant:
    """Thin wrapper around AI Gateway for valuation-specific prompts."""

    _TIMEOUT = 90.0

    # ── Assumption suggestions ────────────────────────────────────────────────

    async def suggest_assumptions(
        self,
        project_type: str,
        geography: str,
        stage: str,
    ) -> AssumptionSuggestion:
        """
        Ask Claude for reasonable DCF assumptions given project context.
        Returns structured discount rate, growth rate, terminal method,
        projection years, and comparable multiples with reasoning.
        """
        prompt = f"""You are a specialist in infrastructure and alternative investment project finance.

Suggest reasonable DCF valuation assumptions for:
- Project type: {project_type}
- Geography: {geography}
- Development stage: {stage}

Consider:
- Country risk premium and local inflation for geography
- Technology maturity and offtake certainty for project type
- Construction/development risk for stage
- Typical infrastructure project lifetimes (15–30 years)

Respond ONLY with valid JSON in this exact structure:
{{
  "discount_rate": <float between 0.06 and 0.25>,
  "terminal_growth_rate": <float between 0.01 and 0.05>,
  "terminal_method": "gordon",
  "projection_years": <integer between 10 and 30>,
  "comparable_multiples": {{
    "ev_ebitda": <float, typical range 8-16>,
    "ev_mw": <float in USD thousands per MW, typical range 500-2000>
  }},
  "reasoning": {{
    "discount_rate": "<1-2 sentence explanation>",
    "terminal_growth_rate": "<1-2 sentence explanation>",
    "projection_years": "<1 sentence explanation>",
    "comparable_multiples": "<1-2 sentence explanation>"
  }}
}}"""

        try:
            async with httpx.AsyncClient(timeout=self._TIMEOUT) as client:
                resp = await client.post(
                    f"{settings.AI_GATEWAY_URL}/v1/completions",
                    json={
                        "prompt": prompt,
                        "task_type": "analysis",
                        "max_tokens": 600,
                        "temperature": 0.2,
                    },
                    headers={"Authorization": f"Bearer {settings.AI_GATEWAY_API_KEY}"},
                )
                resp.raise_for_status()
                content = resp.json().get("content", "")
        except Exception as exc:
            logger.warning("suggest_assumptions_ai_failed", error=str(exc))
            return self._fallback_assumptions(project_type, geography)

        return self._parse_suggestion(content, project_type, geography)

    def _parse_suggestion(
        self, content: str, project_type: str, geography: str
    ) -> AssumptionSuggestion:
        try:
            match = re.search(r"\{.*\}", content, re.DOTALL)
            raw: dict[str, Any] = json.loads(match.group() if match else content)
            return AssumptionSuggestion(
                discount_rate=float(raw["discount_rate"]),
                terminal_growth_rate=float(raw["terminal_growth_rate"]),
                terminal_method=str(raw.get("terminal_method", "gordon")),
                projection_years=int(raw.get("projection_years", 20)),
                comparable_multiples={
                    k: float(v)
                    for k, v in raw.get("comparable_multiples", {}).items()
                },
                reasoning={
                    k: str(v) for k, v in raw.get("reasoning", {}).items()
                },
            )
        except Exception as exc:
            logger.warning("suggest_assumptions_parse_failed", error=str(exc))
            return self._fallback_assumptions(project_type, geography)

    def _fallback_assumptions(
        self, project_type: str, geography: str
    ) -> AssumptionSuggestion:
        """Rule-based fallback when AI Gateway is unavailable."""
        # High-risk geographies get a country risk premium
        high_risk = {
            "Nigeria", "Kenya", "Ethiopia", "Tanzania", "Bangladesh",
            "Pakistan", "Cambodia", "Myanmar", "Haiti",
        }
        base_dr = 0.14 if geography in high_risk else 0.10

        # Technology risk adjustment
        early_tech = {"geothermal", "sustainable_agriculture", "biomass"}
        dr = base_dr + (0.02 if project_type in early_tech else 0.0)

        return AssumptionSuggestion(
            discount_rate=round(dr, 3),
            terminal_growth_rate=0.02,
            terminal_method="gordon",
            projection_years=20,
            comparable_multiples={"ev_ebitda": 10.0, "ev_mw": 1000.0},
            reasoning={
                "discount_rate": f"Rule-based estimate for {project_type} in {geography}.",
                "terminal_growth_rate": "Conservative long-term inflation-linked growth.",
                "projection_years": "Standard infrastructure asset life assumption.",
                "comparable_multiples": "Market median multiples for similar assets.",
            },
        )

    # ── Narrative generation ──────────────────────────────────────────────────

    async def generate_valuation_narrative(
        self,
        method: str,
        enterprise_value: float,
        equity_value: float,
        currency: str,
        project_type: str,
        geography: str,
        assumptions_summary: dict[str, Any],
    ) -> str:
        """
        Generate an LP-ready valuation summary paragraph.
        Returns plain text (2–3 sentences in investment banking style).
        """
        prompt = f"""You are a senior investment analyst writing a valuation section for an LP report.

Write 2-3 concise sentences summarising this project valuation:
- Method: {method.replace("_", " ").upper()}
- Enterprise Value: {currency} {enterprise_value:,.0f}
- Equity Value: {currency} {equity_value:,.0f}
- Project type: {project_type}
- Geography: {geography}
- Key inputs: {json.dumps(assumptions_summary, indent=2)}

Write in professional investment banking style. Be specific about methodology and conclusion.
Do NOT use bullet points. Output plain prose only."""

        try:
            async with httpx.AsyncClient(timeout=self._TIMEOUT) as client:
                resp = await client.post(
                    f"{settings.AI_GATEWAY_URL}/v1/completions",
                    json={
                        "prompt": prompt,
                        "task_type": "analysis",
                        "max_tokens": 250,
                        "temperature": 0.4,
                    },
                    headers={"Authorization": f"Bearer {settings.AI_GATEWAY_API_KEY}"},
                )
                resp.raise_for_status()
                return resp.json().get("content", "").strip()
        except Exception as exc:
            logger.warning("narrative_generation_failed", error=str(exc))
            return (
                f"The {method.replace('_', ' ').upper()} analysis yields an enterprise value "
                f"of {currency} {enterprise_value:,.0f} and equity value of "
                f"{currency} {equity_value:,.0f}."
            )

    # ── Comparable suggestions ────────────────────────────────────────────────

    async def find_comparables(
        self, project_type: str, geography: str, stage: str
    ) -> list[dict[str, Any]]:
        """
        Suggest representative comparable transactions for the given project context.
        Returns a list of comparable company dicts with multiple estimates.
        """
        prompt = f"""You are a private markets M&A advisor specializing in alternative investments.

List 4-5 representative comparable transactions or publicly traded companies for:
- Project type: {project_type}
- Geography / market: {geography}
- Stage: {stage}

Respond ONLY with valid JSON array:
[
  {{
    "name": "Company or transaction name",
    "ev_ebitda": <typical multiple or null>,
    "ev_mw": <USD thousands per MW or null>,
    "ev_revenue": <multiple or null>,
    "geography": "<country or region>",
    "transaction_date": "<year or null>",
    "notes": "<brief context>"
  }}
]"""

        try:
            async with httpx.AsyncClient(timeout=self._TIMEOUT) as client:
                resp = await client.post(
                    f"{settings.AI_GATEWAY_URL}/v1/completions",
                    json={
                        "prompt": prompt,
                        "task_type": "analysis",
                        "max_tokens": 700,
                        "temperature": 0.3,
                    },
                    headers={"Authorization": f"Bearer {settings.AI_GATEWAY_API_KEY}"},
                )
                resp.raise_for_status()
                content = resp.json().get("content", "")
            match = re.search(r"\[.*\]", content, re.DOTALL)
            return json.loads(match.group() if match else content)
        except Exception as exc:
            logger.warning("find_comparables_failed", error=str(exc))
            return self._fallback_comparables(project_type)

    def _fallback_comparables(self, project_type: str) -> list[dict[str, Any]]:
        defaults: dict[str, list[dict[str, Any]]] = {
            "solar": [
                {"name": "SunPower Corp", "ev_ebitda": 12.0, "ev_mw": 950.0,
                 "geography": "USA", "transaction_date": "2023", "notes": "Utility-scale solar"},
                {"name": "First Solar", "ev_ebitda": 14.0, "ev_mw": 1100.0,
                 "geography": "USA", "transaction_date": "2023", "notes": "Module manufacturer + IPP"},
            ],
            "wind": [
                {"name": "Vestas Wind", "ev_ebitda": 11.0, "ev_mw": 1200.0,
                 "geography": "Europe", "transaction_date": "2023", "notes": "Onshore wind"},
            ],
        }
        return defaults.get(project_type, [
            {"name": "Generic Renewable Asset", "ev_ebitda": 10.0, "ev_mw": 1000.0,
             "geography": "Global", "transaction_date": None, "notes": "Market median estimate"},
        ])
