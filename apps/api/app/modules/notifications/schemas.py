"""Notification Pydantic schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import NotificationType


class NotificationResponse(BaseModel):
    id: uuid.UUID
    type: NotificationType
    title: str
    message: str
    link: str | None
    is_read: bool
    created_at: datetime


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class UnreadCountResponse(BaseModel):
    count: int


class UpdatePreferencesRequest(BaseModel):
    preferences: dict  # merged into user.preferences.notification_settings
