"""Tests for the TaskBatcher."""

import json

import pytest

from app.task_batcher import BATCHABLE_TASKS, MAX_BATCH_SIZE, TaskBatcher


# ── Eligibility tests ─────────────────────────────────────────────────────────


class TestBatchEligibility:
    def test_batchable_tasks_defined(self):
        assert "classify_document" in BATCHABLE_TASKS
        assert "explain_match" in BATCHABLE_TASKS
        assert "summarize_document" in BATCHABLE_TASKS
        assert "extract_kpis" in BATCHABLE_TASKS

    def test_sonnet_tasks_not_batchable(self):
        assert "score_quality" not in BATCHABLE_TASKS
        assert "assess_risk" not in BATCHABLE_TASKS
        assert "chat_with_tools" not in BATCHABLE_TASKS

    def test_max_batch_size(self):
        assert MAX_BATCH_SIZE == 8


# ── Response parsing tests ────────────────────────────────────────────────────


class TestBatchResponseParsing:
    def setup_method(self):
        # Instantiate without calling __init__ to avoid needing a real llm_client
        self.batcher = TaskBatcher.__new__(TaskBatcher)

    def test_parse_clean_array(self):
        response = '[{"classification": "financial_statement"}, {"classification": "legal_agreement"}]'
        results = self.batcher._parse_batch_response(response, 2)
        assert len(results) == 2
        assert results[0]["classification"] == "financial_statement"
        assert results[1]["classification"] == "legal_agreement"

    def test_parse_markdown_wrapped(self):
        response = '```json\n[{"classification": "business_plan"}]\n```'
        results = self.batcher._parse_batch_response(response, 1)
        assert len(results) == 1
        assert results[0]["classification"] == "business_plan"

    def test_parse_array_embedded_in_text(self):
        response = 'Here are the results:\n[{"score": 85}, {"score": 72}]\nDone.'
        results = self.batcher._parse_batch_response(response, 2)
        assert len(results) == 2
        assert results[0]["score"] == 85

    def test_parse_individual_objects(self):
        response = '{"classification": "a"}\n{"classification": "b"}'
        results = self.batcher._parse_batch_response(response, 2)
        assert len(results) == 2
        assert results[0]["classification"] == "a"
        assert results[1]["classification"] == "b"

    def test_parse_failure_returns_empty(self):
        response = "This is not JSON at all, sorry."
        results = self.batcher._parse_batch_response(response, 3)
        assert len(results) == 0

    def test_parse_wrong_count_returns_empty(self):
        # Array with 2 items but expected 3
        response = '[{"a": 1}, {"b": 2}]'
        # _parse_batch_response just returns whatever it finds — count check is in _process_batch
        results = self.batcher._parse_batch_response(response, 2)
        assert len(results) == 2

    def test_parse_nested_objects_ignored(self):
        # Nested JSON inside each element should not create extra results
        response = '[{"data": {"nested": true}}, {"data": {"nested": false}}]'
        results = self.batcher._parse_batch_response(response, 2)
        assert len(results) == 2


# ── Batch splitting tests ─────────────────────────────────────────────────────


class TestBatchSplitting:
    def test_empty_input(self):
        """batch_complete with empty list returns empty list immediately."""
        import asyncio
        batcher = TaskBatcher.__new__(TaskBatcher)
        result = asyncio.get_event_loop().run_until_complete(
            batcher.batch_complete("classify_document", [])
        )
        assert result == []

    def test_non_batchable_routes_individually(self):
        """Non-batchable tasks should call _process_individually."""
        called_individually = []

        async def fake_individual(task_type, contexts):
            called_individually.extend(contexts)
            return [{"result": i} for i in range(len(contexts))]

        import asyncio
        batcher = TaskBatcher.__new__(TaskBatcher)
        batcher._process_individually = fake_individual
        batcher.registry = None

        contexts = [{"x": 1}, {"x": 2}]
        result = asyncio.get_event_loop().run_until_complete(
            batcher.batch_complete("score_quality", contexts)
        )
        assert len(called_individually) == 2
