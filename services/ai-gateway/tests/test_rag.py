"""Tests for the production RAG pipeline."""
import pytest
from app.rag import RAGPipeline, CHUNK_CONFIGS, Chunk


class TestSemanticChunking:
    """Test chunking respects document structure."""

    def setup_method(self):
        self.pipeline = RAGPipeline.__new__(RAGPipeline)

    def test_markdown_headers_create_sections(self):
        text = "# Introduction\nThis is the introduction section.\n\n# Financial Summary\nRevenue was $5M in FY2024."
        config = CHUNK_CONFIGS["default"]
        chunks = self.pipeline._semantic_chunk(text, config)
        assert len(chunks) >= 1

    def test_legal_docs_get_larger_chunks(self):
        assert CHUNK_CONFIGS["legal_agreement"]["chunk_size"] > CHUNK_CONFIGS["default"]["chunk_size"]

    def test_small_text_below_min_chunk_skipped(self):
        text = "Short."
        config = CHUNK_CONFIGS["default"]
        chunks = self.pipeline._semantic_chunk(text, config)
        assert len(chunks) == 0

    def test_page_numbers_estimated(self):
        text = "A" * 6000 + "\n\n" + "B" * 3000
        config = {"chunk_size": 10000, "overlap": 0, "min_chunk": 10}
        chunks = self.pipeline._semantic_chunk(text, config)
        for chunk in chunks:
            assert chunk.page_number >= 1

    def test_long_section_split_into_multiple_chunks(self):
        long_para = "word " * 500  # ~2500 chars
        config = CHUNK_CONFIGS["default"]  # chunk_size=1000
        chunks = self.pipeline._semantic_chunk(long_para, config)
        assert len(chunks) > 1

    def test_chunk_has_correct_index_sequence(self):
        text = "Section one content here.\n\nSection two content here.\n\nSection three content."
        config = {"chunk_size": 1000, "overlap": 0, "min_chunk": 5}
        chunks = self.pipeline._semantic_chunk(text, config)
        indices = [c.index for c in chunks]
        assert indices == list(range(len(chunks)))


class TestRRFMerge:
    """Test Reciprocal Rank Fusion."""

    def setup_method(self):
        self.pipeline = RAGPipeline.__new__(RAGPipeline)

    def test_item_in_both_lists_ranked_higher(self):
        semantic = [
            {"id": "a", "metadata": {"text_preview": "text a", "summary": ""}},
            {"id": "b", "metadata": {"text_preview": "text b", "summary": ""}},
        ]
        keyword = [
            {"id": "b", "text": "text b", "summary": "", "metadata": {}, "score": 2.0},
            {"id": "c", "text": "text c", "summary": "", "metadata": {}, "score": 1.5},
        ]
        merged = self.pipeline._rrf_merge(semantic, keyword)
        assert merged[0]["id"] == "b"

    def test_empty_keyword_results_handled(self):
        semantic = [{"id": "a", "metadata": {"text_preview": "text a", "summary": ""}}]
        merged = self.pipeline._rrf_merge(semantic, [])
        assert len(merged) == 1
        assert merged[0]["id"] == "a"

    def test_empty_semantic_results_handled(self):
        keyword = [{"id": "x", "text": "some text", "summary": "", "metadata": {}, "score": 1.0}]
        merged = self.pipeline._rrf_merge([], keyword)
        assert len(merged) == 1

    def test_scores_are_positive(self):
        semantic = [{"id": "a", "metadata": {}}]
        merged = self.pipeline._rrf_merge(semantic, [])
        assert merged[0]["score"] > 0


class TestChunkConfigs:
    """Verify chunk config completeness."""

    def test_default_config_exists(self):
        assert "default" in CHUNK_CONFIGS

    def test_all_configs_have_required_keys(self):
        for name, config in CHUNK_CONFIGS.items():
            assert "chunk_size" in config, f"{name} missing chunk_size"
            assert "overlap" in config, f"{name} missing overlap"
            assert "min_chunk" in config, f"{name} missing min_chunk"
            assert config["overlap"] < config["chunk_size"]

    def test_split_by_size_produces_valid_chunks(self):
        pipeline = RAGPipeline.__new__(RAGPipeline)
        text = "Para one.\n\nPara two.\n\nPara three.\n\nPara four.\n\nPara five."
        chunks = pipeline._split_by_size(text, chunk_size=30, overlap=0)
        assert len(chunks) >= 1
        for chunk in chunks:
            assert len(chunk.strip()) > 0
