"""AI output validation — sits inside route_completion() before returning to callers.

Every LLM response is validated against a schema for its task_type.
Modules get validated + repaired data automatically without changing their code.
"""

from __future__ import annotations

import json
import re
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel


class ConfidenceLevel(str, Enum):
    HIGH = "high"      # 0.80–1.00 — use without review
    MEDIUM = "medium"  # 0.50–0.79 — use but flag for review
    LOW = "low"        # 0.20–0.49 — use with warning
    FAILED = "failed"  # 0.00–0.19 — don't use, return error


class ValidatedResponse(BaseModel):
    data: Optional[dict] = None
    raw_text: str
    confidence: float          # 0.0 to 1.0
    confidence_level: ConfidenceLevel
    validated: bool
    repairs_applied: list[str] = []   # What was fixed
    warnings: list[str] = []          # Issues detected but not fixable
    error: Optional[str] = None


# ── Validation schemas — one per task_type in MODEL_ROUTING ──────────────────
#
# Required: fields that MUST be present for the output to be useful.
# Fields: per-field type + range/enum/length rules — validate and repair.
# flexible: True → only check non-empty (used for chat/conversational tasks).

VALIDATION_SCHEMAS: dict[str, dict] = {

    # ── Document Intelligence ─────────────────────────────────────────────────

    "classify_document": {
        "required": ["classification", "confidence"],
        "fields": {
            "classification": {"type": "str", "max_length": 100},
            "confidence": {"type": "float", "min": 0.0, "max": 1.0},
        },
    },
    "extract_kpis": {
        "required": ["kpis"],
        "fields": {
            "kpis": {"type": "list", "min_items": 0},
        },
    },
    "extract_clauses": {
        "required": ["clauses"],
        "fields": {
            "clauses": {"type": "list"},
        },
    },
    "ocr_extract": {
        "required": ["text"],
        "fields": {
            "text": {"type": "str", "min_length": 1},
        },
    },
    "summarize_document": {
        "required": ["summary"],
        "fields": {
            "summary": {"type": "str", "min_length": 20, "max_length": 3000},
        },
    },

    # ── Signal Score ──────────────────────────────────────────────────────────

    "score_quality": {
        "required": ["score", "reasoning"],
        "fields": {
            "score": {"type": "int", "min": 0, "max": 100},
            "reasoning": {"type": "str", "min_length": 10, "max_length": 1000},
            "strengths": {"type": "list"},
            "weaknesses": {"type": "list"},
            "recommendation": {"type": "str", "max_length": 500},
        },
    },
    "score_deal_readiness": {
        "required": ["fit_score", "recommendation", "executive_summary"],
        "fields": {
            "fit_score": {"type": "int", "min": 0, "max": 100},
            "recommendation": {"type": "str", "enum": ["proceed", "pass", "need_more_info"]},
            "executive_summary": {"type": "str", "min_length": 50},
            "strengths": {"type": "list"},
            "risks": {"type": "list"},
        },
    },
    "assess_risk": {
        "required": ["overall_score", "domain_scores"],
        "fields": {
            "overall_score": {"type": "float", "min": 0, "max": 100},
            "domain_scores": {"type": "dict"},
        },
    },

    # ── Investor Signal Score ─────────────────────────────────────────────────

    "investor_signal_score": {
        "required": ["overall_score", "dimensions"],
        "fields": {
            "overall_score": {"type": "float", "min": 0, "max": 100},
            "dimensions": {"type": "dict"},
        },
    },
    "investor_score_improvement": {
        "required": ["improvements"],
        "fields": {
            "improvements": {"type": "list", "min_items": 1},
        },
    },

    # ── Deal Intelligence ─────────────────────────────────────────────────────

    "screen_deal": {
        "required": ["fit_score", "recommendation", "executive_summary"],
        "fields": {
            "fit_score": {"type": "int", "min": 0, "max": 100},
            "recommendation": {"type": "str", "enum": ["proceed", "pass", "need_more_info"]},
            "executive_summary": {"type": "str", "min_length": 50},
            "strengths": {"type": "list"},
            "risks": {"type": "list"},
            "questions_to_ask": {"type": "list"},
        },
    },

    # ── Compliance & ESG ──────────────────────────────────────────────────────

    "classify_sfdr": {
        "required": ["classification", "reasoning"],
        "fields": {
            "classification": {"type": "str", "enum": ["article_6", "article_8", "article_9"]},
            "reasoning": {"type": "str", "min_length": 20},
        },
    },
    "check_taxonomy": {
        "required": ["aligned_percentage", "assessment"],
        "fields": {
            "aligned_percentage": {"type": "float", "min": 0, "max": 100},
            "assessment": {"type": "str", "min_length": 20},
        },
    },
    "extract_esg": {
        "required": ["metrics"],
        "fields": {
            "metrics": {"type": "dict"},
        },
    },
    "risk_mitigation_generation": {
        "required": ["strategies"],
        "fields": {
            "strategies": {"type": "list", "min_items": 1},
        },
    },
    "risk_monitoring_analysis": {
        "required": ["severity", "summary"],
        "fields": {
            "severity": {"type": "str", "enum": ["info", "warning", "critical"]},
            "summary": {"type": "str", "min_length": 10},
        },
    },

    # ── Matching ──────────────────────────────────────────────────────────────

    "explain_match": {
        "required": ["explanation"],
        "fields": {
            "explanation": {"type": "str", "min_length": 20, "max_length": 500},
        },
    },

    # ── Valuation ─────────────────────────────────────────────────────────────

    "suggest_assumptions": {
        "required": ["discount_rate", "growth_rate", "reasoning"],
        "fields": {
            "discount_rate": {"type": "float", "min": 0.01, "max": 0.50},
            "growth_rate": {"type": "float", "min": -0.10, "max": 0.30},
            "reasoning": {"type": "str", "min_length": 20},
        },
    },
    "generate_valuation_narrative": {
        "required": ["narrative"],
        "fields": {
            "narrative": {"type": "str", "min_length": 50},
        },
    },
    "find_comparables": {
        "required": ["comparables"],
        "fields": {
            "comparables": {"type": "list", "min_items": 1},
        },
    },

    # ── Business Planning ─────────────────────────────────────────────────────

    "business_plan_section": {
        "required": ["content"],
        "fields": {
            "content": {"type": "str", "min_length": 100},
        },
    },

    # ── Legal ─────────────────────────────────────────────────────────────────

    "review_legal_doc": {
        "required": ["risk_score", "summary"],
        "fields": {
            "risk_score": {"type": "int", "min": 0, "max": 100},
            "summary": {"type": "str", "min_length": 50},
            "clause_analyses": {"type": "list"},
            "recommendations": {"type": "list"},
        },
    },
    "suggest_terms": {
        "required": ["terms"],
        "fields": {
            "terms": {"type": "list", "min_items": 1},
        },
    },
    "legal_document_generation": {
        "required": ["document_content"],
        "fields": {
            "document_content": {"type": "str", "min_length": 200},
        },
    },
    "legal_document_review": {
        "required": ["issues", "overall_assessment"],
        "fields": {
            "issues": {"type": "list"},
            "overall_assessment": {"type": "str", "min_length": 20},
        },
    },

    # ── Advisory ─────────────────────────────────────────────────────────────

    "board_advisor_matching": {
        "required": ["matches"],
        "fields": {
            "matches": {"type": "list"},
        },
    },
    "persona_extraction": {
        "required": ["strategy_type", "asset_types"],
        "fields": {
            "strategy_type": {"type": "str"},
            "asset_types": {"type": "list", "min_items": 1},
        },
    },

    # ── Reports ───────────────────────────────────────────────────────────────

    "generate_memo": {
        "required": ["content"],
        "fields": {
            "content": {"type": "str", "min_length": 200},
        },
    },
    "generate_section": {
        "required": ["content"],
        "fields": {
            "content": {"type": "str", "min_length": 50},
        },
    },
    "generate_narrative": {
        "required": ["narrative"],
        "fields": {
            "narrative": {"type": "str", "min_length": 50},
        },
    },

    # ── Conversational (flexible — just check non-empty) ──────────────────────

    "chat": {
        "required": [],
        "fields": {},
        "flexible": True,
    },
    "chat_with_tools": {
        "required": [],
        "fields": {},
        "flexible": True,
    },

    # ── Digest ────────────────────────────────────────────────────────────────

    "generate_digest_summary": {
        "required": [],
        "fields": {},
        "flexible": True,  # plain prose output, no JSON validation
    },

    # ── Additional task types ─────────────────────────────────────────────────

    "insurance_risk_impact": {
        "required": ["impact_score", "recommendation"],
        "fields": {
            "impact_score": {"type": "float", "min": 0, "max": 100},
            "recommendation": {"type": "str"},
        },
    },
    "capital_efficiency_report": {
        "required": ["metrics", "narrative"],
        "fields": {
            "metrics": {"type": "dict"},
            "narrative": {"type": "str", "min_length": 50},
        },
    },
    "market_opportunity_analysis": {
        "required": ["analysis"],
        "fields": {
            "analysis": {"type": "dict"},
        },
    },
    "live_score_enrichment": {
        "required": ["enrichment"],
        "fields": {
            "enrichment": {"type": "dict"},
        },
    },

    # ── Due Diligence ─────────────────────────────────────────────────────────

    "dd_review_item": {
        "required": ["satisfied", "confidence", "summary"],
        "fields": {
            "satisfied": {"type": "bool"},
            "confidence": {"type": "float", "min": 0.0, "max": 1.0},
            "summary": {"type": "str", "min_length": 10, "max_length": 2000},
            "gaps": {"type": "list"},
            "recommendation": {"type": "str", "max_length": 500},
        },
    },

    # ── ESG Impact Dashboard ──────────────────────────────────────────────────

    "generate_esg_narrative": {
        "required": ["narrative", "key_achievements", "areas_for_improvement"],
        "fields": {
            "narrative": {"type": "str", "min_length": 50, "max_length": 4000},
            "key_achievements": {"type": "list", "min_items": 0},
            "areas_for_improvement": {"type": "list", "min_items": 0},
        },
    },

    # ── LP Reporting ──────────────────────────────────────────────────────────

    "generate_lp_report_narrative": {
        "required": ["executive_summary", "portfolio_commentary", "market_outlook"],
        "fields": {
            "executive_summary": {"type": "str", "min_length": 100, "max_length": 3000},
            "portfolio_commentary": {"type": "str", "min_length": 100, "max_length": 5000},
            "market_outlook": {"type": "str", "min_length": 50, "max_length": 3000},
            "esg_highlights": {"type": "str", "max_length": 2000},
        },
    },

    # ── Comparable Transactions ───────────────────────────────────────────────

    "rank_comparable_transactions": {
        "required": ["ranked_comps"],
        "fields": {
            "ranked_comps": {"type": "list", "min_items": 0},
        },
    },

    # ── Document Version Control ──────────────────────────────────────────────

    "summarize_doc_changes": {
        "required": ["summary", "significance"],
        "fields": {
            "summary": {"type": "str", "min_length": 20, "max_length": 2000},
            "significance": {"type": "str", "enum": ["minor", "moderate", "major", "critical"]},
            "key_changes": {"type": "list", "min_items": 0},
        },
    },

    # ── Meeting Prep ──────────────────────────────────────────────────────────

    "generate_meeting_briefing": {
        "required": ["executive_summary", "talking_points", "questions_to_ask"],
        "fields": {
            "executive_summary": {"type": "str", "min_length": 50, "max_length": 2000},
            "key_metrics": {"type": "dict"},
            "risk_flags": {"type": "list"},
            "dd_progress": {"type": "dict"},
            "talking_points": {"type": "list", "min_items": 1},
            "questions_to_ask": {"type": "list", "min_items": 1},
            "changes_since_last": {"type": "list"},
        },
    },

    # ── Smart Screener ────────────────────────────────────────────────────────

    "parse_screener_query": {
        "required": [],
        "fields": {
            "project_types": {"type": "list"},
            "geographies": {"type": "list"},
            "stages": {"type": "list"},
            "min_signal_score": {"type": "int", "min": 0, "max": 100},
            "max_signal_score": {"type": "int", "min": 0, "max": 100},
            "min_ticket_size": {"type": "float", "min": 0},
            "max_ticket_size": {"type": "float", "min": 0},
            "min_capacity_mw": {"type": "float", "min": 0},
            "max_capacity_mw": {"type": "float", "min": 0},
            "sector_keywords": {"type": "list"},
            "esg_requirements": {"type": "list"},
            "sort_by": {"type": "str", "enum": ["signal_score", "match_score", "created_at"]},
        },
    },
}


