"""Stress test Pydantic schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RunStressTestRequest(BaseModel):
    portfolio_id: uuid.UUID
    scenario_key: str = "combined_downturn"  # predefined key or "custom"
    custom_params: dict[str, Any] | None = None  # used when scenario_key == "custom"
    custom_name: str | None = None
    simulations: int = Field(default=10_000, ge=1000, le=100_000)


class ProjectSensitivity(BaseModel):
    project_id: str
    project_name: str
    base_value: float
    stressed_value: float
    change_pct: float


class StressTestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    portfolio_id: uuid.UUID
    scenario_key: str
    scenario_name: str
    parameters: dict[str, Any]
    simulations_count: int
    base_nav: float
    mean_nav: float
    median_nav: float
    p5_nav: float
    p95_nav: float
    var_95: float
    max_loss_pct: float
    probability_of_loss: float
    histogram: list[int]
    histogram_edges: list[float]
    project_sensitivities: list[ProjectSensitivity]
    created_at: datetime


class StressTestListResponse(BaseModel):
    items: list[StressTestResponse]
    total: int


class ScenarioResponse(BaseModel):
    key: str
    name: str
    description: str
    params: dict[str, Any]
