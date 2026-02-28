"""Semantic search and RAG endpoints."""
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.services.auth import verify_gateway_key
from app.services.rag import get_rag

logger = structlog.get_logger()
router = APIRouter()


class IngestRequest(BaseModel):
    document_id: str
    text: str
    org_id: str
    metadata: dict[str, Any] | None = None
    index_type: str = "document_chunks"


class IngestResponse(BaseModel):
    document_id: str
    chunks_stored: int


class SearchRequest(BaseModel):
    query: str
    org_id: str
    index_type: str = "document_chunks"
    filters: dict[str, Any] | None = None
    top_k: int = Field(default=5, ge=1, le=20)


class SearchResult(BaseModel):
    text: str
    score: float
    document_id: str | None
    chunk_index: int | None
    metadata: dict[str, Any]


class SearchResponse(BaseModel):
    results: list[SearchResult]
    total: int


class RAGRequest(BaseModel):
    query: str
    org_id: str
    system_prompt: str = "You are a helpful assistant. Answer based on the provided context."
    index_type: str = "document_chunks"
    filters: dict[str, Any] | None = None
    top_k: int = 5
    model: str | None = None
    temperature: float = 0.3
    max_tokens: int = 4096


class RAGResponse(BaseModel):
    content: str
    model_used: str
    context_chunks: int
    context_sources: list[str]
    usage: dict[str, int]


@router.post("/ingest", response_model=IngestResponse)
async def ingest_document(
    request: IngestRequest,
    _api_key: str = Depends(verify_gateway_key),
) -> IngestResponse:
    """Chunk, embed, and store a document in the vector store."""
    rag = get_rag()
    try:
        chunks = await rag.ingest_document(
            document_id=request.document_id,
            text=request.text,
            org_id=request.org_id,
            metadata=request.metadata,
            index_type=request.index_type,
        )
        return IngestResponse(document_id=request.document_id, chunks_stored=chunks)
    except Exception as e:
        logger.error("ingest_failed", document_id=request.document_id, error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e


@router.post("/search", response_model=SearchResponse)
async def semantic_search(
    request: SearchRequest,
    _api_key: str = Depends(verify_gateway_key),
) -> SearchResponse:
    """Search the vector store for relevant context chunks."""
    rag = get_rag()
    results = await rag.query(
        query=request.query,
        org_id=request.org_id,
        index_type=request.index_type,
        filters=request.filters,
        top_k=request.top_k,
    )
    search_results = [
        SearchResult(
            text=r["text"],
            score=r["score"],
            document_id=r.get("document_id"),
            chunk_index=r.get("chunk_index"),
            metadata=r["metadata"],
        )
        for r in results
    ]
    return SearchResponse(results=search_results, total=len(search_results))


@router.post("/rag", response_model=RAGResponse)
async def rag_complete(
    request: RAGRequest,
    _api_key: str = Depends(verify_gateway_key),
) -> RAGResponse:
    """RAG completion: search for context → augment prompt → complete."""
    rag = get_rag()
    try:
        result = await rag.complete_with_context(
            query=request.query,
            org_id=request.org_id,
            system_prompt=request.system_prompt,
            index_type=request.index_type,
            filters=request.filters,
            top_k=request.top_k,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
        usage = result.get("usage", {})
        return RAGResponse(
            content=result["content"],
            model_used=result.get("model_used", "unknown"),
            context_chunks=result.get("context_chunks", 0),
            context_sources=result.get("context_sources", []),
            usage=usage,
        )
    except Exception as e:
        logger.error("rag_failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e
