"""External data Celery tasks — fetch data from 14 new connectors and store as ExternalDataPoint records."""

from __future__ import annotations

import asyncio

import structlog
from celery import shared_task

logger = structlog.get_logger()


# ── Helper ────────────────────────────────────────────────────────────────────


async def _run_ingest(ingest_fn_name: str) -> dict:
    """Run a named ingest function from market_data.service within an async DB session."""
    from app.core.database import async_session_factory
    from app.modules.market_data import service

    fn = getattr(service, ingest_fn_name)
    async with async_session_factory() as db:
        rows = await fn(db)
    logger.info(f"external_data.{ingest_fn_name}.complete", rows=rows)
    return {"rows": rows, "source": ingest_fn_name}


# ── IRENA ─────────────────────────────────────────────────────────────────────


@shared_task(name="tasks.fetch_irena_data", bind=True, max_retries=3)
def fetch_irena_data(self) -> dict:  # type: ignore[type-arg]
    """Fetch IRENA global renewable energy statistics."""
    try:
        return asyncio.run(_run_ingest("ingest_irena_data"))
    except Exception as exc:
        logger.error("tasks.fetch_irena_data.failed", error=str(exc))
        raise self.retry(exc=exc, countdown=300) from exc


# ── EU ETS / Ember ─────────────────────────────────────────────────────────────


@shared_task(name="tasks.fetch_eu_ets_data", bind=True, max_retries=3)
def fetch_eu_ets_data(self) -> dict:  # type: ignore[type-arg]
    """Fetch EU ETS carbon price data from Ember."""
    try:
        return asyncio.run(_run_ingest("ingest_eu_ets_data"))
    except Exception as exc:
        logger.error("tasks.fetch_eu_ets_data.failed", error=str(exc))
        raise self.retry(exc=exc, countdown=300) from exc


# ── Companies House ────────────────────────────────────────────────────────────


@shared_task(name="tasks.fetch_companies_house_data", bind=True, max_retries=3)
def fetch_companies_house_data(self) -> dict:  # type: ignore[type-arg]
    """Fetch UK Companies House aggregate statistics."""
    try:
        return asyncio.run(_run_ingest("ingest_companies_house_data"))
    except Exception as exc:
        logger.error("tasks.fetch_companies_house_data.failed", error=str(exc))
        raise self.retry(exc=exc, countdown=300) from exc


# ── Alpha Vantage ──────────────────────────────────────────────────────────────


@shared_task(name="tasks.fetch_alpha_vantage_data", bind=True, max_retries=3)
def fetch_alpha_vantage_data(self) -> dict:  # type: ignore[type-arg]
    """Fetch commodity and ETF prices from Alpha Vantage."""
    try:
        return asyncio.run(_run_ingest("ingest_alpha_vantage_data"))
    except Exception as exc:
        logger.error("tasks.fetch_alpha_vantage_data.failed", error=str(exc))
        raise self.retry(exc=exc, countdown=300) from exc


# ── ENTSOE ─────────────────────────────────────────────────────────────────────


@shared_task(name="tasks.fetch_entsoe_data", bind=True, max_retries=3)
def fetch_entsoe_data(self) -> dict:  # type: ignore[type-arg]
    """Fetch ENTSOE European electricity market day-ahead prices."""
    try:
        return asyncio.run(_run_ingest("ingest_entsoe_data"))
    except Exception as exc:
        logger.error("tasks.fetch_entsoe_data.failed", error=str(exc))
        raise self.retry(exc=exc, countdown=300) from exc


# ── OpenWeather ────────────────────────────────────────────────────────────────


@shared_task(name="tasks.fetch_openweather_data", bind=True, max_retries=3)
def fetch_openweather_data(self) -> dict:  # type: ignore[type-arg]
    """Fetch OpenWeather data for European energy hub locations."""
    try:
        return asyncio.run(_run_ingest("ingest_openweather_data"))
    except Exception as exc:
        logger.error("tasks.fetch_openweather_data.failed", error=str(exc))
        raise self.retry(exc=exc, countdown=300) from exc


# ── Eurostat ───────────────────────────────────────────────────────────────────


