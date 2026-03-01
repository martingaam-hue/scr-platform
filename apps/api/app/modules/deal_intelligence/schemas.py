"""Deal Intelligence API schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator


# ── Pipeline ─────────────────────────────────────────────────────────────────


class DealCardResponse(BaseModel):
    project_id: uuid.UUID
    match_id: uuid.UUID
    project_name: str
    project_type: str
    geography_country: str
    stage: str
    total_investment_required: str
    currency: str
    signal_score: int | None
    alignment_score: int
    status: str
    cover_image_url: str | None
    updated_at: datetime


class DealPipelineResponse(BaseModel):
    discovered: list[DealCardResponse]
    screening: list[DealCardResponse]
    due_diligence: list[DealCardResponse]
    negotiation: list[DealCardResponse]
    passed: list[DealCardResponse]


# ── Discovery ────────────────────────────────────────────────────────────────


class DiscoveryDealResponse(BaseModel):
    project_id: uuid.UUID
    project_name: str
    project_type: str
    geography_country: str
    stage: str
    total_investment_required: str
    currency: str
    signal_score: int | None
    alignment_score: int
    alignment_reasons: list[str]
    cover_image_url: str | None
    is_in_pipeline: bool


class DiscoveryResponse(BaseModel):
    items: list[DiscoveryDealResponse]
    total: int
    mandate_name: str | None


# ── Screening ────────────────────────────────────────────────────────────────


class ScreeningReportResponse(BaseModel):
    task_log_id: uuid.UUID
    project_id: uuid.UUID
    fit_score: int
    executive_summary: str
    strengths: list[str]
    risks: list[str]
    key_metrics: list[dict]
    mandate_alignment: list[dict]
    recommendation: str
    questions_to_ask: list[str]
    model_used: str
    status: str
    created_at: datetime


class ScreenAcceptedResponse(BaseModel):
    task_log_id: uuid.UUID
    status: str
    message: str


# ── Compare ──────────────────────────────────────────────────────────────────


class CompareRequest(BaseModel):
    project_ids: list[uuid.UUID]

    @field_validator("project_ids")
    @classmethod
    def validate_count(cls, v: list[uuid.UUID]) -> list[uuid.UUID]:
        if len(v) < 2 or len(v) > 5:
            raise ValueError("Must compare between 2 and 5 projects")
        return v


class CompareRow(BaseModel):
    dimension: str
    values: list[str | int | None]
    best_index: int | None
    worst_index: int | None


class CompareResponse(BaseModel):
    project_ids: list[uuid.UUID]
    project_names: list[str]
    rows: list[CompareRow]


# ── Memo ─────────────────────────────────────────────────────────────────────


class MemoAcceptedResponse(BaseModel):
    memo_id: uuid.UUID
    status: str
    message: str


class MemoResponse(BaseModel):
    memo_id: uuid.UUID
    project_id: uuid.UUID
    title: str
    status: str
    content: str | None
    download_url: str | None
    model_used: str | None
    created_at: datetime


# ── Status Update ─────────────────────────────────────────────────────────────


class DealStatusUpdateRequest(BaseModel):
    status: str
    notes: str | None = None


# ── Batch screening ───────────────────────────────────────────────────────────


class BatchScreenRequest(BaseModel):
    project_ids: list[uuid.UUID]


class BatchScreenItem(BaseModel):
    project_id: uuid.UUID
    task_log_id: uuid.UUID
    status: str


class BatchScreenResponse(BaseModel):
    queued: int
    failed: int
    items: list[BatchScreenItem]
    errors: list[dict]
