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
    {
        "name": "irena",
        "display_name": "IRENA Renewable Energy Statistics",
        "category": "energy",
        "description": "International Renewable Energy Agency — global capacity, LCOE trends, and investment data.",
        "base_url": "https://www.irena.org/Data",
        "auth_type": "none",
        "pricing_tier": "free",
        "rate_limit_per_minute": 10,
        "documentation_url": "https://www.irena.org/Data",
    },
    {
        "name": "eu_ets",
        "display_name": "EU ETS / Ember Carbon Data",
        "category": "esg",
        "description": "European carbon market — EUA spot prices, carbon intensity, and power sector emissions via Ember.",
        "base_url": "https://api.ember-climate.org/v1",
        "auth_type": "api_key",
        "pricing_tier": "free",
        "rate_limit_per_minute": 60,
        "documentation_url": "https://ember-climate.org/data/apis/",
    },
    {
        "name": "alpha_vantage",
        "display_name": "Alpha Vantage",
        "category": "market_data",
        "description": "Commodity prices (WTI, Brent, natural gas, copper), sector ETFs, and VIX volatility index.",
        "base_url": "https://www.alphavantage.co/query",
        "auth_type": "api_key",
        "pricing_tier": "free",
        "rate_limit_per_minute": 5,
        "documentation_url": "https://www.alphavantage.co/documentation/",
    },
    {
        "name": "eurostat",
        "display_name": "Eurostat",
        "category": "market_data",
        "description": "EU economic and energy statistics — GDP, unemployment, renewable share, energy intensity.",
        "base_url": "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0",
        "auth_type": "none",
        "pricing_tier": "free",
        "rate_limit_per_minute": 60,
        "documentation_url": "https://wikis.ec.europa.eu/display/EUROSTATHELP/API+-+Getting+started+with+statistics+API",
    },
    {
        "name": "iea",
        "display_name": "International Energy Agency (IEA)",
        "category": "energy",
        "description": "Global clean energy investment, renewable deployment, EV sales, and net-zero scenarios.",
        "base_url": "https://api.iea.org",
        "auth_type": "api_key",
        "pricing_tier": "professional",
        "rate_limit_per_minute": 30,
        "documentation_url": "https://www.iea.org/data-and-statistics",
    },
    {
        "name": "sp_global",
        "display_name": "S&P Global Market Intelligence",
        "category": "esg",
        "description": "S&P Global ESG scores, credit ratings, probability of default, and GICS industry classifications.",
        "base_url": "https://api.spglobal.com/esg",
        "auth_type": "api_key",
        "pricing_tier": "enterprise",
        "rate_limit_per_minute": 60,
        "documentation_url": "https://www.spglobal.com/esg/solutions/data-intelligence-esg-scores",
    },
    {
        "name": "bnef",
        "display_name": "Bloomberg NEF",
        "category": "energy",
        "description": "Clean energy investment flows, corporate PPA prices, renewable auction results, and LCOE benchmarks.",
        "base_url": "https://api.bnef.com",
        "auth_type": "api_key",
        "pricing_tier": "enterprise",
        "rate_limit_per_minute": 30,
        "documentation_url": "https://about.bnef.com/bnef-data-services/",
    },
    {
        "name": "msci_esg",
        "display_name": "MSCI ESG Research",
        "category": "esg",
        "description": "MSCI ESG ratings (AAA-CCC), carbon intensity, climate Value-at-Risk, and implied temperature rise.",
        "base_url": "https://api.msci.com/esg",
        "auth_type": "api_key",
        "pricing_tier": "enterprise",
        "rate_limit_per_minute": 30,
        "documentation_url": "https://www.msci.com/our-solutions/esg-investing/esg-ratings-climate-search-tool",
    },
    {
        "name": "un_sdg",
        "display_name": "UN SDG Indicators",
        "category": "esg",
        "description": "United Nations Sustainable Development Goal metrics by country — SDG 7 (energy), SDG 13 (climate).",
        "base_url": "https://unstats.un.org/sdgs/UNSDGAPIV5/v1",
        "auth_type": "none",
        "pricing_tier": "free",
        "rate_limit_per_minute": 30,
        "documentation_url": "https://unstats.un.org/sdgs/UNSDGAPIV5/swagger/index.html",
    },
    {
        "name": "preqin",
        "display_name": "Preqin",
        "category": "market_data",
        "description": "Private markets benchmarks — infrastructure fund IRR, dry powder, deal volumes, and fundraising data.",
        "base_url": "https://api.preqin.com/v1",
        "auth_type": "api_key",
        "pricing_tier": "enterprise",
        "rate_limit_per_minute": 30,
        "documentation_url": "https://www.preqin.com/data",
    },
    {
        "name": "eia",
        "display_name": "US Energy Information Administration (EIA)",
        "category": "energy",
        "description": "US electricity generation by fuel type, capacity factors, and interconnection queue data.",
        "base_url": "https://api.eia.gov/v2",
        "auth_type": "api_key",
        "pricing_tier": "free",
        "rate_limit_per_minute": 60,
        "documentation_url": "https://www.eia.gov/opendata/documentation.php",
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
    from app.services.encryption import encrypt_field

    existing = await get_org_config(db, org_id, connector_id)
    if existing:
        existing.is_enabled = True
        if api_key is not None:
            existing.api_key_encrypted = encrypt_field(api_key)
        if config is not None:
            existing.config = config
        await db.commit()
        await db.refresh(existing)
        return existing

    cfg = OrgConnectorConfig(
        org_id=org_id,
        connector_id=connector_id,
        is_enabled=True,
        api_key_encrypted=encrypt_field(api_key),
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
    from app.services.encryption import decrypt_field
    api_key = decrypt_field(cfg.api_key_encrypted) if cfg else None

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


async def ingest_to_dataroom(
    db: AsyncSession,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    connector_id: uuid.UUID,
    project_id: uuid.UUID,
    endpoint: str,
    params: dict[str, Any] | None = None,
    folder_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Fetch data from a connector and store the result as a document in the dataroom.

    Returns {"document_id": str, "document_name": str, "file_size_bytes": int}.
    """
    import hashlib
    import json as _json
    from datetime import datetime as _dt

    import boto3
    from botocore.config import Config as BotoConfig

    from app.core.config import settings
    from app.models.dataroom import Document
    from app.models.enums import DocumentStatus

    # 1. Get connector row and org config
    result = await db.execute(select(DataConnector).where(DataConnector.id == connector_id))
    connector_row = result.scalar_one_or_none()
    if not connector_row:
        raise ValueError("Connector not found")

    cfg = await get_org_config(db, org_id, connector_id)
    if not cfg or not cfg.is_enabled:
        raise ValueError("Connector is not enabled for this organisation")

    from app.services.encryption import decrypt_field
    api_key = decrypt_field(cfg.api_key_encrypted) if cfg else None
    instance = _get_connector_instance(connector_row.name, api_key, cfg.config if cfg else {})

    # 2. Fetch data
    start_ts = _dt.utcnow()
    try:
        data = await instance.fetch(endpoint, params)
        elapsed_ms = int((_dt.utcnow() - start_ts).total_seconds() * 1000)
        db.add(DataFetchLog(
            org_id=org_id, connector_id=connector_id,
            endpoint=endpoint, status_code=200, response_time_ms=elapsed_ms,
        ))
    except Exception as exc:
        db.add(DataFetchLog(
            org_id=org_id, connector_id=connector_id,
            endpoint=endpoint, status_code=500, error_message=str(exc)[:500],
        ))
        await db.commit()
        raise RuntimeError(f"Connector fetch failed: {exc}") from exc

    # 3. Serialize to JSON bytes
    json_bytes = _json.dumps(data, indent=2, default=str).encode("utf-8")
    checksum = hashlib.sha256(json_bytes).hexdigest()
    timestamp = start_ts.strftime("%Y%m%d_%H%M%S")
    safe_endpoint = endpoint.strip("/").replace("/", "_")[:50]
    file_name = f"{connector_row.name}_{safe_endpoint}_{timestamp}.json"
    s3_key = f"connector-data/{org_id}/{connector_row.name}/{file_name}"

    # 4. Upload to S3
    s3_client = boto3.client(
        "s3",
        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION,
        config=BotoConfig(signature_version="s3v4"),
    )
    bucket = settings.AWS_S3_BUCKET
    try:
        s3_client.put_object(
            Bucket=bucket,
            Key=s3_key,
            Body=json_bytes,
            ContentType="application/json",
        )
    except Exception as exc:
        await db.commit()
        raise RuntimeError(f"S3 upload failed: {exc}") from exc

    # 5. Create document record
    doc = Document(
        org_id=org_id,
        project_id=project_id,
        folder_id=folder_id,
        name=file_name,
        file_type="json",
        mime_type="application/json",
        s3_key=s3_key,
        s3_bucket=bucket,
        file_size_bytes=len(json_bytes),
        status=DocumentStatus.READY,
        checksum_sha256=checksum,
        uploaded_by=user_id,
        metadata_={
            "source": "connector",
            "connector_id": str(connector_id),
            "connector_name": connector_row.name,
            "endpoint": endpoint,
            "params": params or {},
            "fetched_at": start_ts.isoformat(),
        },
    )
    db.add(doc)

    # 6. Update last_sync_at on config
    if cfg:
        cfg.last_sync_at = _dt.utcnow()
        cfg.total_calls_this_month = (cfg.total_calls_this_month or 0) + 1

    await db.commit()
    await db.refresh(doc)

    logger.info(
        "connector_ingest_complete",
        connector=connector_row.name,
        document_id=str(doc.id),
        file_size_bytes=len(json_bytes),
    )
    return {
        "document_id": str(doc.id),
        "document_name": file_name,
        "file_size_bytes": len(json_bytes),
        "s3_key": s3_key,
    }


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
