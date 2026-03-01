"""CRM Sync — Pydantic v2 request/response schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class CRMConnectionResponse(BaseModel):
    id: uuid.UUID
    provider: str
    portal_id: str | None = None
    sync_frequency: str
    sync_direction: str
    last_sync_at: datetime | None = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class FieldMappingUpdate(BaseModel):
    field_mappings: dict[str, str]
    sync_frequency: str | None = None
    sync_direction: str | None = None


class SyncLogResponse(BaseModel):
    id: uuid.UUID
    direction: str
    entity_type: str
    scr_entity_id: uuid.UUID | None = None
    crm_entity_id: str | None = None
    action: str
    status: str
    error_message: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TestConnectionResponse(BaseModel):
    success: bool
    message: str
    portal_id: str | None = None
