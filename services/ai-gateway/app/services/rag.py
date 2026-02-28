"""RAG pipeline — chunk, embed, store, retrieve, augment, complete."""
from __future__ import annotations

import hashlib
import uuid
from typing import Any

import structlog

from app.services.vector_store import vector_store

logger = structlog.get_logger()

# Chunk size for document splitting
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150


def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks."""
    words = text.split()
    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        if end == len(words):
            break
        start += chunk_size - overlap
    return chunks


async def _embed_text(text: str) -> list[float]:
    """Generate embeddings via litellm."""
    try:
        import litellm
        from app.core.config import settings

        response = await litellm.aembedding(
            model=settings.AI_EMBEDDING_MODEL,
            input=[text],
            api_key=settings.OPENAI_API_KEY,
        )
        return response.data[0]["embedding"]
    except Exception as e:
        logger.warning("embedding_failed", error=str(e))
        # Return a stub vector for dev — real production needs embeddings
        import hashlib
        seed = int(hashlib.md5(text.encode()).hexdigest(), 16) % 2**31
        import random
        rng = random.Random(seed)
        return [rng.gauss(0, 1) for _ in range(1536)]  # text-embedding-3-large dim


class RAGPipeline:
    """Retrieval-Augmented Generation pipeline."""

    def __init__(self) -> None:
        self._vs = vector_store()

    def _org_namespace(self, org_id: str, index_type: str = "document_chunks") -> str:
        """Namespaced per org for tenant isolation: org_{id}_{type}."""
        return f"org_{org_id}_{index_type}"

    async def ingest_document(
        self,
        document_id: str,
        text: str,
        org_id: str,
        metadata: dict[str, Any] | None = None,
        index_type: str = "document_chunks",
    ) -> int:
        """Chunk text, embed each chunk, store in vector DB. Returns chunk count."""
        namespace = self._org_namespace(org_id, index_type)
        chunks = _chunk_text(text)
        meta_base = metadata or {}

        ingested = 0
        for i, chunk in enumerate(chunks):
            chunk_id = f"{document_id}_chunk_{i}"
            try:
                vector = await _embed_text(chunk)
                self._vs.upsert(
                    namespace=namespace,
                    doc_id=chunk_id,
                    vector=vector,
                    metadata={
                        **meta_base,
                        "document_id": document_id,
                        "chunk_index": i,
                        "chunk_total": len(chunks),
                        "text": chunk[:500],  # Store first 500 chars for display
                        "org_id": org_id,
                    },
                )
                ingested += 1
            except Exception as e:
                logger.error("chunk_ingest_failed", chunk_id=chunk_id, error=str(e))

        logger.info("document_ingested", document_id=document_id, chunks=ingested, org_id=org_id)
        return ingested

    async def query(
        self,
        query: str,
        org_id: str,
        index_type: str = "document_chunks",
        filters: dict | None = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Search for relevant context. Returns list of {text, score, metadata}."""
        namespace = self._org_namespace(org_id, index_type)
        try:
            query_vector = await _embed_text(query)
            matches = self._vs.query(namespace=namespace, query_vector=query_vector, top_k=top_k, filters=filters)
            return [
                {
                    "text": m.metadata.get("text", ""),
                    "score": m.score,
                    "document_id": m.metadata.get("document_id"),
                    "chunk_index": m.metadata.get("chunk_index"),
                    "metadata": m.metadata,
                }
                for m in matches
            ]
        except Exception as e:
            logger.error("rag_query_failed", error=str(e))
            return []

    async def complete_with_context(
        self,
        query: str,
        org_id: str,
        system_prompt: str,
        index_type: str = "document_chunks",
        filters: dict | None = None,
        top_k: int = 5,
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        """RAG completion: search → inject context → complete."""
        from app.services.llm_router import route_completion
        from app.core.config import settings as cfg

        # 1. Retrieve relevant context
        results = await self.query(query=query, org_id=org_id, index_type=index_type, filters=filters, top_k=top_k)
        context_text = "\n\n---\n\n".join(
            f"[Source: {r['metadata'].get('document_id', 'unknown')}]\n{r['text']}"
            for r in results
        )

        # 2. Build augmented prompt
        augmented_system = f"{system_prompt}\n\n## Retrieved Context\n\n{context_text}" if context_text else system_prompt
        messages = [
            {"role": "system", "content": augmented_system},
            {"role": "user", "content": query},
        ]

        # 3. Complete
        result = await route_completion(
            model=model or cfg.AI_DEFAULT_MODEL,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return {
            **result,
            "context_chunks": len(results),
            "context_sources": list({r["metadata"].get("document_id") for r in results}),
        }


_rag: RAGPipeline | None = None


def get_rag() -> RAGPipeline:
    global _rag
    if _rag is None:
        _rag = RAGPipeline()
    return _rag
