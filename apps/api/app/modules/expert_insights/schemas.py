"""Pydantic v2 schemas for Expert Insights module."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel


class CreateExpertNoteRequest(BaseModel):
    project_id: uuid.UUID
    note_type: str
    title: str
    content: str
    participants: list[dict] | None = None
    meeting_date: date | None = None
    is_private: bool = False


class UpdateExpertNoteRequest(BaseModel):
    title: str | None = None
    content: str | None = None
    participants: list[dict] | None = None
    meeting_date: date | None = None
    is_private: bool | None = None


class ExpertNoteResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    project_id: uuid.UUID | None
    created_by: uuid.UUID | None
    note_type: str
    title: str
    content: str
    ai_summary: str | None
    key_takeaways: list[str] | None
    risk_factors_identified: list[str] | None
    linked_signal_dimensions: list[str] | None
    participants: list[dict] | None
    meeting_date: date | None
    enrichment_status: str
    is_private: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ExpertNoteListResponse(BaseModel):
    items: list[ExpertNoteResponse]
    total: int


class InsightsTimelineEntry(BaseModel):
    note_id: uuid.UUID
    date: date | None
    note_type: str
    title: str
    ai_summary: str | None
    risk_factors: list[str] | None
    enrichment_status: str


class InsightsTimelineResponse(BaseModel):
    timeline: list[InsightsTimelineEntry]
    total: int
