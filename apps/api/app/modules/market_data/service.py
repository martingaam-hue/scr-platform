"""Market Data service — ingest public economic indicators, query historical series."""

from __future__ import annotations

import random
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

import httpx
import structlog
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.external_data import ExternalDataPoint
from app.modules.market_data.schemas import MarketDataSummary

logger = structlog.get_logger()

# ── FRED series to fetch ──────────────────────────────────────────────────────

FRED_SERIES: list[dict[str, str]] = [
    {"series_id": "DGS10",    "series_name": "10-Year Treasury Constant Maturity Rate", "unit": "percent"},
    {"series_id": "FEDFUNDS", "series_name": "Federal Funds Effective Rate",             "unit": "percent"},
    {"series_id": "UNRATE",   "series_name": "Unemployment Rate",                        "unit": "percent"},
    {"series_id": "CPIAUCSL", "series_name": "Consumer Price Index (All Urban)",          "unit": "index"},
    {"series_id": "SP500",    "series_name": "S&P 500 Index",                            "unit": "index"},
    {"series_id": "MORTGAGE30US", "series_name": "30-Year Fixed Rate Mortgage Average",  "unit": "percent"},
]

# ── World Bank indicators to fetch ───────────────────────────────────────────

WORLDBANK_INDICATORS: list[dict[str, str]] = [
    {"series_id": "NY.GDP.MKTP.KD.ZG", "series_name": "GDP Growth Rate (annual %)", "unit": "percent"},
    {"series_id": "FP.CPI.TOTL.ZG",    "series_name": "Inflation (CPI, annual %)",  "unit": "percent"},
    {"series_id": "SL.UEM.TOTL.ZS",    "series_name": "Unemployment, Total (% of labor force)", "unit": "percent"},
]
WORLDBANK_COUNTRIES = ["WLD", "US", "EU", "GB"]  # World, US, Euro area, UK


# ── Mock data helpers ─────────────────────────────────────────────────────────

_MOCK_BASE: dict[str, float] = {
    "DGS10":         4.25,
    "FEDFUNDS":      5.33,
    "UNRATE":        3.7,
    "CPIAUCSL":      312.0,
    "SP500":         5200.0,
    "MORTGAGE30US":  6.82,
}


def _mock_series(series_id: str, days: int = 90) -> list[dict[str, Any]]:
    """Generate plausible mock time-series for a FRED series."""
    base = _MOCK_BASE.get(series_id, 100.0)
    result = []
    today = date.today()
    value = base
    rng = random.Random(hash(series_id) & 0xFFFF)
    for i in range(days, 0, -1):
        d = today - timedelta(days=i)
        # Skip weekends for financial series
        if d.weekday() >= 5:
            continue
        drift = rng.gauss(0, base * 0.002)
        value = max(0, value + drift)
        result.append({"date": d, "value": round(value, 4)})
    return result


# ── Upsert helper ─────────────────────────────────────────────────────────────


async def _upsert_points(
    db: AsyncSession,
    source: str,
    series_id: str,
    series_name: str,
    unit: str,
    observations: list[dict[str, Any]],
) -> int:
    """Upsert observations for one series. Returns number of rows inserted/updated."""
    if not observations:
        return 0

    inserted = 0
    for obs in observations:
        obs_date = obs["date"] if isinstance(obs["date"], date) else date.fromisoformat(str(obs["date"]))
        raw_value = obs["value"]
        if raw_value is None:
            continue
        try:
            numeric_value = float(raw_value)
        except (TypeError, ValueError):
            continue

        stmt = (
            pg_insert(ExternalDataPoint)
            .values(
                source=source,
                series_id=series_id,
                series_name=series_name,
                data_date=obs_date,
                value=Decimal(str(round(numeric_value, 6))),
                unit=unit,
            )
            .on_conflict_do_update(
                constraint="uq_external_data_point",
                set_={"value": Decimal(str(round(numeric_value, 6))), "fetched_at": text("now()")},
            )
        )
        await db.execute(stmt)
        inserted += 1

    await db.commit()
    return inserted


# ── FRED ingestion ────────────────────────────────────────────────────────────


async def ingest_fred_data(db: AsyncSession) -> int:
    """Fetch FRED series and store. Falls back to mock data if no API key."""
    api_key: str = getattr(settings, "FRED_API_KEY", "")
    total = 0

    for series_meta in FRED_SERIES:
        sid = series_meta["series_id"]
        sname = series_meta["series_name"]
        unit = series_meta["unit"]

        if api_key:
            observations = await _fetch_fred_series(sid, api_key)
        else:
            logger.debug("market_data.fred.no_api_key_mock", series_id=sid)
            observations = _mock_series(sid, days=90)

        count = await _upsert_points(db, "fred", sid, sname, unit, observations)
        total += count
        logger.info("market_data.fred.ingested", series_id=sid, rows=count)

    return total


async def _fetch_fred_series(series_id: str, api_key: str) -> list[dict[str, Any]]:
    """Call the FRED API for the last 180 days of data."""
    observation_start = (date.today() - timedelta(days=180)).isoformat()
    url = (
        f"https://api.stlouisfed.org/fred/series/observations"
        f"?series_id={series_id}"
        f"&api_key={api_key}"
        f"&file_type=json"
        f"&observation_start={observation_start}"
    )
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        logger.warning("market_data.fred.fetch_error", series_id=series_id, error=str(exc))
        return _mock_series(series_id, days=90)

    observations = []
    for obs in data.get("observations", []):
        val_str = obs.get("value", ".")
        if val_str == ".":
            continue  # FRED uses "." for missing
        observations.append({"date": obs["date"], "value": val_str})
    return observations


