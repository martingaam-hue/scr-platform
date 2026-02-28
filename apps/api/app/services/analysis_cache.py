"""Document Analysis Cache — eliminates redundant AI calls across modules.

Instead of each module calling the AI gateway directly for document analysis,
they call the cache. The cache returns an existing extraction or runs the
analysis once and stores it in document_extractions for all modules.

Usage from any module:
    from app.services.analysis_cache import DocumentAnalysisCache

    cache = DocumentAnalysisCache(db, ai_gateway_client)
    result = await cache.get_or_analyze(
        document_id=doc.id,
        analysis_type="quality_assessment",
        context={"criterion": "financial_planning", "project_type": "solar"},
    )
    # result["cached"] == True if a valid extraction existed
"""

from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime
from typing import Any
from uuid import UUID

import httpx
import structlog
from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dataroom import Document, DocumentExtraction
from app.models.enums import DocumentStatus

logger = structlog.get_logger()


class AsyncGatewayClient:
    """Async AI Gateway adapter satisfying DocumentAnalysisCache._ai interface."""

    def __init__(self, gateway_url: str, gateway_key: str) -> None:
        self._url = gateway_url
        self._key = gateway_key

    async def complete(self, task_type: str, context: dict[str, Any]) -> dict[str, Any]:
        """Call gateway and return normalised result dict."""
        doc_text = context.get("document_text", "")
        doc_name = context.get("document_name", "document")
        prompt = (
            f"Analyse the following document ({doc_name}) for task '{task_type}'.\n\n"
            f"Document content:\n{doc_text[:12_000]}\n\n"
            f"Additional context: {json.dumps({k: v for k, v in context.items() if k not in ('document_text', 'document_name', 'document_type')})}\n\n"
            f"Respond with a JSON object summarising your findings."
        )
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{self._url}/v1/completions",
                    json={"prompt": prompt, "task_type": task_type, "max_tokens": 800, "temperature": 0.3},
                    headers={"Authorization": f"Bearer {self._key}"},
                )
                resp.raise_for_status()
                data = resp.json()
                content = data.get("content", "")
                # Try to parse JSON out of the response
                validated: dict[str, Any] | None = None
                match = re.search(r"\{.*\}", content, re.DOTALL)
                if match:
                    try:
                        validated = json.loads(match.group())
                    except Exception:
                        pass
                return {
                    "content": content,
                    "validated_data": validated,
                    "confidence": 0.75,
                    "model_used": data.get("model_used", "claude"),
                    "usage": data.get("usage", {}),
                }
        except Exception as exc:
            logger.warning("async_gateway_client_failed", task_type=task_type, error=str(exc))
            return {
                "content": "",
                "validated_data": None,
                "confidence": 0.0,
                "model_used": "unavailable",
                "usage": {},
            }


def make_analysis_cache(db: AsyncSession) -> "DocumentAnalysisCache":
    """Factory: builds a ready-to-use cache with the async gateway client."""
    from app.core.config import settings
    client = AsyncGatewayClient(
        gateway_url=settings.AI_GATEWAY_URL or "",
        gateway_key=settings.AI_GATEWAY_API_KEY or "",
    )
    return DocumentAnalysisCache(db, client)

# Maps cross-module analysis_type → AI Gateway task_type
ANALYSIS_TASK_MAPPING: dict[str, str] = {
    "quality_assessment": "score_quality",
    "risk_flags": "assess_risk",
    "deal_relevance": "score_deal_readiness",
    "completeness_check": "classify_document",
    "key_figures": "extract_kpis",
    "entity_extraction": "extract_kpis",
    # Original S5 types — included for completeness
    "kpi": "extract_kpis",
    "clause": "extract_clauses",
    "summary": "summarize_document",
    "classification": "classify_document",
}

# Cross-module types that the cache manages (not S5 originals)
CROSS_MODULE_TYPES = {
    "quality_assessment", "risk_flags", "deal_relevance",
    "completeness_check", "key_figures", "entity_extraction",
}


