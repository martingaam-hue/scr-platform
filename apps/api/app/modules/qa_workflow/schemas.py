"""Q&A Workflow — Pydantic v2 schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class QAQuestionCreate(BaseModel):
    question: str = Field(..., min_length=1, max_length=5000)
    category: str = Field(
        ...,
        pattern="^(financial|legal|technical|commercial|regulatory|esg|operational)$",
    )
    priority: str = Field(
        default="normal",
        pattern="^(urgent|high|normal|low)$",
    )
    deal_room_id: uuid.UUID | None = None
    tags: list[str] | None = None


class QAQuestionUpdate(BaseModel):
    status: str | None = Field(
        default=None,
        pattern="^(open|assigned|in_progress|answered|closed|declined)$",
    )
    assigned_to: uuid.UUID | None = None
    tags: list[str] | None = None


class QAAnswerCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=20000)
    is_official: bool = False
    linked_documents: list[uuid.UUID] | None = None


class QAAnswerResponse(BaseModel):
    id: uuid.UUID
    question_id: uuid.UUID
    answered_by: uuid.UUID
    content: str
    is_official: bool
    approved_by: uuid.UUID | None = None
    linked_documents: list[uuid.UUID] | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class QAQuestionResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    project_id: uuid.UUID
    deal_room_id: uuid.UUID | None = None
    question_number: int
    question: str
    category: str
    priority: str
    asked_by: uuid.UUID
    assigned_to: uuid.UUID | None = None
    assigned_team: str | None = None
    status: str
    sla_deadline: datetime | None = None
    answered_at: datetime | None = None
    sla_breached: bool
    linked_documents: list[uuid.UUID] | None = None
    tags: list[str] | None = None
    created_at: datetime
    updated_at: datetime
    answers: list[QAAnswerResponse] = []

    model_config = {"from_attributes": True}


class QAStatsResponse(BaseModel):
    total: int
    open: int
    answered: int
    overdue: int
    avg_response_hours: float | None = None
