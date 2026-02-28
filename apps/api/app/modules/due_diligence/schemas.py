"""Due Diligence Checklist — Pydantic v2 schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


# ── Template schemas ──────────────────────────────────────────────────────────


class DDTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    asset_type: str
    deal_stage: str
    jurisdiction_group: str | None
    name: str
    description: str | None
    version: int
    item_count: int = 0


# ── Item schemas ──────────────────────────────────────────────────────────────


class DDItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    template_id: uuid.UUID
    category: str
    name: str
    description: str | None
    requirement_type: str
    required_document_types: list[Any] | None
    verification_criteria: str | None
    priority: str
    sort_order: int
    estimated_time_hours: float | None
    regulatory_reference: str | None


# ── Item status schemas ───────────────────────────────────────────────────────


class DDItemStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    item_id: uuid.UUID
    checklist_id: uuid.UUID
    status: str
    satisfied_by_document_id: uuid.UUID | None
    ai_review_result: dict[str, Any] | None
    reviewer_notes: str | None
    reviewed_at: datetime | None


# ── Combined item + status ────────────────────────────────────────────────────


class DDChecklistItemFull(BaseModel):
    """A checklist item merged with its current status for this checklist."""

    # Item fields
    item_id: uuid.UUID
    template_id: uuid.UUID
    category: str
    name: str
    description: str | None
    requirement_type: str
    required_document_types: list[Any] | None
    verification_criteria: str | None
    priority: str
    sort_order: int
    estimated_time_hours: float | None
    regulatory_reference: str | None

    # Status fields (may be None if no status record yet)
    status_id: uuid.UUID | None = None
    status: str = "pending"
    satisfied_by_document_id: uuid.UUID | None = None
    ai_review_result: dict[str, Any] | None = None
    reviewer_notes: str | None = None
    reviewed_at: datetime | None = None


# ── Checklist response ────────────────────────────────────────────────────────


class DDChecklistResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    org_id: uuid.UUID
    template_id: uuid.UUID
    investor_id: uuid.UUID | None
    status: str
    completion_percentage: float
    total_items: int
    completed_items: int
    custom_items: list[Any]
    items_by_category: dict[str, list[DDChecklistItemFull]] = {}
    created_at: datetime
    updated_at: datetime


# ── Request schemas ───────────────────────────────────────────────────────────


class GenerateChecklistRequest(BaseModel):
    project_id: uuid.UUID
    investor_id: uuid.UUID | None = None


class UpdateItemStatusRequest(BaseModel):
    status: str
    notes: str | None = None
    document_id: uuid.UUID | None = None


class AddCustomItemRequest(BaseModel):
    name: str
    category: str
    description: str | None = None
    priority: str = "recommended"


class TriggerAIReviewRequest(BaseModel):
    document_id: uuid.UUID
