"""Unit tests for citation parsing — pure regex + static methods, no DB required."""

import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.citations.service import (
    _CONTEXT_CHARS,
    _SOURCE_PATTERN,
    CitationService,
)

# ── Regex pattern tests ───────────────────────────────────────────────────────


class TestSourcePatternRegex:
    def test_simple_source_tag(self):
        matches = _SOURCE_PATTERN.findall("Revenue was $100M [SOURCE: annual_report]")
        assert matches == ["annual_report"]

    def test_pipe_delimited_source(self):
        text = "The IRR is 15% [SOURCE: financial_model | page 5 | IRR calculation]"
        matches = _SOURCE_PATTERN.findall(text)
        assert matches == ["financial_model | page 5 | IRR calculation"]

    def test_multiple_citations_extracted(self):
        text = (
            "Revenue is $10M [SOURCE: doc1]. "
            "Costs are $5M [SOURCE: doc2 | p.3]. "
            "Net margin is 50% [SOURCE: AI_INFERENCE]"
        )
        matches = _SOURCE_PATTERN.findall(text)
        assert len(matches) == 3
        assert "doc1" in matches[0]
        assert "AI_INFERENCE" in matches[2]

    def test_metric_prefix_captured(self):
        matches = _SOURCE_PATTERN.findall("Total AUM is $500M [SOURCE: METRIC: total_aum]")
        assert matches == ["METRIC: total_aum"]

    def test_ai_inference_tag(self):
        matches = _SOURCE_PATTERN.findall("Inference here [SOURCE: AI_INFERENCE]")
        assert matches == ["AI_INFERENCE"]

    def test_no_source_tags_returns_empty(self):
        assert _SOURCE_PATTERN.findall("No citations at all.") == []

    def test_empty_string_returns_empty(self):
        assert _SOURCE_PATTERN.findall("") == []

    def test_whitespace_inside_tag_included(self):
        """Leading/trailing spaces in source ref are captured (stripped in service)."""
        text = "Fact [SOURCE:  my_document  ]"
        matches = _SOURCE_PATTERN.findall(text)
        assert len(matches) == 1
        assert matches[0].strip() == "my_document"

    def test_malformed_unclosed_tag_not_matched(self):
        """Unclosed bracket → no match."""
        assert _SOURCE_PATTERN.findall("Fact [SOURCE: doc_name") == []

    def test_unicode_in_source_name(self):
        text = "Données [SOURCE: rapport_financier_2023_résumé]"
        matches = _SOURCE_PATTERN.findall(text)
        assert matches == ["rapport_financier_2023_résumé"]

    def test_context_chars_constant_positive(self):
        assert _CONTEXT_CHARS > 0


# ── strip_citation_tags ───────────────────────────────────────────────────────


class TestStripCitationTags:
    def test_strips_single_tag(self):
        stripped = CitationService.strip_citation_tags("Revenue was $100M [SOURCE: annual_report].")
        assert "[SOURCE:" not in stripped
        assert "Revenue was $100M" in stripped

    def test_strips_multiple_tags(self):
        stripped = CitationService.strip_citation_tags("A [SOURCE: x] and B [SOURCE: y].")
        assert "[SOURCE:" not in stripped
        assert "A" in stripped
        assert "B" in stripped

    def test_text_without_tags_unchanged(self):
        text = "No citations here."
        assert "No citations here." in CitationService.strip_citation_tags(text)

    def test_empty_string(self):
        assert CitationService.strip_citation_tags("") == ""

    def test_only_tags_leaves_empty_or_whitespace(self):
        stripped = CitationService.strip_citation_tags("[SOURCE: a][SOURCE: b]")
        assert stripped.strip() == ""

    def test_pipe_delimited_tag_stripped(self):
        text = "NPV is $10M [SOURCE: model | sheet1 | cell B5]."
        stripped = CitationService.strip_citation_tags(text)
        assert "[SOURCE:" not in stripped
        assert "NPV is $10M" in stripped


# ── _resolve_source — non-DB branches ────────────────────────────────────────


class TestResolveSourceNonDB:
    """Test METRIC: and AI_INFERENCE branches that never touch the database."""

    def _make_svc(self) -> CitationService:
        mock_db = MagicMock()
        return CitationService(db=mock_db, org_id=uuid.uuid4())

    def test_metric_prefix_returns_metric_snapshot(self):
        svc = self._make_svc()
        result = asyncio.run(svc._resolve_source("METRIC: total_aum"))
        assert result["source_type"] == "metric_snapshot"
        assert result["confidence"] == pytest.approx(0.95)
        assert "total_aum" in result["document_name"]

    def test_ai_inference_returns_ai_inference(self):
        svc = self._make_svc()
        result = asyncio.run(svc._resolve_source("AI_INFERENCE"))
        assert result["source_type"] == "ai_inference"
        assert result["confidence"] == pytest.approx(0.7)

    def test_ai_inference_with_suffix(self):
        """AI_INFERENCE prefix (any trailing text) should still match."""
        svc = self._make_svc()
        result = asyncio.run(svc._resolve_source("AI_INFERENCE: market sizing"))
        # "AI_INFERENCE" is a prefix check with startswith
        assert result["source_type"] == "ai_inference"

    def test_metric_strip_whitespace(self):
        svc = self._make_svc()
        result = asyncio.run(svc._resolve_source("METRIC:  irr_pct "))
        assert result["source_type"] == "metric_snapshot"
        assert result["document_name"].strip() == "irr_pct"


# ── CITATION_INSTRUCTION constant ────────────────────────────────────────────


class TestCitationInstruction:
    def test_instruction_references_source_format(self):
        assert "[SOURCE:" in CitationService.CITATION_INSTRUCTION

    def test_instruction_mentions_metric_format(self):
        assert "METRIC:" in CitationService.CITATION_INSTRUCTION

    def test_instruction_mentions_ai_inference(self):
        assert "AI_INFERENCE" in CitationService.CITATION_INSTRUCTION
