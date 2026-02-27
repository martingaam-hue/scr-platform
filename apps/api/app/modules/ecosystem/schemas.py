"""Ecosystem schemas — stakeholder relationship mapping."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class StakeholderNode(BaseModel):
    id: str
    name: str
    type: str           # investor, ally, advisor, regulator, partner, supplier, community
    sub_type: str | None
    relationship_strength: int  # 1–5
    engagement_status: str      # active, passive, at_risk, churned
    tags: list[str]
    metadata: dict[str, Any] | None


class StakeholderEdge(BaseModel):
    source: str
    target: str
    relationship_type: str  # investment, partnership, advisory, regulatory, supply_chain
    weight: int             # 1–10
    description: str | None


class EcosystemMapResponse(BaseModel):
    project_id: uuid.UUID | None
    org_id: uuid.UUID
    nodes: list[StakeholderNode]
    edges: list[StakeholderEdge]
    summary: dict[str, Any]     # {total_stakeholders, by_type, avg_strength}
    last_updated: datetime


class StakeholderCreate(BaseModel):
    name: str
    type: str
    sub_type: str | None = None
    relationship_strength: int = 3
    engagement_status: str = "active"
    tags: list[str] = []
    metadata: dict[str, Any] | None = None


class RelationshipCreate(BaseModel):
    source_id: str
    target_id: str
    relationship_type: str
    weight: int = 5
    description: str | None = None
