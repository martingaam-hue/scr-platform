"""Comprehensive tests for the AI output validator."""
import pytest
from app.validation import AIOutputValidator, ConfidenceLevel, VALIDATION_SCHEMAS

validator = AIOutputValidator()


class TestRobustJsonParsing:
    """Tests for the 5 JSON parsing strategies."""

    def test_direct_json(self):
        result = validator.validate(
            "score_quality",
            '{"score": 75, "reasoning": "Good financial projections with clear assumptions."}',
        )
        assert result.validated
        assert result.data["score"] == 75

    def test_markdown_wrapped_json(self):
        raw = '```json\n{"score": 75, "reasoning": "Good financial projections."}\n```'
        result = validator.validate("score_quality", raw)
        assert result.validated
        assert result.data["score"] == 75
        assert "Stripped markdown code fences" in result.repairs_applied

    def test_json_with_surrounding_text(self):
        raw = 'Here is my analysis:\n{"score": 75, "reasoning": "Good financial projections with clear revenue model."}\nLet me know if you need more.'
        result = validator.validate("score_quality", raw)
        assert result.validated
        assert result.data["score"] == 75
        assert "Extracted JSON object from surrounding text" in result.repairs_applied

    def test_trailing_commas(self):
        raw = '{"score": 75, "reasoning": "Solid analysis.",}'
        result = validator.validate("score_quality", raw)
        assert result.validated
        assert result.data["score"] == 75

    def test_completely_unparseable(self):
        raw = "I think the score should be about 75 because the document looks good."
        result = validator.validate("score_quality", raw)
        assert not result.validated
        assert result.confidence_level == ConfidenceLevel.FAILED
        assert "parse JSON" in result.error


class TestFieldValidation:
    """Tests for field-level validation and repair."""

    def test_score_clamped_above_max(self):
        raw = '{"score": 150, "reasoning": "Excellent document with comprehensive analysis."}'
        result = validator.validate("score_quality", raw)
        assert result.data["score"] == 100
        assert any("Clamped score" in r for r in result.repairs_applied)

    def test_score_clamped_below_min(self):
        raw = '{"score": -10, "reasoning": "Poor document quality overall."}'
        result = validator.validate("score_quality", raw)
        assert result.data["score"] == 0

    def test_score_string_coerced_to_int(self):
        raw = '{"score": "75", "reasoning": "Good document with clear data."}'
        result = validator.validate("score_quality", raw)
        assert result.data["score"] == 75
        assert any("Coerced" in r for r in result.repairs_applied)

    def test_enum_case_insensitive(self):
        raw = '{"fit_score": 80, "recommendation": "Proceed", "executive_summary": "This is a strong investment opportunity with solid fundamentals."}'
        result = validator.validate("score_deal_readiness", raw)
        assert result.data["recommendation"] == "proceed"
        assert any("Fixed" in r and "case" in r for r in result.repairs_applied)

    def test_enum_invalid_value_reset(self):
        raw = '{"fit_score": 80, "recommendation": "maybe", "executive_summary": "This project has interesting characteristics worth exploring further."}'
        result = validator.validate("score_deal_readiness", raw)
        assert result.data["recommendation"] in ["proceed", "pass", "need_more_info"]
        assert any("Reset" in r for r in result.repairs_applied)

    def test_string_wrapped_in_list(self):
        raw = '{"kpis": "revenue: 5M"}'
        result = validator.validate("extract_kpis", raw)
        assert isinstance(result.data["kpis"], list)
        assert result.data["kpis"] == ["revenue: 5M"]

    def test_float_clamped_from_percentage_string(self):
        raw = '{"discount_rate": "12%", "growth_rate": "3%", "reasoning": "Based on market conditions and sector analysis."}'
        result = validator.validate("suggest_assumptions", raw)
        # 12.0 > max (0.50), so clamped to 0.50
        assert result.data["discount_rate"] == 0.50


class TestConfidenceScoring:
    """Tests for confidence heuristics."""

    def test_high_confidence_complete_response(self):
        raw = '{"score": 73, "reasoning": "The financial projections are well-documented with realistic assumptions. Revenue model is clear and backed by market data.", "strengths": ["Clear revenue model", "Detailed cost structure"], "weaknesses": ["No sensitivity analysis"]}'
        result = validator.validate("score_quality", raw)
        assert result.confidence >= 0.7
        assert result.confidence_level in (ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM)

    def test_low_confidence_short_reasoning(self):
        raw = '{"score": 50, "reasoning": "OK."}'
        result = validator.validate("score_quality", raw)
        assert result.confidence < 0.7

    def test_low_confidence_uncertainty_expressed(self):
        raw = '{"score": 40, "reasoning": "Unable to assess due to insufficient data in the document."}'
        result = validator.validate("score_quality", raw)
        assert result.confidence < 0.65

    def test_missing_required_reduces_confidence(self):
        raw = '{"reasoning": "Good document."}'
        result = validator.validate("score_quality", raw)
        assert result.confidence < 0.6

    def test_round_score_slightly_penalized(self):
        result_round = validator.validate(
            "score_quality",
            '{"score": 50, "reasoning": "Average quality document with some good sections."}',
        )
        result_specific = validator.validate(
            "score_quality",
            '{"score": 53, "reasoning": "Average quality document with some good sections."}',
        )
        assert result_specific.confidence > result_round.confidence


class TestFlexibleTasks:
    """Tests for chat/conversational tasks."""

    def test_chat_non_empty_passes(self):
        result = validator.validate("chat", "The project has a strong Signal Score of 78.")
        assert result.validated
        assert result.confidence_level == ConfidenceLevel.HIGH

    def test_chat_empty_fails(self):
        result = validator.validate("chat", "")
        assert not result.validated
        assert result.confidence_level == ConfidenceLevel.FAILED

    def test_chat_whitespace_only_fails(self):
        result = validator.validate("chat", "   \n  ")
        assert not result.validated


class TestSchemaCompleteness:
    """Verify every task_type in MODEL_ROUTING has a validation schema."""

    def test_all_model_routing_tasks_have_schemas(self):
        MODEL_ROUTING_TASKS = [
            "extract_kpis", "extract_clauses", "classify_document", "ocr_extract",
            "summarize_document", "score_quality", "score_deal_readiness", "assess_risk",
            "suggest_assumptions", "generate_valuation_narrative", "find_comparables",
            "explain_match", "generate_memo", "generate_section", "generate_narrative",
            "chat", "chat_with_tools", "classify_sfdr", "check_taxonomy", "extract_esg",
            "review_legal_doc", "suggest_terms",
        ]
        ADDITIONAL_TASKS = [
            "investor_signal_score", "investor_score_improvement",
            "board_advisor_matching", "persona_extraction",
            "risk_mitigation_generation", "risk_monitoring_analysis",
            "legal_document_generation", "legal_document_review",
            "business_plan_section", "capital_efficiency_report",
            "insurance_risk_impact", "market_opportunity_analysis",
            "live_score_enrichment",
        ]
        all_tasks = MODEL_ROUTING_TASKS + ADDITIONAL_TASKS
        missing = [t for t in all_tasks if t not in VALIDATION_SCHEMAS]
        assert missing == [], f"Missing validation schemas for: {missing}"
