"""CitationService — extracts and resolves [SOURCE:] tags from AI outputs."""

import re
import uuid
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.citations import AICitation

logger = structlog.get_logger()

_SOURCE_PATTERN = re.compile(r'\[SOURCE:\s*([^\]]+)\]')
_CONTEXT_CHARS = 200  # chars before [SOURCE:] tag to extract as claim text


class CitationService:
    def __init__(self, db: AsyncSession, org_id: uuid.UUID):
        self.db = db
        self.org_id = org_id

    CITATION_INSTRUCTION = """
IMPORTANT: For every factual claim, financial figure, or specific assertion in your response, include a source reference in this exact format: [SOURCE: document_name | section/page | data_point]

If a claim comes from computed data (e.g., platform metrics), use: [SOURCE: METRIC: metric_name]
If a claim is your analytical inference (not directly from a source), use: [SOURCE: AI_INFERENCE]

Every number, date, and specific fact MUST have a [SOURCE:] tag.
"""

    async def extract_citations_from_output(
        self,
        ai_task_log_id: uuid.UUID,
        ai_output: str,
    ) -> list[AICitation]:
        """Parse [SOURCE:] tags from AI output, resolve to DB records, store as AICitation."""
        matches = list(_SOURCE_PATTERN.finditer(ai_output))
        citations = []
        for i, match in enumerate(matches):
            source_ref = match.group(1).strip()
            resolved = await self._resolve_source(source_ref)
            # Extract claim text: text before this [SOURCE:] tag
            start = max(0, match.start() - _CONTEXT_CHARS)
            claim_text = ai_output[start:match.start()].strip()
            # Remove prior [SOURCE:] tags from claim_text
            claim_text = _SOURCE_PATTERN.sub("", claim_text).strip()[-_CONTEXT_CHARS:]

            citation = AICitation(
                org_id=self.org_id,
                ai_task_log_id=ai_task_log_id,
                claim_text=claim_text or source_ref,
                claim_index=i,
                **resolved,
            )
            self.db.add(citation)
            citations.append(citation)

        if citations:
            await self.db.flush()
            logger.info(
                "citations_extracted",
                task_log_id=str(ai_task_log_id),
                count=len(citations),
            )
        return citations

    async def _resolve_source(self, source_ref: str) -> dict[str, Any]:
        """Match a source reference string to actual database records."""
        if source_ref.startswith("METRIC:"):
            metric_name = source_ref.replace("METRIC:", "").strip()
            return {
                "source_type": "metric_snapshot",
                "document_name": metric_name,
                "confidence": 0.95,
            }
        if source_ref.startswith("AI_INFERENCE"):
            return {
                "source_type": "ai_inference",
                "confidence": 0.7,
            }
        # Try to match document name
        parts = [p.strip() for p in source_ref.split("|")]
        doc_name = parts[0] if parts else source_ref
        page_section = parts[1] if len(parts) > 1 else None

        try:
            from app.models.dataroom import Document
            doc_result = await self.db.execute(
                select(Document)
                .where(
                    Document.org_id == self.org_id,
                    Document.name.ilike(f"%{doc_name[:50]}%"),
                    Document.is_deleted.is_(False),
                )
                .limit(1)
            )
            document = doc_result.scalar_one_or_none()
        except Exception:
            document = None

        return {
            "source_type": "document" if document else "unknown",
            "document_id": document.id if document else None,
            "document_name": doc_name,
            "page_or_section": page_section,
            "confidence": 0.9 if document else 0.5,
        }

    @staticmethod
    def strip_citation_tags(text: str) -> str:
        """Remove [SOURCE:] tags from user-facing text."""
        return _SOURCE_PATTERN.sub("", text).strip()

    async def get_citations_for_output(
        self, ai_task_log_id: uuid.UUID
    ) -> list[AICitation]:
        """Get all citations for an AI output."""
        result = await self.db.execute(
            select(AICitation)
            .where(AICitation.ai_task_log_id == ai_task_log_id)
            .order_by(AICitation.claim_index)
        )
        return list(result.scalars().all())

    async def verify_citation(
        self, citation_id: uuid.UUID, user_id: uuid.UUID, is_correct: bool
    ) -> AICitation:
        """Human verification of a citation's accuracy."""
        citation = await self.db.get(AICitation, citation_id)
        if not citation or citation.org_id != self.org_id:
            raise LookupError(f"Citation {citation_id} not found")
        citation.verified = True
        citation.verified_by = user_id
        if not is_correct:
            citation.confidence = 0.0
        await self.db.flush()
        return citation

    async def get_stats(self) -> dict[str, Any]:
        """Citation accuracy stats."""
        from sqlalchemy import func
        total = (await self.db.execute(
            select(func.count()).where(AICitation.org_id == self.org_id)
        )).scalar() or 0
        verified = (await self.db.execute(
            select(func.count()).where(
                AICitation.org_id == self.org_id,
                AICitation.verified.is_(True),
            )
        )).scalar() or 0
        avg_confidence = (await self.db.execute(
            select(func.avg(AICitation.confidence))
            .where(AICitation.org_id == self.org_id)
        )).scalar()
        return {
            "total_citations": total,
            "verified": verified,
            "verification_rate": round(verified / total, 3) if total else 0.0,
            "avg_confidence": round(float(avg_confidence), 3) if avg_confidence else None,
        }
