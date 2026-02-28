"""Connectors service — registry, org config, usage tracking."""

from __future__ import annotations

import uuid
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.connectors import DataConnector, DataFetchLog, OrgConnectorConfig

logger = structlog.get_logger()

# ── Connector registry ────────────────────────────────────────────────────────

_CATALOG = [
    {
        "name": "entso_e",
        "display_name": "ENTSO-E Transparency Platform",
        "category": "energy",
        "description": "European electricity market data — day-ahead prices, generation forecasts, cross-border flows.",
        "base_url": "https://web-api.tp.entsoe.eu/api",
        "auth_type": "api_key",
        "pricing_tier": "free",
        "rate_limit_per_minute": 30,
        "documentation_url": "https://transparency.entsoe.eu/content/static_content/Static%20content/web%20api/Guide.html",
    },
    {
        "name": "companies_house",
        "display_name": "Companies House",
        "category": "company",
        "description": "UK company registry — company info, filing history, officers, persons with significant control.",
        "base_url": "https://api.company-information.service.gov.uk",
        "auth_type": "api_key",
        "pricing_tier": "free",
        "rate_limit_per_minute": 60,
        "documentation_url": "https://developer.company-information.service.gov.uk/",
    },
    {
        "name": "open_weather",
        "display_name": "OpenWeatherMap",
        "category": "weather",
        "description": "Current weather, forecasts, and solar irradiance data for any location.",
        "base_url": "https://api.openweathermap.org",
        "auth_type": "api_key",
        "pricing_tier": "free",
        "rate_limit_per_minute": 60,
        "documentation_url": "https://openweathermap.org/api",
    },
    {
        "name": "ecb",
        "display_name": "European Central Bank",
        "category": "market_data",
        "description": "ECB reference exchange rates and economic statistics — no API key required.",
        "base_url": "https://data-api.ecb.europa.eu/service",
        "auth_type": "none",
        "pricing_tier": "free",
        "rate_limit_per_minute": 60,
        "documentation_url": "https://data.ecb.europa.eu/help/api",
    },
]


async def seed_catalog(db: AsyncSession) -> None:
    """Upsert the connector catalog (run at startup or via CLI)."""
    for entry in _CATALOG:
        stmt = (
            pg_insert(DataConnector)
            .values(**entry)
            .on_conflict_do_update(index_elements=["name"], set_=entry)
        )
        await db.execute(stmt)
    await db.commit()


def _get_connector_instance(name: str, api_key: str | None, config: dict | None) -> Any:
    """Instantiate the correct connector class by name."""
    from app.modules.connectors.implementations.entso_e import ENTSOEConnector
    from app.modules.connectors.implementations.companies_house import CompaniesHouseConnector
    from app.modules.connectors.implementations.open_weather import OpenWeatherConnector
    from app.modules.connectors.implementations.ecb_connector import ECBConnector

    registry = {
        "entso_e": ENTSOEConnector,
        "companies_house": CompaniesHouseConnector,
        "open_weather": OpenWeatherConnector,
        "ecb": ECBConnector,
    }
    cls = registry.get(name)
    if not cls:
        raise ValueError(f"Unknown connector: {name}")
    return cls(api_key=api_key, config=config)


async def list_connectors(db: AsyncSession) -> list[DataConnector]:
    result = await db.execute(
        select(DataConnector).where(DataConnector.is_deleted == False, DataConnector.is_available == True)
    )
    return list(result.scalars().all())


async def get_org_config(db: AsyncSession, org_id: uuid.UUID, connector_id: uuid.UUID) -> OrgConnectorConfig | None:
    result = await db.execute(
        select(OrgConnectorConfig).where(
            OrgConnectorConfig.org_id == org_id,
            OrgConnectorConfig.connector_id == connector_id,
            OrgConnectorConfig.is_deleted == False,
        )
    )
    return result.scalar_one_or_none()


async def list_org_configs(db: AsyncSession, org_id: uuid.UUID) -> list[OrgConnectorConfig]:
    result = await db.execute(
        select(OrgConnectorConfig).where(
            OrgConnectorConfig.org_id == org_id, OrgConnectorConfig.is_deleted == False
        )
    )
    return list(result.scalars().all())


async def enable_connector(
    db: AsyncSession, org_id: uuid.UUID, connector_id: uuid.UUID, api_key: str | None, config: dict | None
) -> OrgConnectorConfig:
    existing = await get_org_config(db, org_id, connector_id)
    if existing:
        existing.is_enabled = True
        if api_key is not None:
            existing.api_key_encrypted = api_key  # TODO: encrypt with AES-256-GCM
        if config is not None:
            existing.config = config
        await db.commit()
        await db.refresh(existing)
        return existing

    cfg = OrgConnectorConfig(
        org_id=org_id,
        connector_id=connector_id,
        is_enabled=True,
        api_key_encrypted=api_key,
        config=config or {},
    )
    db.add(cfg)
    await db.commit()
    await db.refresh(cfg)
    return cfg


async def disable_connector(db: AsyncSession, org_id: uuid.UUID, connector_id: uuid.UUID) -> None:
    cfg = await get_org_config(db, org_id, connector_id)
    if cfg:
        cfg.is_enabled = False
        await db.commit()


async def test_connector(db: AsyncSession, org_id: uuid.UUID, connector_id: uuid.UUID) -> dict[str, Any]:
    result = await db.execute(select(DataConnector).where(DataConnector.id == connector_id))
    connector_row = result.scalar_one_or_none()
    if not connector_row:
        raise ValueError("Connector not found")

    cfg = await get_org_config(db, org_id, connector_id)
    api_key = cfg.api_key_encrypted if cfg else None

    instance = _get_connector_instance(connector_row.name, api_key, cfg.config if cfg else {})
    try:
        result_data = await instance.test()
        # Log successful call
        db.add(DataFetchLog(
            org_id=org_id, connector_id=connector_id,
            endpoint="test", status_code=200, response_time_ms=0,
        ))
        await db.commit()
        return result_data
    except Exception as exc:
        db.add(DataFetchLog(
            org_id=org_id, connector_id=connector_id,
            endpoint="test", status_code=500, error_message=str(exc)[:500],
        ))
        await db.commit()
        raise


async def get_usage_stats(db: AsyncSession, org_id: uuid.UUID) -> list[dict[str, Any]]:
    from sqlalchemy import func
    result = await db.execute(
        select(
            DataFetchLog.connector_id,
            func.count(DataFetchLog.id).label("total_calls"),
            func.sum(func.case((DataFetchLog.status_code >= 400, 1), else_=0)).label("error_count"),
            func.avg(DataFetchLog.response_time_ms).label("avg_ms"),
        )
        .where(DataFetchLog.org_id == org_id)
        .group_by(DataFetchLog.connector_id)
    )
    return [{"connector_id": str(r.connector_id), "total_calls": r.total_calls,
             "error_count": r.error_count or 0, "avg_response_ms": float(r.avg_ms or 0)} for r in result.all()]
