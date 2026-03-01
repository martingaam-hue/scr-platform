"""Pydantic v2 schemas for the Document Annotations module."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class CreateAnnotationRequest(BaseModel):
    document_id: uuid.UUID
    annotation_type: str = Field(
        ...,
        description="highlight | note | bookmark | question_link",
    )
    page_number: int = Field(..., ge=1)
    position: dict = Field(
        ...,
        description="Normalised coords: {x, y, width, height, rects?: [{x,y,w,h}]}",
    )
    content: str | None = None
    color: str = "#FFFF00"
    linked_qa_question_id: uuid.UUID | None = None
    linked_citation_id: uuid.UUID | None = None
    is_private: bool = False


class UpdateAnnotationRequest(BaseModel):
    content: str | None = None
    color: str | None = None
    is_private: bool | None = None


class AnnotationResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    annotation_type: str
    page_number: int
    position: dict
    content: str | None
    color: str
    linked_qa_question_id: uuid.UUID | None
    linked_citation_id: uuid.UUID | None
    is_private: bool
    created_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
