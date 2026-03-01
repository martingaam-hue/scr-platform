"""Settings module schemas: org profile, team management, API keys, preferences, branding."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, field_validator

from app.models.enums import OrgType, SubscriptionStatus, SubscriptionTier, UserRole


# ── Organization ────────────────────────────────────────────────────────────


class OrgResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    type: OrgType
    logo_url: str | None
    settings: dict[str, Any]
    subscription_tier: SubscriptionTier
    subscription_status: SubscriptionStatus
    created_at: datetime


class OrgUpdateRequest(BaseModel):
    name: str | None = None
    logo_url: str | None = None
    settings: dict[str, Any] | None = None


# ── Team ─────────────────────────────────────────────────────────────────────


class TeamMember(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: UserRole
    avatar_url: str | None
    is_active: bool
    mfa_enabled: bool
    last_login_at: datetime | None
    created_at: datetime


class TeamListResponse(BaseModel):
    items: list[TeamMember]
    total: int


class InviteUserRequest(BaseModel):
    email: EmailStr
    full_name: str
    role: UserRole = UserRole.VIEWER


class UpdateUserRoleRequest(BaseModel):
    role: UserRole


class ToggleUserStatusRequest(BaseModel):
    is_active: bool


# ── API Keys ─────────────────────────────────────────────────────────────────


class ApiKeyItem(BaseModel):
    id: str
    name: str
    prefix: str        # first 8 chars of key, for display
    is_active: bool
    created_at: str
    last_used_at: str | None


class ApiKeyListResponse(BaseModel):
    items: list[ApiKeyItem]


class ApiKeyCreateRequest(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Name must not be blank")
        return v.strip()


class ApiKeyCreatedResponse(BaseModel):
    """Returned once only — key is never retrievable again."""
    id: str
    name: str
    key: str           # full key shown only at creation
    created_at: str


# ── Preferences ──────────────────────────────────────────────────────────────


class NotificationPreferences(BaseModel):
    email_match_alerts: bool = True
    email_project_updates: bool = True
    email_report_ready: bool = True
    email_weekly_digest: bool = False
    in_app_mentions: bool = True
    in_app_match_alerts: bool = True
    in_app_status_changes: bool = True
    digest_frequency: str = "weekly"  # never | daily | weekly


class PreferencesResponse(BaseModel):
    notification: NotificationPreferences
    raw: dict[str, Any]


# ── Branding ──────────────────────────────────────────────────────────────────


class BrandingSettings(BaseModel):
    primary_color: str = "#6366f1"
    logo_url: str | None = None
    company_name: str | None = None
    accent_color: str = "#8b5cf6"
    font_family: str = "Inter"


class BrandingResponse(BrandingSettings):
    org_id: uuid.UUID


class BrandingUpdateRequest(BaseModel):
    primary_color: str | None = None
    logo_url: str | None = None
    company_name: str | None = None
    accent_color: str | None = None
    font_family: str | None = None
