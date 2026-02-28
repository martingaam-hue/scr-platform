"""Vector store interface — Pinecone or in-memory fallback for dev."""
from __future__ import annotations

import hashlib
import uuid
from typing import Any

import structlog

from app.core.config import settings

logger = structlog.get_logger()


class VectorMatch:
    def __init__(self, id: str, score: float, metadata: dict[str, Any]) -> None:
        self.id = id
        self.score = score
        self.metadata = metadata


class InMemoryVectorStore:
    """Simple in-memory cosine-similarity store for development."""

    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {}

    def _namespace_key(self, namespace: str, doc_id: str) -> str:
        return f"{namespace}::{doc_id}"

    def upsert(self, namespace: str, doc_id: str, vector: list[float], metadata: dict[str, Any]) -> None:
        key = self._namespace_key(namespace, doc_id)
        self._store[key] = {"id": doc_id, "vector": vector, "metadata": metadata, "namespace": namespace}

    def query(
        self, namespace: str, query_vector: list[float], top_k: int = 5, filters: dict | None = None
    ) -> list[VectorMatch]:
        """Return top_k matches by cosine similarity within namespace."""
        import math

        def cosine_sim(a: list[float], b: list[float]) -> float:
            dot = sum(x * y for x, y in zip(a, b))
            mag_a = math.sqrt(sum(x * x for x in a))
            mag_b = math.sqrt(sum(x * x for x in b))
            if mag_a == 0 or mag_b == 0:
                return 0.0
            return dot / (mag_a * mag_b)

        candidates = [v for k, v in self._store.items() if v["namespace"] == namespace]
        if filters:
            for fk, fv in filters.items():
                candidates = [c for c in candidates if c["metadata"].get(fk) == fv]

        scored = [(cosine_sim(query_vector, c["vector"]), c) for c in candidates]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [VectorMatch(id=c["id"], score=s, metadata=c["metadata"]) for s, c in scored[:top_k]]

    def delete(self, namespace: str, doc_id: str) -> None:
        key = self._namespace_key(namespace, doc_id)
        self._store.pop(key, None)


class PineconeVectorStore:
    """Pinecone-backed vector store for production."""

    def __init__(self) -> None:
        try:
            from pinecone import Pinecone  # type: ignore[import]
            pc = Pinecone(api_key=settings.PINECONE_API_KEY)
            self._index = pc.Index(settings.PINECONE_INDEX_NAME)
            logger.info("pinecone_connected", index=settings.PINECONE_INDEX_NAME)
        except Exception as e:
            logger.error("pinecone_init_failed", error=str(e))
            raise

    def upsert(self, namespace: str, doc_id: str, vector: list[float], metadata: dict[str, Any]) -> None:
        self._index.upsert(vectors=[{"id": doc_id, "values": vector, "metadata": metadata}], namespace=namespace)

    def query(
        self, namespace: str, query_vector: list[float], top_k: int = 5, filters: dict | None = None
    ) -> list[VectorMatch]:
        kwargs: dict[str, Any] = {"vector": query_vector, "top_k": top_k, "namespace": namespace, "include_metadata": True}
        if filters:
            kwargs["filter"] = filters
        results = self._index.query(**kwargs)
        return [
            VectorMatch(id=m["id"], score=m["score"], metadata=m.get("metadata", {}))
            for m in results.get("matches", [])
        ]

    def delete(self, namespace: str, doc_id: str) -> None:
        self._index.delete(ids=[doc_id], namespace=namespace)


def get_vector_store() -> InMemoryVectorStore | PineconeVectorStore:
    """Factory: returns Pinecone in production, in-memory in dev."""
    if settings.VECTOR_STORE_BACKEND == "pinecone" and settings.PINECONE_API_KEY:
        try:
            return PineconeVectorStore()
        except Exception:
            logger.warning("pinecone_unavailable_using_memory")
    return InMemoryVectorStore()


# Singleton
_vector_store: InMemoryVectorStore | PineconeVectorStore | None = None


def vector_store() -> InMemoryVectorStore | PineconeVectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = get_vector_store()
    return _vector_store
