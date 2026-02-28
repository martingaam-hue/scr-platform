"""Watchlist Pydantic schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class WatchlistCreate(BaseModel):
    name: str
    watch_type: str  # new_projects, score_changes, risk_alerts, market_events, specific_project
    nl_query: str | None = None  # optional: auto-populate criteria via NL parser
    criteria: dict[str, Any] = {}
    alert_channels: list[str] = ["in_app"]
    alert_frequency: str = "immediate"  # immediate, daily_digest, weekly


class WatchlistUpdate(BaseModel):
    name: str | None = None
    criteria: dict[str, Any] | None = None
    alert_channels: list[str] | None = None
    alert_frequency: str | None = None
    is_active: bool | None = None


class WatchlistResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    user_id: uuid.UUID
    org_id: uuid.UUID
    name: str
    watch_type: str
    criteria: dict[str, Any]
    alert_channels: list[str]
    alert_frequency: str
    is_active: bool
    total_alerts_sent: int
    created_at: datetime


class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    watchlist_id: uuid.UUID
    user_id: uuid.UUID
    alert_type: str
    title: str
    description: str | None
    entity_type: str | None
    entity_id: uuid.UUID | None
    data: dict[str, Any]
    is_read: bool
    created_at: datetime


class AlertListResponse(BaseModel):
    items: list[AlertResponse]
    total: int
    unread_count: int
