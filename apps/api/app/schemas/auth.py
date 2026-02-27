"""Auth schemas: CurrentUser, profile, preferences, permissions."""

import uuid

from pydantic import BaseModel

from app.models.enums import OrgType, UserRole


class CurrentUser(BaseModel):
    """Lightweight user context extracted from Clerk JWT + DB lookup."""

    user_id: uuid.UUID
    org_id: uuid.UUID
    role: UserRole
    email: str
    external_auth_id: str  # Clerk user ID (e.g. "user_2x...")


class UserProfileResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: UserRole
    org_id: uuid.UUID
    org_name: str
    org_type: OrgType
    org_slug: str
    avatar_url: str | None = None
    mfa_enabled: bool
    preferences: dict
    permissions: dict[str, list[str]]  # resource_type -> allowed actions


class UpdatePreferencesRequest(BaseModel):
    preferences: dict  # partial merge into existing JSONB


class SwitchOrgRequest(BaseModel):
    org_id: uuid.UUID


class SwitchOrgResponse(BaseModel):
    org_id: uuid.UUID
    org_name: str
    role: UserRole


class PermissionMatrixResponse(BaseModel):
    role: UserRole
    permissions: dict[str, list[str]]  # resource_type -> actions
