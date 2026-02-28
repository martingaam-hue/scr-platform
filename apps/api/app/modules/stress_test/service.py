"""Stress test service — load portfolio data and persist results."""

from __future__ import annotations

import uuid
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stress_test import StressTestRun
from app.modules.stress_test.engine import PREDEFINED_SCENARIOS, run_monte_carlo

logger = structlog.get_logger()


async def _get_portfolio_projects(db: AsyncSession, portfolio_id: uuid.UUID, org_id: uuid.UUID) -> list[dict[str, Any]]:
    """Load holdings with project financial data for simulation."""
    from app.models.investors import Portfolio, PortfolioHolding
    from app.models.projects import Project

    result = await db.execute(
        select(PortfolioHolding, Project)
        .join(Project, PortfolioHolding.project_id == Project.id)
        .join(Portfolio, PortfolioHolding.portfolio_id == Portfolio.id)
        .where(
            PortfolioHolding.portfolio_id == portfolio_id,
            Portfolio.org_id == org_id,
            PortfolioHolding.is_deleted == False,
            Project.is_deleted == False,
        )
    )
    rows = result.all()

    projects: list[dict[str, Any]] = []
    for holding, project in rows:
        projects.append({
            "id": str(holding.id),
            "name": project.name,
            "current_value": float(holding.current_value or holding.investment_amount or 0),
            "project_type": project.project_type or "general",
            "stage": project.stage or "operational",
            "currency": getattr(project, "project_currency", "EUR") or "EUR",
            "leverage_ratio": float(getattr(holding, "leverage_ratio", 0.5) or 0.5),
        })
    return projects


async def run_stress_test(
    db: AsyncSession,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    portfolio_id: uuid.UUID,
    scenario_key: str,
    custom_params: dict[str, Any] | None = None,
    custom_name: str | None = None,
    simulations: int = 10_000,
) -> StressTestRun:
    if scenario_key == "custom":
        if not custom_params:
            raise ValueError("custom_params required for custom scenario")
        params = custom_params
        name = custom_name or "Custom Scenario"
    else:
        scenario = PREDEFINED_SCENARIOS.get(scenario_key)
        if not scenario:
            raise ValueError(f"Unknown scenario: {scenario_key}")
        params = scenario["params"]
        name = scenario["name"]

    projects = await _get_portfolio_projects(db, portfolio_id, org_id)
    if not projects:
        raise ValueError("Portfolio has no holdings to stress test")

    logger.info("stress_test.running", portfolio_id=str(portfolio_id), scenario=scenario_key, n=simulations)
    results = run_monte_carlo(projects, params, simulations)

    run = StressTestRun(
        org_id=org_id,
        portfolio_id=portfolio_id,
        created_by=user_id,
        scenario_key=scenario_key,
        scenario_name=name,
        parameters=params,
        simulations_count=simulations,
        **results,
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)
    return run


async def list_stress_tests(
    db: AsyncSession, org_id: uuid.UUID, portfolio_id: uuid.UUID
) -> list[StressTestRun]:
    result = await db.execute(
        select(StressTestRun)
        .where(
            StressTestRun.org_id == org_id,
            StressTestRun.portfolio_id == portfolio_id,
            StressTestRun.is_deleted == False,
        )
        .order_by(StressTestRun.created_at.desc())
    )
    return list(result.scalars().all())


async def get_stress_test(
    db: AsyncSession, run_id: uuid.UUID, org_id: uuid.UUID
) -> StressTestRun | None:
    result = await db.execute(
        select(StressTestRun).where(
            StressTestRun.id == run_id,
            StressTestRun.org_id == org_id,
            StressTestRun.is_deleted == False,
        )
    )
    return result.scalar_one_or_none()
