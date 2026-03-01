"""Pydantic v2 schemas for the AI Document Redaction module."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

# ── Entity type registry ──────────────────────────────────────────────────────

ENTITY_TYPES: list[str] = [
    "person_name",
    "email",
    "phone_number",
    "address",
    "tax_id",
    "bank_account",
    "iban",
    "credit_card",
    "date_of_birth",
    "passport_number",
    "company_name",
    "financial_figure",
    "signature",
]

HIGH_SENSITIVITY: set[str] = {
    "tax_id",
    "bank_account",
    "iban",
    "credit_card",
    "passport_number",
    "date_of_birth",
}


# ── Sub-models ────────────────────────────────────────────────────────────────


class DetectedEntity(BaseModel):
    """A single PII entity detected in the document."""

    id: int
    entity_type: str
    text: str
    page: int
    confidence: float
    position: dict  # {x, y, width, height} normalised percentages
    is_high_sensitivity: bool = False


# ── Request bodies ────────────────────────────────────────────────────────────


class AnalyzeRequest(BaseModel):
    """Optional body for POST /redaction/analyze/{document_id}.

    ``document_text`` can be supplied by the caller when it has already
    extracted the text (e.g. from a prior extraction pipeline run).
    When omitted, the task will attempt to read the extraction cache.
    """

    document_text: str | None = None


class ApproveRedactionsRequest(BaseModel):
    """Indices (matching ``DetectedEntity.id``) selected by the user."""

    approved_entity_ids: list[int]


# ── Response bodies ───────────────────────────────────────────────────────────


class RedactionJobResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    status: str
    detected_entities: list[dict] | None
    approved_redactions: list[dict] | None
    entity_count: int
    approved_count: int
    redacted_document_id: uuid.UUID | None
    redacted_s3_key: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EntityTypeInfo(BaseModel):
    entity_type: str
    is_high_sensitivity: bool


class RedactionRulesResponse(BaseModel):
    entity_types: list[EntityTypeInfo]
    high_sensitivity_types: list[str]