@shared_task(name="tasks.fetch_eurostat_data", bind=True, max_retries=3)
def fetch_eurostat_data(self) -> dict:  # type: ignore[type-arg]
    """Fetch EU energy and economic statistics from Eurostat."""
    try:
        return asyncio.run(_run_ingest("ingest_eurostat_data"))
    except Exception as exc:
        logger.error("tasks.fetch_eurostat_data.failed", error=str(exc))
        raise self.retry(exc=exc, countdown=300) from exc


# ── IEA ───────────────────────────────────────────────────────────────────────


@shared_task(name="tasks.fetch_iea_data", bind=True, max_retries=3)
def fetch_iea_data(self) -> dict:  # type: ignore[type-arg]
    """Fetch IEA clean energy statistics."""
    try:
        return asyncio.run(_run_ingest("ingest_iea_data"))
    except Exception as exc:
        logger.error("tasks.fetch_iea_data.failed", error=str(exc))
        raise self.retry(exc=exc, countdown=300) from exc


# ── S&P Global ────────────────────────────────────────────────────────────────


@shared_task(name="tasks.fetch_sp_global_data", bind=True, max_retries=3)
def fetch_sp_global_data(self) -> dict:  # type: ignore[type-arg]
    """Fetch S&P Global ESG and credit data."""
    try:
        return asyncio.run(_run_ingest("ingest_sp_global_data"))
    except Exception as exc:
        logger.error("tasks.fetch_sp_global_data.failed", error=str(exc))
        raise self.retry(exc=exc, countdown=300) from exc


# ── BNEF ──────────────────────────────────────────────────────────────────────


@shared_task(name="tasks.fetch_bnef_data", bind=True, max_retries=3)
def fetch_bnef_data(self) -> dict:  # type: ignore[type-arg]
    """Fetch Bloomberg NEF clean energy market data."""
    try:
        return asyncio.run(_run_ingest("ingest_bnef_data"))
    except Exception as exc:
        logger.error("tasks.fetch_bnef_data.failed", error=str(exc))
        raise self.retry(exc=exc, countdown=300) from exc


# ── MSCI ESG ──────────────────────────────────────────────────────────────────


@shared_task(name="tasks.fetch_msci_esg_data", bind=True, max_retries=3)
def fetch_msci_esg_data(self) -> dict:  # type: ignore[type-arg]
    """Fetch MSCI ESG ratings and climate metrics."""
    try:
        return asyncio.run(_run_ingest("ingest_msci_esg_data"))
    except Exception as exc:
        logger.error("tasks.fetch_msci_esg_data.failed", error=str(exc))
        raise self.retry(exc=exc, countdown=300) from exc


# ── UN SDG ─────────────────────────────────────────────────────────────────────


@shared_task(name="tasks.fetch_un_sdg_data", bind=True, max_retries=3)
def fetch_un_sdg_data(self) -> dict:  # type: ignore[type-arg]
    """Fetch UN Sustainable Development Goal indicator data."""
    try:
        return asyncio.run(_run_ingest("ingest_un_sdg_data"))
    except Exception as exc:
        logger.error("tasks.fetch_un_sdg_data.failed", error=str(exc))
        raise self.retry(exc=exc, countdown=300) from exc


# ── Preqin ────────────────────────────────────────────────────────────────────


@shared_task(name="tasks.fetch_preqin_data", bind=True, max_retries=3)
def fetch_preqin_data(self) -> dict:  # type: ignore[type-arg]
    """Fetch Preqin private markets benchmark data."""
    try:
        return asyncio.run(_run_ingest("ingest_preqin_data"))
    except Exception as exc:
        logger.error("tasks.fetch_preqin_data.failed", error=str(exc))
        raise self.retry(exc=exc, countdown=300) from exc


# ── EIA ───────────────────────────────────────────────────────────────────────


@shared_task(name="tasks.fetch_eia_data", bind=True, max_retries=3)
def fetch_eia_data(self) -> dict:  # type: ignore[type-arg]
    """Fetch US EIA electricity generation data."""
    try:
        return asyncio.run(_run_ingest("ingest_eia_data"))
    except Exception as exc:
        logger.error("tasks.fetch_eia_data.failed", error=str(exc))
        raise self.retry(exc=exc, countdown=300) from exc
