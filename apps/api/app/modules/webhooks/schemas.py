"""Pydantic schemas for the Webhook System."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

VALID_EVENTS: list[str] = [
    "signal_score.computed",
    "signal_score.threshold_breach",
    "deal.stage_changed",
    "deal.screening_complete",
    "matching.new_match",
    "matching.score_updated",
    "monitoring.covenant_breach",
    "monitoring.kpi_variance",
    "dataroom.document_uploaded",
    "dataroom.document_accessed",
    "project.published",
    "project.status_changed",
]


class CreateSubscriptionRequest(BaseModel):
    url: str
    secret: str
    events: list[str]
    description: str | None = None


class UpdateSubscriptionRequest(BaseModel):
    url: str | None = None
    events: list[str] | None = None
    description: str | None = None
    is_active: bool | None = None


class WebhookSubscriptionResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    url: str
    events: list[str]
    is_active: bool
    failure_count: int
    disabled_reason: str | None
    description: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class WebhookDeliveryResponse(BaseModel):
    id: uuid.UUID
    subscription_id: uuid.UUID
    event_type: str
    status: str
    response_status_code: int | None
    attempts: int
    next_retry_at: datetime | None
    delivered_at: datetime | None
    error_message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TestWebhookRequest(BaseModel):
    event_type: str = "test.ping"