class DocumentAnalysisCache:
    """
    Cross-module AI analysis cache backed by document_extractions table.

    Cache key:   (document_id, extraction_type)
    Valid when:  created_at >= document.updated_at AND confidence_score > 0
    Invalidated: on document re-upload or explicit .invalidate() call
    """

    def __init__(self, db: AsyncSession, ai_gateway_client: Any) -> None:
        self._db = db
        self._ai = ai_gateway_client

    async def get_or_analyze(
        self,
        document_id: UUID,
        analysis_type: str,
        context: dict[str, Any],
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        """Get cached analysis or run a new one.

        Returns:
            {
                "result": dict,          # The parsed AI output
                "confidence": float,     # Validation confidence from S33
                "cached": bool,          # True = cache hit, False = fresh analysis
                "analyzed_at": str,      # ISO timestamp
                "model_used": str | None,
            }
        """
        if not force_refresh:
            cached = await self._get_cached(document_id, analysis_type)
            if cached:
                logger.debug("analysis_cache.hit", document_id=str(document_id), analysis_type=analysis_type)
                return {
                    "result": cached.result,
                    "confidence": cached.confidence_score,
                    "cached": True,
                    "analyzed_at": cached.created_at.isoformat(),
                    "model_used": cached.model_used,
                }

        logger.info("analysis_cache.miss", document_id=str(document_id), analysis_type=analysis_type)
        result = await self._run_analysis(document_id, analysis_type, context)
        await self._store(document_id, analysis_type, result)

        return {
            "result": result.get("validated_data") or {"raw": result.get("content", "")},
            "confidence": result.get("confidence", 0.5),
            "cached": False,
            "analyzed_at": datetime.utcnow().isoformat(),
            "model_used": result.get("model_used"),
        }

    async def get_all_analyses(self, document_id: UUID) -> dict[str, dict[str, Any]]:
        """Get ALL valid cached analyses for a document, keyed by extraction_type."""
        result = await self._db.execute(
            select(DocumentExtraction)
            .where(DocumentExtraction.document_id == document_id)
            .where(DocumentExtraction.confidence_score > 0)
            .order_by(DocumentExtraction.created_at.desc())
        )
        extractions = result.scalars().all()

        by_type: dict[str, dict[str, Any]] = {}
        for ext in extractions:
            et = ext.extraction_type.value if hasattr(ext.extraction_type, "value") else str(ext.extraction_type)
            if et not in by_type:
                by_type[et] = {
                    "result": ext.result,
                    "confidence": ext.confidence_score,
                    "analyzed_at": ext.created_at.isoformat(),
                    "model_used": ext.model_used,
                }
        return by_type

    async def batch_analyze(
        self,
        document_ids: list[UUID],
        analysis_type: str,
        shared_context: dict[str, Any],
    ) -> dict[str, dict[str, Any]]:
        """Analyze multiple documents. Uses cache where available."""
        results: dict[str, dict[str, Any]] = {}
        to_analyze: list[UUID] = []

        for doc_id in document_ids:
            cached = await self._get_cached(doc_id, analysis_type)
            if cached:
                results[str(doc_id)] = {
                    "result": cached.result,
                    "confidence": cached.confidence_score,
                    "cached": True,
                    "analyzed_at": cached.created_at.isoformat(),
                    "model_used": cached.model_used,
                }
            else:
                to_analyze.append(doc_id)

        if to_analyze:
            tasks = [
                self.get_or_analyze(doc_id, analysis_type, shared_context)
                for doc_id in to_analyze
            ]
            analyzed = await asyncio.gather(*tasks, return_exceptions=True)
            for doc_id, result in zip(to_analyze, analyzed):
                if isinstance(result, Exception):
                    logger.warning("batch_analyze.error", document_id=str(doc_id), error=str(result))
                    results[str(doc_id)] = {"result": None, "confidence": 0, "cached": False, "error": str(result)}
                else:
                    results[str(doc_id)] = result  # type: ignore[assignment]

        return results

    async def invalidate(self, document_id: UUID) -> None:
        """Invalidate all cross-module cached analyses for a document.

        Sets confidence_score=0 rather than deleting to preserve history.
        Does NOT invalidate S5's original extractions (kpi, clause, summary).
        """
        await self._db.execute(
            update(DocumentExtraction)
            .where(DocumentExtraction.document_id == document_id)
            .where(DocumentExtraction.extraction_type.in_(list(CROSS_MODULE_TYPES)))
            .values(confidence_score=0.0)
        )
        await self._db.commit()
        logger.info("analysis_cache.invalidated", document_id=str(document_id))

    async def get_cache_stats(self) -> dict[str, Any]:
        """Cache statistics for the admin dashboard."""
        from sqlalchemy import func, case

        result = await self._db.execute(
            select(
                func.count(DocumentExtraction.id).label("total_cached"),
                func.count(
                    case((DocumentExtraction.confidence_score > 0, 1))
                ).label("valid_cached"),
                func.coalesce(func.sum(DocumentExtraction.tokens_used), 0).label("total_tokens"),
            ).where(
                DocumentExtraction.extraction_type.in_(list(CROSS_MODULE_TYPES))
            )
        )
        row = result.one()
        estimated_savings = float(row.valid_cached or 0) * 0.02  # ~$0.02 per Sonnet call

        return {
            "total_cached_analyses": row.total_cached or 0,
            "valid_cached": row.valid_cached or 0,
            "total_tokens_used": row.total_tokens or 0,
            "estimated_cost_saved_usd": round(estimated_savings, 2),
        }

    # ── Private ───────────────────────────────────────────────────────────────

    async def _get_cached(self, document_id: UUID, analysis_type: str) -> DocumentExtraction | None:
        doc_result = await self._db.execute(
            select(Document.updated_at).where(Document.id == document_id)
        )
        doc_updated = doc_result.scalar_one_or_none()
        if not doc_updated:
            return None

        result = await self._db.execute(
            select(DocumentExtraction)
            .where(and_(
                DocumentExtraction.document_id == document_id,
                DocumentExtraction.extraction_type == analysis_type,
                DocumentExtraction.confidence_score > 0,
                DocumentExtraction.created_at >= doc_updated,
            ))
            .order_by(DocumentExtraction.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _run_analysis(
        self, document_id: UUID, analysis_type: str, context: dict[str, Any]
    ) -> dict[str, Any]:
        doc_result = await self._db.execute(
            select(Document).where(Document.id == document_id)
        )
        document = doc_result.scalar_one()
        doc_text = await self._get_document_text(document)

        task_type = ANALYSIS_TASK_MAPPING.get(analysis_type, analysis_type)
        full_context = {
            "document_text": doc_text[:15_000],
            "document_name": document.name,
            "document_type": document.file_type or "unknown",
            **context,
        }

        return await self._ai.complete(task_type=task_type, context=full_context)

    async def _store(self, document_id: UUID, analysis_type: str, result: dict[str, Any]) -> None:
        extraction = DocumentExtraction(
            document_id=document_id,
            extraction_type=analysis_type,
            result=result.get("validated_data") or {"raw": result.get("content", "")},
            model_used=result.get("model_used", "unknown"),
            confidence_score=result.get("confidence", 0.5),
            tokens_used=(
                result.get("usage", {}).get("prompt_tokens", 0)
                + result.get("usage", {}).get("completion_tokens", 0)
            ),
            processing_time_ms=0,
        )
        self._db.add(extraction)
        await self._db.commit()

    async def _get_document_text(self, document: Document) -> str:
        # Check for existing summary extraction
        result = await self._db.execute(
            select(DocumentExtraction.result)
            .where(and_(
                DocumentExtraction.document_id == document.id,
                DocumentExtraction.extraction_type == "summary",
            ))
            .order_by(DocumentExtraction.created_at.desc())
            .limit(1)
        )
        summary_result = result.scalar_one_or_none()
        if summary_result and isinstance(summary_result, dict):
            return summary_result.get("text") or summary_result.get("summary", "")

        # Fall back to metadata extracted_text if present
        if document.metadata_ and isinstance(document.metadata_, dict):
            return document.metadata_.get("extracted_text", "")

        return ""