class AIOutputValidator:
    """
    Validates every LLM response against its task_type schema.
    Sits inside route_completion() — callers get validated data automatically.
    """

    def validate(self, task_type: str, raw_response: str) -> ValidatedResponse:
        schema = VALIDATION_SCHEMAS.get(task_type)

        if not schema:
            return ValidatedResponse(
                data=None,
                raw_text=raw_response,
                confidence=0.5,
                confidence_level=ConfidenceLevel.MEDIUM,
                validated=False,
                warnings=[f"No validation schema for task_type: {task_type}"],
            )

        # Flexible tasks (chat) — just check non-empty
        if schema.get("flexible"):
            if raw_response and len(raw_response.strip()) > 0:
                return ValidatedResponse(
                    data={"content": raw_response},
                    raw_text=raw_response,
                    confidence=0.8,
                    confidence_level=ConfidenceLevel.HIGH,
                    validated=True,
                )
            return ValidatedResponse(
                data=None,
                raw_text=raw_response,
                confidence=0.0,
                confidence_level=ConfidenceLevel.FAILED,
                validated=False,
                error="Empty response from LLM",
            )

        # Step 1: Parse JSON robustly
        parsed, parse_repairs = self._robust_json_parse(raw_response)
        if parsed is None:
            return ValidatedResponse(
                data=None,
                raw_text=raw_response,
                confidence=0.0,
                confidence_level=ConfidenceLevel.FAILED,
                validated=False,
                error="Failed to parse JSON from LLM response",
            )

        repairs = list(parse_repairs)
        warnings: list[str] = []

        # Step 2: Check required fields
        missing = [f for f in schema.get("required", []) if f not in parsed]
        if missing:
            warnings.append(f"Missing required fields: {missing}")

        # Step 3: Validate and repair each field
        for field_name, rules in schema.get("fields", {}).items():
            if field_name not in parsed:
                continue
            repaired, repair_note = self._validate_field(field_name, parsed[field_name], rules)
            if repair_note:
                repairs.append(repair_note)
            parsed[field_name] = repaired

        # Step 4: Calculate confidence
        confidence = self._calculate_confidence(parsed, schema, missing, repairs)

        if confidence >= 0.8:
            level = ConfidenceLevel.HIGH
        elif confidence >= 0.5:
            level = ConfidenceLevel.MEDIUM
        elif confidence >= 0.2:
            level = ConfidenceLevel.LOW
        else:
            level = ConfidenceLevel.FAILED

        return ValidatedResponse(
            data=parsed,
            raw_text=raw_response,
            confidence=confidence,
            confidence_level=level,
            validated=True,
            repairs_applied=repairs,
            warnings=warnings,
        )

    # ── JSON parsing (5 strategies) ───────────────────────────────────────────

    def _robust_json_parse(self, text: str) -> tuple[Optional[dict], list[str]]:
        repairs: list[str] = []

        # Strategy 1: Direct parse
        try:
            return json.loads(text), repairs
        except json.JSONDecodeError:
            pass

        # Strategy 2: Strip markdown code fences
        cleaned = re.sub(r"```(?:json)?\s*", "", text)
        cleaned = re.sub(r"```\s*$", "", cleaned).strip()
        try:
            repairs.append("Stripped markdown code fences")
            return json.loads(cleaned), repairs
        except json.JSONDecodeError:
            pass

        # Strategy 3: Find first JSON object
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            try:
                repairs.append("Extracted JSON object from surrounding text")
                return json.loads(match.group()), repairs
            except json.JSONDecodeError:
                pass

        # Strategy 4: Find JSON array
        match = re.search(r"\[[\s\S]*\]", text)
        if match:
            try:
                repairs.append("Extracted JSON array from surrounding text")
                return {"items": json.loads(match.group())}, repairs
            except json.JSONDecodeError:
                pass

        # Strategy 5: Fix common LLM issues (trailing commas, single quotes)
        fixed = text.replace("'", '"')
        fixed = re.sub(r",\s*([}\]])", r"\1", fixed)
        try:
            repairs.append("Fixed quotes and trailing commas")
            return json.loads(fixed), repairs
        except json.JSONDecodeError:
            pass

        return None, repairs

    # ── Field validation ──────────────────────────────────────────────────────

    def _validate_field(
        self, name: str, value: Any, rules: dict
    ) -> tuple[Any, Optional[str]]:
        expected_type = rules.get("type")

        if expected_type == "int":
            if not isinstance(value, (int, float)):
                try:
                    value = int(float(str(value).replace(",", "")))
                    return self._clamp_int(name, value, rules), f"Coerced {name} to int"
                except (ValueError, TypeError):
                    return rules.get("min", 0), f"Reset {name} to minimum (unparseable)"
            value = int(value)
            clamped = self._clamp_int(name, value, rules)
            if clamped != value:
                return clamped, f"Clamped {name} from {value} to {'min' if clamped == rules.get('min') else 'max'} {clamped}"
            return value, None

        elif expected_type == "float":
            if not isinstance(value, (int, float)):
                try:
                    value = float(str(value).replace("%", "").replace(",", ""))
                    return self._clamp_float(name, value, rules), f"Coerced {name} to float"
                except (ValueError, TypeError):
                    return rules.get("min", 0.0), f"Reset {name} to minimum (unparseable)"
            value = float(value)
            clamped = self._clamp_float(name, value, rules)
            if clamped != value:
                return clamped, f"Clamped {name} from {value} to {'min' if clamped == rules.get('min') else 'max'} {clamped}"
            return value, None

        elif expected_type == "str":
            if not isinstance(value, str):
                return str(value), f"Coerced {name} to string"
            if "enum" in rules and value not in rules["enum"]:
                lower_map = {v.lower(): v for v in rules["enum"]}
                if value.lower() in lower_map:
                    canonical = lower_map[value.lower()]
                    return canonical, f"Fixed {name} case: '{value}' → '{canonical}'"
                return rules["enum"][0], f"Reset {name} to '{rules['enum'][0]}' (invalid: '{value}')"
            if "max_length" in rules and len(value) > rules["max_length"]:
                return value[: rules["max_length"]], f"Truncated {name} to {rules['max_length']} chars"
            return value, None

        elif expected_type == "list":
            if not isinstance(value, list):
                if isinstance(value, str):
                    return [value], f"Wrapped {name} string in list"
                return [], f"Reset {name} to empty list (was {type(value).__name__})"
            return value, None

        elif expected_type == "dict":
            if not isinstance(value, dict):
                return {}, f"Reset {name} to empty dict (was {type(value).__name__})"
            return value, None

        return value, None

    def _clamp_int(self, name: str, value: int, rules: dict) -> int:
        if "min" in rules and value < rules["min"]:
            return rules["min"]
        if "max" in rules and value > rules["max"]:
            return rules["max"]
        return value

    def _clamp_float(self, name: str, value: float, rules: dict) -> float:
        if "min" in rules and value < rules["min"]:
            return rules["min"]
        if "max" in rules and value > rules["max"]:
            return rules["max"]
        return value

    # ── Confidence scoring ────────────────────────────────────────────────────

    def _calculate_confidence(
        self,
        parsed: dict,
        schema: dict,
        missing_required: list[str],
        repairs: list[str],
    ) -> float:
        confidence = 0.85  # Base for valid, parsed output

        # Penalize proportionally for missing required fields
        required_count = len(schema.get("required", []))
        if required_count > 0 and missing_required:
            confidence -= 0.30 * (len(missing_required) / required_count)

        # Penalize for each repair (something was wrong)
        confidence -= 0.05 * min(len(repairs), 5)

        # Heuristic: short or uncertain reasoning
        reasoning = parsed.get("reasoning", "")
        if isinstance(reasoning, str):
            if 0 < len(reasoning) < 30:
                confidence -= 0.10
            uncertainty_phrases = [
                "cannot determine", "insufficient data", "unclear",
                "not enough information", "unable to assess", "i cannot",
                "limited information", "no data available",
            ]
            if any(phrase in reasoning.lower() for phrase in uncertainty_phrases):
                confidence -= 0.15

        # Heuristic: suspiciously round scores
        score = (
            parsed.get("score")
            or parsed.get("fit_score")
            or parsed.get("overall_score")
            or parsed.get("risk_score")
        )
        if isinstance(score, (int, float)):
            if score in (0, 50, 100):
                confidence -= 0.08
            elif score in (25, 75):
                confidence -= 0.03

        # Heuristic: empty optional fields
        all_fields = set(schema.get("fields", {}).keys())
        optional_fields = all_fields - set(schema.get("required", []))
        missing_optional = optional_fields - set(parsed.keys())
        if optional_fields and missing_optional:
            confidence -= 0.02 * len(missing_optional)

        return max(0.0, min(1.0, round(confidence, 3)))
