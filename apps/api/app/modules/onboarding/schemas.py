"""Onboarding schemas."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class OnboardingCompleteRequest(BaseModel):
    """Payload sent when a user finishes the onboarding wizard."""

    org_type: Literal["investor", "ally"]
    org_name: str = Field(..., min_length=1, max_length=255)
    org_industry: str | None = None
    org_geography: str | None = None
    org_size: str | None = None  # ally: team size
    org_aum: str | None = None  # investor: AUM
    preferences: dict[str, Any] = Field(default_factory=dict)
    first_action: dict[str, Any] | None = None


class OnboardingCompleteResponse(BaseModel):
    success: bool
    org_type: str
    created_entities: dict[str, Any]
    redirect_to: str
