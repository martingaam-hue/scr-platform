"""Service layer for the AI Document Redaction module."""

from __future__ import annotations

import json
import uuid

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.redaction import RedactionJob
from app.modules.redaction.schemas import ENTITY_TYPES, HIGH_SENSITIVITY

logger = structlog.get_logger()


class RedactionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Job lifecycle ─────────────────────────────────────────────────────────

    async def create_job(
        self,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        document_id: uuid.UUID,
    ) -> RedactionJob:
        """Create a new redaction job in `pending` state."""
        job = RedactionJob(
            org_id=org_id,
            created_by=user_id,
            document_id=document_id,
            status="pending",
        )
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def analyze_document(
        self,
        job_id: uuid.UUID,
        document_text: str,
    ) -> RedactionJob | None:
        """Call AI Gateway to detect PII entities in *document_text*.

        Transitions: pending → analyzing → review | failed
        """
        job = await self.get_job_by_id(job_id)
        if not job:
            logger.warning("redaction.analyze.job_not_found", job_id=str(job_id))
            return None

        job.status = "analyzing"
        await self.db.commit()

        prompt = (
            "Analyze this document and identify all PII (Personally Identifiable "
            "Information) and sensitive data entities.\n\n"
            f"Document text:\n{document_text[:8000]}\n\n"
            "For each entity found, return a JSON array with objects containing:\n"
            f"- entity_type: one of {ENTITY_TYPES}\n"
            "- text: the exact text found\n"
            "- page: page number (default 1 if unknown)\n"
            "- confidence: 0.0-1.0 confidence score\n"
            "- position: {x: 0, y: 0, width: 10, height: 2} "
            "(approximate normalised percentages)\n\n"
            "Return ONLY a JSON array. If no entities found, return []."
        )

        try:
            resp = httpx.post(
                f"{settings.AI_GATEWAY_URL}/completions",
                json={
                    "prompt": prompt,
                    "task_type": "document_redaction",
                    "max_tokens": 2000,
                },
                headers={"Authorization": f"Bearer {settings.AI_GATEWAY_API_KEY}"},
                timeout=60.0,
            )
            if resp.status_code == 200:
                content = resp.json().get("content", resp.json().get("text", "[]"))
                try:
                    start = content.find("[")
                    end = content.rfind("]") + 1
                    entities_raw: list[dict] = (
                        json.loads(content[start:end]) if start >= 0 else []
                    )
                except Exception:
                    entities_raw = []

                entities: list[dict] = []
                for i, e in enumerate(entities_raw):
                    e["id"] = i
                    e["is_high_sensitivity"] = (
                        e.get("entity_type", "") in HIGH_SENSITIVITY
                    )
                    entities.append(e)

                job.detected_entities = entities
                job.entity_count = len(entities)
                job.status = "review"
                logger.info(
                    "redaction.analyze.done",
                    job_id=str(job_id),
                    entity_count=len(entities),
                )
            else:
                job.status = "failed"
                job.error_message = f"AI gateway returned {resp.status_code}"
                logger.error(
                    "redaction.analyze.gateway_error",
                    job_id=str(job_id),
                    status_code=resp.status_code,
                )
        except Exception as exc:
            job.status = "failed"
            job.error_message = str(exc)[:500]
            logger.error(
                "redaction.analyze.exception",
                job_id=str(job_id),
                error=str(exc),
            )

        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def approve_redactions(
        self,
        org_id: uuid.UUID,
        job_id: uuid.UUID,
        approved_ids: list[int],
    ) -> RedactionJob | None:
        """Record the user's selection of which entities to redact.

        Transitions: review → applying
        """
        job = await self.get_job(org_id, job_id)
        if not job or job.status != "review":
            return None

        entities: list[dict] = job.detected_entities or []
        approved = [e for e in entities if e.get("id") in approved_ids]
        job.approved_redactions = approved
        job.approved_count = len(approved)
        job.status = "applying"
        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def generate_redacted_document(
        self,
        job_id: uuid.UUID,
    ) -> RedactionJob | None:
        """Produce a redacted copy of the document.

        In production this would use PyMuPDF/fitz to paint redaction boxes
        over the approved entity positions and upload the result to S3.
        For now we store a placeholder S3 key and mark the job done.

        Transitions: applying → done | failed
        """
        job = await self.get_job_by_id(job_id)
        if not job:
            return None

        try:
            # Real implementation: fetch PDF from S3, apply fitz redaction, re-upload.
            job.redacted_s3_key = (
                f"redacted/{job.org_id}/{job.document_id}/redacted_{job.id}.pdf"
            )
            job.status = "done"
            logger.info("redaction.apply.done", job_id=str(job_id))
        except Exception as exc:
            job.status = "failed"
            job.error_message = str(exc)[:500]
            logger.error(
                "redaction.apply.exception", job_id=str(job_id), error=str(exc)
            )

        await self.db.commit()
        await self.db.refresh(job)
        return job

    # ── Queries ───────────────────────────────────────────────────────────────

    async def get_job(
        self,
        org_id: uuid.UUID,
        job_id: uuid.UUID,
    ) -> RedactionJob | None:
        stmt = select(RedactionJob).where(
            RedactionJob.id == job_id,
            RedactionJob.org_id == org_id,
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_job_by_id(self, job_id: uuid.UUID) -> RedactionJob | None:
        stmt = select(RedactionJob).where(RedactionJob.id == job_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list_jobs(
        self,
        org_id: uuid.UUID,
        document_id: uuid.UUID | None = None,
    ) -> list[RedactionJob]:
        stmt = select(RedactionJob).where(RedactionJob.org_id == org_id)
        if document_id:
            stmt = stmt.where(RedactionJob.document_id == document_id)
        stmt = stmt.order_by(RedactionJob.created_at.desc())
        return list((await self.db.execute(stmt)).scalars().all())
