"""Production RAG Pipeline for SCR Platform.

Architecture:
  Document upload → S5 process_document() → calls rag.ingest_document()
  Query time → semantic (Pinecone) + keyword (ES) → RRF merge → Haiku rerank

Key design decisions:
  - Semantic chunking respects section/paragraph boundaries
  - Document-type-aware chunk sizes (legal docs need larger chunks)
  - Chunk summaries via Haiku improve embedding quality significantly
  - Dual index: Pinecone (semantic) + ES (keyword) with Reciprocal Rank Fusion
  - Haiku reranking for top candidates (~500ms overhead, major quality gain)
  - Per-org namespace isolation in Pinecone
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from typing import Any
from uuid import UUID

import structlog

logger = structlog.get_logger()

# ── Chunking configuration per document type ──────────────────────────────────

CHUNK_CONFIGS: dict[str, dict[str, int]] = {
    "financial_statement":      {"chunk_size": 600,  "overlap": 100, "min_chunk": 100},
    "legal_agreement":          {"chunk_size": 1500, "overlap": 300, "min_chunk": 200},
    "technical_study":          {"chunk_size": 1200, "overlap": 250, "min_chunk": 150},
    "business_plan":            {"chunk_size": 1000, "overlap": 200, "min_chunk": 150},
    "pitch_deck":               {"chunk_size": 800,  "overlap": 150, "min_chunk": 100},
    "environmental_assessment": {"chunk_size": 1000, "overlap": 200, "min_chunk": 150},
    "regulatory_filing":        {"chunk_size": 1200, "overlap": 250, "min_chunk": 150},
    "due_diligence_report":     {"chunk_size": 1000, "overlap": 200, "min_chunk": 150},
    "valuation_report":         {"chunk_size": 800,  "overlap": 150, "min_chunk": 100},
    "insurance_policy":         {"chunk_size": 1200, "overlap": 250, "min_chunk": 150},
    "default":                  {"chunk_size": 1000, "overlap": 200, "min_chunk": 100},
}

_SECTION_PATTERN = re.compile(
    r"(?:^#{1,4}\s+.+$|"           # Markdown headers
    r"^\d+[\.\)]\s+[A-Z].+$|"       # Numbered sections
    r"^[A-Z][A-Z\s]{10,}$)",         # ALL CAPS headers
    re.MULTILINE,
)


class Chunk:
    """A text chunk with metadata."""

    def __init__(
        self,
        text: str,
        index: int,
        section_title: str = "",
        char_start: int = 0,
        char_end: int = 0,
    ) -> None:
        self.text = text
        self.index = index
        self.section_title = section_title
        self.char_start = char_start
        self.char_end = char_end
        self.page_number: int = max(1, (char_start // 3000) + 1)
        self.summary: str = ""
        self.embedding: list[float] | None = None


class RAGPipeline:
    """Production RAG: ingest documents and query with hybrid semantic+keyword search."""

    def __init__(
        self,
        vector_store: Any,
        elasticsearch_client: Any,
        ai_gateway_client: Any,
        embedding_client: Any,
        task_batcher: Any | None = None,
    ) -> None:
        self.vectors = vector_store
        self.es = elasticsearch_client
        self.ai = ai_gateway_client
        self.embedder = embedding_client
        self.batcher = task_batcher

    # ── Ingestion ─────────────────────────────────────────────────────────────

    async def ingest_document(
        self, document_id: UUID, text: str, metadata: dict[str, Any]
    ) -> dict[str, Any]:
        """Full ingestion pipeline. Called by S5 process_document() after text extraction.

        metadata must contain: org_id, project_id, portfolio_id, document_type, filename
        """
        org_id = metadata["org_id"]
        doc_type = metadata.get("document_type", "default")
        config = CHUNK_CONFIGS.get(doc_type, CHUNK_CONFIGS["default"])

        chunks = self._semantic_chunk(text, config)
        if not chunks:
            return {"chunks_created": 0}

        await self._summarize_chunks(chunks, doc_type)

        texts_to_embed = [
            f"{c.summary}\n---\n{c.text}" if c.summary else c.text for c in chunks
        ]
        embeddings = await self.embedder.embed_batch(texts_to_embed)
        for chunk, emb in zip(chunks, embeddings):
            chunk.embedding = emb

        vectors_to_upsert = [
            {
                "id": f"{document_id}_{chunk.index}",
                "values": chunk.embedding,
                "metadata": {
                    "document_id": str(document_id),
                    "org_id": str(org_id),
                    "project_id": str(metadata.get("project_id", "")),
                    "portfolio_id": str(metadata.get("portfolio_id", "")),
                    "doc_type": doc_type,
                    "filename": metadata.get("filename", ""),
                    "section": chunk.section_title,
                    "page": chunk.page_number,
                    "chunk_index": chunk.index,
                    "summary": chunk.summary,
                    "text_preview": chunk.text[:200],
                },
            }
            for chunk in chunks
        ]
        await self.vectors.upsert(vectors=vectors_to_upsert, namespace=str(org_id))

        es_index = f"scr_rag_{org_id}"
        await self._ensure_es_index(es_index)
        for chunk in chunks:
            await self.es.index(
                index=es_index,
                id=f"{document_id}_{chunk.index}",
                document={
                    "document_id": str(document_id),
                    "project_id": str(metadata.get("project_id", "")),
                    "doc_type": doc_type,
                    "filename": metadata.get("filename", ""),
                    "section": chunk.section_title,
                    "text": chunk.text,
                    "summary": chunk.summary,
                    "page": chunk.page_number,
                    "chunk_index": chunk.index,
                },
            )

        logger.info("rag.ingested", document_id=str(document_id), chunks=len(chunks))
        return {"chunks_created": len(chunks), "doc_type": doc_type}

    async def remove_document(self, document_id: UUID, org_id: UUID) -> None:
        """Remove all chunks for a document (on delete or re-upload)."""
        try:
            await self.vectors.delete(
                filter={"document_id": str(document_id)},
                namespace=str(org_id),
            )
        except Exception as e:
            logger.warning("rag.vector_delete_failed", error=str(e))

        try:
            es_index = f"scr_rag_{org_id}"
            await self.es.delete_by_query(
                index=es_index,
                body={"query": {"term": {"document_id": str(document_id)}}},
            )
        except Exception as e:
            logger.warning("rag.es_delete_failed", error=str(e))

    # ── Query ─────────────────────────────────────────────────────────────────

    async def query(
        self,
        query: str,
        org_id: UUID,
        filters: dict[str, Any] | None = None,
        top_k: int = 5,
        rerank: bool = True,
    ) -> list[dict[str, Any]]:
        """Hybrid search: semantic + keyword with optional Haiku reranking.

        filters: project_id, doc_type, document_id (all optional)
        Returns list of {text, summary, metadata, score}
        """
        query_embedding = await self.embedder.embed(query)

        vector_filter: dict[str, Any] = {"org_id": str(org_id)}
        if filters:
            for key in ("project_id", "doc_type", "document_id"):
                if filters.get(key):
                    vector_filter[key] = str(filters[key])

        try:
            semantic_results = await self.vectors.query(
                vector=query_embedding,
                filter=vector_filter,
                namespace=str(org_id),
                top_k=top_k * 3,
                include_metadata=True,
            )
        except Exception as e:
            logger.warning("rag.vector_query_failed", error=str(e))
            semantic_results = []

        try:
            es_index = f"scr_rag_{org_id}"
            es_response = await self.es.search(
                index=es_index,
                body=self._build_es_query(query, filters),
                size=top_k * 2,
            )
            keyword_results = [
                {
                    "id": hit["_id"],
                    "text": hit["_source"]["text"],
                    "summary": hit["_source"].get("summary", ""),
                    "metadata": hit["_source"],
                    "score": hit["_score"],
                }
                for hit in es_response["hits"]["hits"]
            ]
        except Exception as e:
            logger.warning("rag.es_query_failed", error=str(e))
            keyword_results = []

        fused = self._rrf_merge(semantic_results, keyword_results)

        if rerank and len(fused) > 1:
            return await self._rerank(query, fused, top_k)
        return fused[:top_k]

    async def complete_with_context(
        self,
        query: str,
        org_id: UUID,
        system_prompt: str,
        filters: dict[str, Any] | None = None,
        top_k: int = 5,
    ) -> dict[str, Any]:
        """Full RAG completion: search → inject context → LLM answer."""
        results = await self.query(query, org_id, filters, top_k)

        context_parts = []
        sources = []
        for i, result in enumerate(results):
            meta = result.get("metadata", {})
            ref = f"[{meta.get('filename', 'doc')} p.{meta.get('page', '?')}]"
            context_parts.append(
                f"Source {i + 1} {ref}:\n{result.get('text', result.get('summary', ''))}"
            )
            sources.append({
                "document_id": meta.get("document_id"),
                "filename": meta.get("filename"),
                "page": meta.get("page"),
                "section": meta.get("section"),
                "relevance": result.get("score", 0),
            })

        context_text = (
            "\n\n---\n\n".join(context_parts)
            if context_parts
            else "No relevant documents found."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "system", "content": f"Relevant documents:\n\n{context_text}"},
            {"role": "user", "content": query},
        ]

        response = await self.ai.complete(
            model="claude-sonnet-4-20250514",
            messages=messages,
            task_type="chat_with_tools",
        )

        return {
            "response": response.get("content", ""),
            "sources": sources,
            "model": response.get("model_used", ""),
        }

    # ── Chunking ──────────────────────────────────────────────────────────────

    def _semantic_chunk(self, text: str, config: dict[str, int]) -> list[Chunk]:
        """Smart chunking that respects document section boundaries."""
        chunk_size = config["chunk_size"]
        overlap = config["overlap"]
        min_chunk = config["min_chunk"]

        sections = _SECTION_PATTERN.split(text)
        headers = _SECTION_PATTERN.findall(text)

        if len(sections) <= 1:
            sections = text.split("\n\n")
            headers = [""] * len(sections)

        chunks: list[Chunk] = []
        char_offset = 0

        for i, section_text in enumerate(sections):
            current_section = headers[i].strip() if i < len(headers) else ""
            section_text = section_text.strip()

            if len(section_text) < min_chunk:
                char_offset += len(section_text)
                continue

            if len(section_text) <= chunk_size:
                chunks.append(Chunk(
                    text=section_text,
                    index=len(chunks),
                    section_title=current_section,
                    char_start=char_offset,
                    char_end=char_offset + len(section_text),
                ))
            else:
                for sub_text in self._split_by_size(section_text, chunk_size, overlap):
                    chunks.append(Chunk(
                        text=sub_text,
                        index=len(chunks),
                        section_title=current_section,
                        char_start=char_offset,
                        char_end=char_offset + len(sub_text),
                    ))
            char_offset += len(section_text)

        return chunks

    def _split_by_size(self, text: str, chunk_size: int, overlap: int) -> list[str]:
        """Split text into size-bounded chunks at paragraph/sentence boundaries."""
        paragraphs = text.split("\n\n")
        chunks: list[str] = []
        current = ""

        for para in paragraphs:
            if len(current) + len(para) + 2 <= chunk_size:
                current = f"{current}\n\n{para}" if current else para
            else:
                if current:
                    chunks.append(current.strip())
                    current = current[-overlap:] + "\n\n" + para if overlap > 0 else para
                else:
                    sentences = re.split(r"(?<=[.!?])\s+", para)
                    for sent in sentences:
                        if len(current) + len(sent) + 1 <= chunk_size:
                            current = f"{current} {sent}" if current else sent
                        else:
                            if current:
                                chunks.append(current.strip())
                            current = sent

        if current.strip():
            chunks.append(current.strip())
        return chunks

    # ── Summarization ─────────────────────────────────────────────────────────

    async def _summarize_chunks(self, chunks: list[Chunk], doc_type: str) -> None:
        """Generate 1-2 sentence summaries per chunk via Haiku (cheap, fast)."""
        # Separate short chunks (no summarization needed) from those to summarize
        chunks_to_summarize = [c for c in chunks if len(c.text) >= 100]
        for chunk in chunks:
            if len(chunk.text) < 100:
                chunk.summary = chunk.text

        if not chunks_to_summarize:
            return

        if self.batcher:
            # Batch summarize all chunks at once
            summaries = await self.batcher.batch_complete(
                "summarize_document",
                [
                    {
                        "document_type": doc_type,
                        "document_text": chunk.text[:2000],
                        "section_title": chunk.section_title,
                    }
                    for chunk in chunks_to_summarize
                ],
            )
            for chunk, summary_result in zip(chunks_to_summarize, summaries):
                chunk.summary = summary_result.get("summary", chunk.text[:150])
        else:
            # Fallback: individual calls (original behaviour)
            for chunk in chunks_to_summarize:
                try:
                    response = await self.ai.complete(
                        model="claude-haiku-4-5-20251001",
                        messages=[{
                            "role": "user",
                            "content": (
                                f"Summarize this {doc_type} excerpt in 1-2 sentences. "
                                f"Focus on key facts, figures, entities:\n\n{chunk.text[:2000]}"
                            ),
                        }],
                        max_tokens=100,
                        temperature=0.1,
                    )
                    chunk.summary = response.get("content", "").strip()
                except Exception:
                    chunk.summary = chunk.text[:150]

    # ── Search helpers ────────────────────────────────────────────────────────

    def _build_es_query(self, query: str, filters: dict[str, Any] | None) -> dict:
        must = [{"multi_match": {
            "query": query,
            "fields": ["text^2", "summary^3", "section^1.5", "filename"],
            "type": "best_fields",
            "fuzziness": "AUTO",
        }}]
        filter_clauses = []
        if filters:
            for field, key in [("project_id", "project_id"), ("doc_type", "doc_type"), ("document_id", "document_id")]:
                if filters.get(key):
                    filter_clauses.append({"term": {field: str(filters[key])}})
        return {"query": {"bool": {"must": must, "filter": filter_clauses}}}

    def _rrf_merge(
        self,
        semantic_results: list[Any],
        keyword_results: list[dict[str, Any]],
        k: int = 60,
    ) -> list[dict[str, Any]]:
        """Reciprocal Rank Fusion: RRF score = Σ 1/(k + rank) across both lists."""
        scores: dict[str, dict[str, Any]] = defaultdict(lambda: {"score": 0.0, "data": None})

        for rank, result in enumerate(semantic_results):
            if hasattr(result, "id"):
                rid = result.id
                data = {"text": result.metadata.get("text_preview", ""), "summary": result.metadata.get("summary", ""), "metadata": dict(result.metadata)}
            else:
                rid = result.get("id", str(rank))
                data = result
            scores[rid]["score"] += 1 / (k + rank + 1)
            if scores[rid]["data"] is None:
                scores[rid]["data"] = data

        for rank, result in enumerate(keyword_results):
            rid = result.get("id", str(rank))
            scores[rid]["score"] += 1 / (k + rank + 1)
            if scores[rid]["data"] is None:
                scores[rid]["data"] = result

        merged = []
        for rid, info in sorted(scores.items(), key=lambda x: -x[1]["score"]):
            item = (info["data"] or {}).copy()
            item["score"] = round(info["score"], 4)
            item["id"] = rid
            merged.append(item)
        return merged

    async def _rerank(
        self,
        query: str,
        candidates: list[dict[str, Any]],
        top_k: int,
    ) -> list[dict[str, Any]]:
        """Rerank candidates using Haiku relevance scoring."""
        if len(candidates) <= 1:
            return candidates

        candidate_texts = []
        for i, c in enumerate(candidates[:15]):
            preview = (c.get("text") or c.get("summary") or "")[:300]
            candidate_texts.append(f"[{i}] {preview}")

        prompt = (
            f"Query: {query}\n\n"
            f"Rate each result 0-10 (0=irrelevant, 10=perfect match).\n"
            f"Respond with ONLY a JSON array of scores, e.g. [8, 3, 9, ...].\n\n"
            + "\n".join(candidate_texts)
        )

        try:
            response = await self.ai.complete(
                model="claude-haiku-4-5-20251001",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.0,
            )
            content = response.get("content", "").strip()
            match = re.search(r"\[[\d,\s\.]+\]", content)
            if not match:
                return candidates[:top_k]
            relevance_scores = json.loads(match.group())
            scored = sorted(
                zip(candidates[: len(relevance_scores)], relevance_scores),
                key=lambda x: -x[1],
            )
            return [item for item, score in scored[:top_k] if score > 2]
        except Exception:
            return candidates[:top_k]

    async def _ensure_es_index(self, index_name: str) -> None:
        try:
            exists = await self.es.indices.exists(index=index_name)
            if not exists:
                await self.es.indices.create(
                    index=index_name,
                    body={
                        "mappings": {
                            "properties": {
                                "document_id": {"type": "keyword"},
                                "project_id": {"type": "keyword"},
                                "doc_type": {"type": "keyword"},
                                "filename": {"type": "text"},
                                "section": {"type": "text"},
                                "text": {"type": "text", "analyzer": "standard"},
                                "summary": {"type": "text", "analyzer": "standard"},
                                "page": {"type": "integer"},
                                "chunk_index": {"type": "integer"},
                            }
                        },
                        "settings": {"number_of_shards": 1, "number_of_replicas": 0},
                    },
                )
        except Exception as e:
            logger.warning("rag.ensure_index_failed", index=index_name, error=str(e))
