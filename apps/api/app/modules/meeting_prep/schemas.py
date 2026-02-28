"""Meeting Prep — Pydantic schemas."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class GenerateBriefingRequest(BaseModel):
    project_id: uuid.UUID
    meeting_type: str  # screening | dd_review | follow_up | ic_presentation
    meeting_date: date | None = None
    previous_meeting_date: date | None = None


class UpdateBriefingRequest(BaseModel):
    """Save user edits as custom_overrides."""
    custom_overrides: dict[str, Any]


class BriefingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    org_id: uuid.UUID
    project_id: uuid.UUID
    created_by: uuid.UUID
    meeting_type: str
    meeting_date: date | None
    previous_meeting_date: date | None
    briefing_content: dict[str, Any] | None
    custom_overrides: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    @property
    def effective_content(self) -> dict[str, Any]:
        """Merge custom_overrides on top of briefing_content."""
        content = dict(self.briefing_content or {})
        content.update(self.custom_overrides or {})
        return content


class BriefingListResponse(BaseModel):
    items: list[BriefingResponse]
    total: int
