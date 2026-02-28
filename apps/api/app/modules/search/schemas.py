"""Search request and response schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ProjectHit(BaseModel):
    type: Literal["project"] = "project"
    id: str
    org_id: str
    name: str
    project_type: str | None = None
    status: str | None = None
    stage: str | None = None
    geography_country: str | None = None
    total_investment_required: float | None = None
    score: float


class ListingHit(BaseModel):
    type: Literal["listing"] = "listing"
    id: str
    org_id: str
    project_id: str | None = None
    headline: str
    listing_type: str | None = None
    sector: str | None = None
    score: float


class DocumentHit(BaseModel):
    type: Literal["document"] = "document"
    id: str
    org_id: str
    project_id: str | None = None
    filename: str
    document_type: str | None = None
    snippet: str | None = None  # highlighted excerpt from extracted_text
    score: float


class SearchResponse(BaseModel):
    query: str
    total: int
    projects: list[ProjectHit] = Field(default_factory=list)
    listings: list[ListingHit] = Field(default_factory=list)
    documents: list[DocumentHit] = Field(default_factory=list)


class ReindexResponse(BaseModel):
    indexed_projects: int
    indexed_listings: int
    indexed_documents: int
    errors: list[str] = Field(default_factory=list)
