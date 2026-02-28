"""Warm Introductions module API schemas."""

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


# ── Connection schemas ────────────────────────────────────────────────────────


class ConnectionCreateRequest(BaseModel):
    connection_type: str = Field(
        ...,
        description="advisor, co_investor, service_provider, board_member, lp_relationship",
    )
    connected_org_name: str = Field(..., min_length=1, max_length=200)
    connected_person_name: str | None = Field(None, max_length=200)
    connected_person_email: str | None = Field(None, max_length=200)
    relationship_strength: str = Field(
        "moderate", description="weak, moderate, strong"
    )
    last_interaction_date: date | None = None
    notes: str | None = None


class ConnectionUpdateRequest(BaseModel):
    connection_type: str | None = None
    connected_org_name: str | None = Field(None, max_length=200)
    connected_person_name: str | None = Field(None, max_length=200)
    connected_person_email: str | None = Field(None, max_length=200)
    relationship_strength: str | None = None
    last_interaction_date: date | None = None
    notes: str | None = None


class ConnectionResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    org_id: uuid.UUID
    connection_type: str
    connected_org_name: str
    connected_person_name: str | None
    connected_person_email: str | None
    relationship_strength: str
    last_interaction_date: date | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


# ── Introduction path schemas ─────────────────────────────────────────────────


class IntroPathResponse(BaseModel):
    type: str
    connector_org: str
    connector_person: str | None
    connection_type: str
    warmth: float


class PathsResponse(BaseModel):
    investor_id: uuid.UUID
    paths: list[IntroPathResponse]


# ── Suggestion schemas ────────────────────────────────────────────────────────


class WarmIntroSuggestion(BaseModel):
    investor_org_id: uuid.UUID
    investor_name: str
    warmth_score: float
    best_path: IntroPathResponse | None
    all_paths: list[IntroPathResponse]


class SuggestionsResponse(BaseModel):
    project_id: uuid.UUID
    items: list[WarmIntroSuggestion]
    total: int


# ── Introduction request schemas ──────────────────────────────────────────────


class IntroRequestCreateRequest(BaseModel):
    target_investor_id: uuid.UUID
    project_id: uuid.UUID | None = None
    path: dict[str, Any]
    message: str = Field(..., min_length=1, max_length=2000)


class IntroRequestStatusUpdateRequest(BaseModel):
    status: str = Field(..., description="pending, sent, accepted, declined")


class IntroRequestResponse(BaseModel):
    id: uuid.UUID
    requester_id: uuid.UUID
    requester_org_id: uuid.UUID
    target_investor_id: uuid.UUID
    connector_id: uuid.UUID | None
    project_id: uuid.UUID | None
    warmth_score: float | None
    introduction_path: dict[str, Any] | None
    status: str
    message: str | None
    created_at: datetime
    updated_at: datetime
