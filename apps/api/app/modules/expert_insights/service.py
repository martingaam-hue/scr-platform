"""Expert Insights service — CRUD + AI enrichment."""

from __future__ import annotations

import json
import uuid

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.expert_notes import ExpertNote
from app.modules.expert_insights.schemas import (
    CreateExpertNoteRequest,
    UpdateExpertNoteRequest,
)

logger = structlog.get_logger()


class ExpertInsightsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Create ────────────────────────────────────────────────────────────

    async def create_note(
        self,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        data: CreateExpertNoteRequest,
    ) -> ExpertNote:
        note = ExpertNote(
            org_id=org_id,
            project_id=data.project_id,
            created_by=user_id,
            note_type=data.note_type,
            title=data.title,
            content=data.content,
            participants=data.participants,
            meeting_date=data.meeting_date,
            is_private=data.is_private,
            enrichment_status="pending",
        )
        self.db.add(note)
        await self.db.commit()
        await self.db.refresh(note)
        return note

    # ── Read ──────────────────────────────────────────────────────────────

    async def list_notes(
        self,
        org_id: uuid.UUID,
        project_id: uuid.UUID | None = None,
    ) -> list[ExpertNote]:
        stmt = (
            select(ExpertNote)
            .where(ExpertNote.org_id == org_id)
            .where(ExpertNote.is_deleted == False)  # noqa: E712
            .order_by(ExpertNote.created_at.desc())
        )
        if project_id is not None:
            stmt = stmt.where(ExpertNote.project_id == project_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_note(
        self,
        org_id: uuid.UUID,
        note_id: uuid.UUID,
    ) -> ExpertNote | None:
        stmt = (
            select(ExpertNote)
            .where(ExpertNote.id == note_id)
            .where(ExpertNote.org_id == org_id)
            .where(ExpertNote.is_deleted == False)  # noqa: E712
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_note_by_id(self, note_id: uuid.UUID) -> ExpertNote | None:
        """Internal lookup without org scope — used during async enrichment."""
        stmt = (
            select(ExpertNote)
            .where(ExpertNote.id == note_id)
            .where(ExpertNote.is_deleted == False)  # noqa: E712
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    # ── Update ────────────────────────────────────────────────────────────

    async def update_note(
        self,
        org_id: uuid.UUID,
        note_id: uuid.UUID,
        data: UpdateExpertNoteRequest,
    ) -> ExpertNote | None:
        note = await self.get_note(org_id, note_id)
        if not note:
            return None
        if data.title is not None:
            note.title = data.title
        if data.content is not None:
            note.content = data.content
        if data.participants is not None:
            note.participants = data.participants
        if data.meeting_date is not None:
            note.meeting_date = data.meeting_date
        if data.is_private is not None:
            note.is_private = data.is_private
        await self.db.commit()
        await self.db.refresh(note)
        return note

    # ── Delete ────────────────────────────────────────────────────────────

    async def delete_note(
        self,
        org_id: uuid.UUID,
        note_id: uuid.UUID,
    ) -> bool:
        note = await self.get_note(org_id, note_id)
        if not note:
            return False
        note.is_deleted = True
        await self.db.commit()
        return True

    # ── AI Enrichment ─────────────────────────────────────────────────────

    async def enrich_note(self, note_id: uuid.UUID) -> ExpertNote | None:
        """Call AI gateway to generate summary, key_takeaways, risk_factors, linked_dimensions."""
        note = await self.get_note_by_id(note_id)
        if not note:
            return None

        note.enrichment_status = "processing"
        await self.db.commit()

        prompt = f"""Analyze these expert notes and extract structured insights:

Title: {note.title}
Type: {note.note_type}
Content: {note.content}
Participants: {json.dumps(note.participants) if note.participants else "Not specified"}

Provide a JSON response with:
- summary: 2-3 sentence executive summary
- key_takeaways: list of 3-5 bullet point takeaways (strings)
- risk_factors_identified: list of risk factors mentioned (strings)
- linked_signal_dimensions: list of signal dimensions affected (from: market_opportunity, team_strength, financial_planning, risk_assessment, esg_alignment, execution_capability)

Respond ONLY with valid JSON (no markdown, no extra text)."""

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{settings.AI_GATEWAY_URL}/v1/completions",
                    json={
                        "messages": [{"role": "user", "content": prompt}],
                        "task_type": "expert_note_enrichment",
                        "max_tokens": 800,
                        "temperature": 0.3,
                    },
                    headers={
                        "Authorization": f"Bearer {settings.AI_GATEWAY_API_KEY}",
                        "Content-Type": "application/json",
                    },
                )

            if response.status_code == 200:
                data = response.json()
                content = data.get("content", "")

                # Parse JSON from response (handle markdown code blocks)
                parsed: dict = {}
                try:
                    parsed = json.loads(content)
                except json.JSONDecodeError:
                    if "```" in content:
                        json_str = content.split("```")[1]
                        if json_str.startswith("json"):
                            json_str = json_str[4:]
                        try:
                            parsed = json.loads(json_str.strip())
                        except json.JSONDecodeError:
                            pass

                note.ai_summary = parsed.get("summary")
                note.key_takeaways = parsed.get("key_takeaways", [])
                note.risk_factors_identified = parsed.get("risk_factors_identified", [])
                note.linked_signal_dimensions = parsed.get("linked_signal_dimensions", [])
                note.enrichment_status = "done"
                logger.info("expert_note_enrichment_success", note_id=str(note_id))
            else:
                note.enrichment_status = "failed"
                logger.warning(
                    "expert_note_enrichment_http_error",
                    note_id=str(note_id),
                    status_code=response.status_code,
                )
        except Exception as exc:
            note.enrichment_status = "failed"
            logger.error(
                "expert_note_enrichment_failed",
                note_id=str(note_id),
                error=str(exc),
            )

        await self.db.commit()
        await self.db.refresh(note)
        return note

    # ── Timeline ──────────────────────────────────────────────────────────

    async def get_project_insights_timeline(
        self,
        org_id: uuid.UUID,
        project_id: uuid.UUID,
    ) -> dict:
        """Notes ordered by meeting_date, returned as timeline entries."""
        stmt = (
            select(ExpertNote)
            .where(ExpertNote.org_id == org_id)
            .where(ExpertNote.project_id == project_id)
            .where(ExpertNote.is_deleted == False)  # noqa: E712
            .order_by(ExpertNote.meeting_date.desc().nulls_last(), ExpertNote.created_at.desc())
        )
        result = await self.db.execute(stmt)
        notes = list(result.scalars().all())

        timeline = [
            {
                "note_id": str(note.id),
                "date": note.meeting_date.isoformat() if note.meeting_date else None,
                "note_type": note.note_type,
                "title": note.title,
                "ai_summary": note.ai_summary,
                "risk_factors": note.risk_factors_identified,
                "enrichment_status": note.enrichment_status,
            }
            for note in notes
        ]

        return {"timeline": timeline, "total": len(timeline)}
