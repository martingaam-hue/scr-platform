"""Pydantic schemas for Custom Domain module (E03)."""

import re
import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator


class SetDomainRequest(BaseModel):
    domain: str  # e.g. "app.acme.com"

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v: str) -> str:
        v = v.lower().strip()
        # Must be a valid hostname, no scheme, no path
        if not re.match(r'^[a-z0-9]([a-z0-9\-\.]{0,251}[a-z0-9])?$', v):
            raise ValueError("Invalid domain format")
        if v.endswith(".scr.io"):
            raise ValueError("Cannot use scr.io subdomains as custom domains")
        return v


class CustomDomainResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    domain: str
    status: str
    cname_target: str
    verification_token: str
    verified_at: datetime | None
    ssl_provisioned_at: datetime | None
    last_checked_at: datetime | None
    error_message: str | None
    created_at: datetime

    # Instructions for the user
    dns_instructions: dict  # cname_record + txt_record instructions

    model_config = {"from_attributes": True}


class VerifyDomainResponse(BaseModel):
    success: bool
    status: str
    message: str
    verified_at: datetime | None = None
