"""Admin module — Pydantic schemas for platform-level administration."""

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import OrgType, SubscriptionStatus, SubscriptionTier, UserRole


# ── Organization ──────────────────────────────────────────────────────────────


class OrgSummary(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    type: OrgType
    subscription_tier: SubscriptionTier
    subscription_status: SubscriptionStatus
    user_count: int
    created_at: datetime
    updated_at: datetime


class OrgDetail(OrgSummary):
    logo_url: str | None
    settings: dict


class UpdateOrgStatusRequest(BaseModel):
    status: SubscriptionStatus


class UpdateOrgTierRequest(BaseModel):
    tier: SubscriptionTier


# ── User ──────────────────────────────────────────────────────────────────────


class UserSummary(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    org_name: str
    org_type: OrgType
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    mfa_enabled: bool
    last_login_at: datetime | None
    created_at: datetime


class UpdateUserStatusRequest(BaseModel):
    is_active: bool


# ── Analytics ─────────────────────────────────────────────────────────────────


class OrgBreakdown(BaseModel):
    total: int
    ally: int
    investor: int
    admin: int
    trial: int
    active: int
    suspended: int
    cancelled: int


class UserBreakdown(BaseModel):
    total: int
    active: int
    inactive: int
    admins: int
    managers: int
    analysts: int
    viewers: int


class PlatformAnalytics(BaseModel):
    orgs: OrgBreakdown
    users: UserBreakdown
    total_projects: int
    total_portfolios: int
    total_ai_conversations: int
    total_documents: int
    generated_at: datetime


# ── AI Cost Report ────────────────────────────────────────────────────────────


class AICostEntry(BaseModel):
    label: str
    task_count: int
    total_tokens: int
    avg_processing_ms: float | None
    failed_count: int


class AICostReport(BaseModel):
    period_days: int
    total_tasks: int
    total_tokens: int
    total_failed: int
    by_agent: list[AICostEntry]
    by_model: list[AICostEntry]
    by_org: list[AICostEntry]


# ── Audit Logs ────────────────────────────────────────────────────────────────


class AuditLogEntry(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    org_name: str | None
    user_id: uuid.UUID | None
    user_email: str | None
    action: str
    entity_type: str
    entity_id: uuid.UUID | None
    ip_address: str | None
    timestamp: datetime


class AuditLogPage(BaseModel):
    items: list[AuditLogEntry]
    total: int
    limit: int
    offset: int


# ── System Health ─────────────────────────────────────────────────────────────


class ServiceHealth(BaseModel):
    name: str
    status: str  # "ok" | "degraded" | "down"
    latency_ms: float | None
    detail: str | None


class SystemHealthResponse(BaseModel):
    overall: str  # "ok" | "degraded" | "down"
    services: list[ServiceHealth]
    checked_at: datetime