# ── World Bank ingestion ──────────────────────────────────────────────────────


async def ingest_worldbank_data(db: AsyncSession) -> int:
    """Fetch World Bank annual indicators for key countries."""
    total = 0

    for indicator_meta in WORLDBANK_INDICATORS:
        ind_id = indicator_meta["series_id"]
        ind_name = indicator_meta["series_name"]
        unit = indicator_meta["unit"]

        for country in WORLDBANK_COUNTRIES:
            observations = await _fetch_worldbank_indicator(ind_id, country)
            if not observations:
                # Use simple mock: last 5 years of plausible annual data
                observations = _mock_worldbank(ind_id)

            series_id = f"{country}:{ind_id}"
            series_name = f"{ind_name} — {country}"
            count = await _upsert_points(db, "worldbank", series_id, series_name, unit, observations)
            total += count
            logger.info("market_data.worldbank.ingested", indicator=ind_id, country=country, rows=count)

    return total


async def _fetch_worldbank_indicator(indicator_id: str, country: str) -> list[dict[str, Any]]:
    """Call World Bank open API — no auth required."""
    url = (
        f"https://api.worldbank.org/v2/country/{country}/indicator/{indicator_id}"
        f"?format=json&mrv=5&per_page=5"
    )
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            payload = resp.json()
    except Exception as exc:
        logger.warning("market_data.worldbank.fetch_error", indicator=indicator_id, country=country, error=str(exc))
        return []

    if not isinstance(payload, list) or len(payload) < 2:
        return []

    observations = []
    for entry in payload[1] or []:
        year = entry.get("date")
        value = entry.get("value")
        if year and value is not None:
            # World Bank gives annual data; use Jan 1 of the year as the date
            obs_date = date(int(year), 1, 1)
            observations.append({"date": obs_date, "value": value})

    return observations


_MOCK_WB: dict[str, float] = {
    "NY.GDP.MKTP.KD.ZG": 2.5,
    "FP.CPI.TOTL.ZG":    3.2,
    "SL.UEM.TOTL.ZS":    5.1,
}


def _mock_worldbank(indicator_id: str) -> list[dict[str, Any]]:
    base = _MOCK_WB.get(indicator_id, 2.0)
    rng = random.Random(hash(indicator_id) & 0xFFFF)
    today = date.today()
    return [
        {"date": date(today.year - i, 1, 1), "value": round(base + rng.gauss(0, base * 0.15), 2)}
        for i in range(5, 0, -1)
    ]


# ── Query helpers ─────────────────────────────────────────────────────────────


async def get_series(
    db: AsyncSession,
    source: str,
    series_id: str,
    days: int = 90,
) -> list[ExternalDataPoint]:
    """Return historical data points for one series (last N days)."""
    cutoff = date.today() - timedelta(days=days)
    result = await db.execute(
        select(ExternalDataPoint)
        .where(
            ExternalDataPoint.source == source,
            ExternalDataPoint.series_id == series_id,
            ExternalDataPoint.data_date >= cutoff,
        )
        .order_by(ExternalDataPoint.data_date.asc())
    )
    return list(result.scalars().all())


async def list_series(db: AsyncSession) -> list[dict[str, Any]]:
    """Return distinct series grouped by source, with latest value."""
    # Use a subquery to get the most recent data_date per source+series_id
    stmt = text(
        """
        SELECT DISTINCT ON (source, series_id)
            source, series_id, series_name, unit, data_date, value
        FROM external_data_points
        ORDER BY source, series_id, data_date DESC
        """
    )
    result = await db.execute(stmt)
    rows = result.mappings().all()

    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        src = row["source"]
        grouped.setdefault(src, []).append(
            {
                "series_id": row["series_id"],
                "series_name": row["series_name"],
                "unit": row["unit"],
                "latest_date": row["data_date"].isoformat() if row["data_date"] else None,
                "latest_value": float(row["value"]),
            }
        )

    return [{"source": src, "series": series} for src, series in sorted(grouped.items())]


async def get_summary(db: AsyncSession) -> list[MarketDataSummary]:
    """Return latest value + change_pct for key FRED indicators."""
    key_series = [
        ("fred", "DGS10"),
        ("fred", "FEDFUNDS"),
        ("fred", "UNRATE"),
        ("fred", "CPIAUCSL"),
        ("fred", "SP500"),
        ("fred", "MORTGAGE30US"),
    ]

    summaries: list[MarketDataSummary] = []

    for source, sid in key_series:
        # Fetch last 2 data points to compute change
        result = await db.execute(
            select(ExternalDataPoint)
            .where(
                ExternalDataPoint.source == source,
                ExternalDataPoint.series_id == sid,
            )
            .order_by(ExternalDataPoint.data_date.desc())
            .limit(2)
        )
        rows = list(result.scalars().all())

        if not rows:
            continue

        latest = rows[0]
        prev = rows[1] if len(rows) > 1 else None

        change_pct: float | None = None
        if prev and float(prev.value) != 0:
            change_pct = round(
                (float(latest.value) - float(prev.value)) / abs(float(prev.value)) * 100, 4
            )

        summaries.append(
            MarketDataSummary(
                source=source,
                series_id=sid,
                series_name=latest.series_name,
                latest_date=latest.data_date,
                latest_value=float(latest.value),
                unit=latest.unit,
                change_pct=change_pct,
            )
        )

    return summaries
