"""Engagement tracking Pydantic schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ── Request schemas ────────────────────────────────────────────────────────────


class TrackOpenRequest(BaseModel):
    """Payload sent when a viewer opens a document."""

    document_id: uuid.UUID
    session_id: str
    total_pages: int | None = None
    referrer: str | None = None
    device_type: str | None = None  # desktop | tablet | mobile


class TrackPageRequest(BaseModel):
    """Payload sent after a viewer dwells on a page."""

    engagement_id: uuid.UUID
    page_number: int = Field(..., ge=1)
    time_seconds: int = Field(..., ge=0)


class TrackCloseRequest(BaseModel):
    """Payload sent when the viewer closes / navigates away from a document."""

    engagement_id: uuid.UUID


class TrackDownloadRequest(BaseModel):
    """Payload sent when the viewer downloads the document."""

    engagement_id: uuid.UUID


# ── Response schemas ───────────────────────────────────────────────────────────


class EngagementSessionResponse(BaseModel):
    """Full representation of a single DocumentEngagement session."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    org_id: uuid.UUID
    document_id: uuid.UUID
    user_id: uuid.UUID
    session_id: str

    opened_at: datetime
    closed_at: datetime | None
    total_time_seconds: int

    pages_viewed: list[Any]
    total_pages: int | None
    pages_viewed_count: int
    completion_pct: float

    downloaded: bool
    printed: bool

    referrer_page: str | None
    device_type: str | None


class DocumentAnalyticsResponse(BaseModel):
    """Aggregate analytics for a single document across all sessions."""

    document_id: uuid.UUID
    total_views: int
    unique_viewers: int
    total_time_seconds: int
    avg_time_seconds: float
    avg_completion_pct: float
    download_count: int
    # page_number → total_time_seconds across all sessions
    page_heatmap: dict[int, int]
    # Last 20 sessions, ordered most-recent first
    recent_sessions: list[dict[str, Any]]


class InvestorEngagementResponse(BaseModel):
    """Per-investor engagement summary for a project."""

    investor_org_id: uuid.UUID
    total_sessions: int
    total_time_seconds: int
    unique_documents_viewed: int
    total_documents_available: int
    documents_downloaded: int
    last_activity_at: datetime | None
    engagement_score: float | None
