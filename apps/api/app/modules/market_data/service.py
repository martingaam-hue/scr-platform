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


# ── IRENA ─────────────────────────────────────────────────────────────────────

IRENA_SERIES: list[dict[str, str]] = [
    {"series_id": "global_renewable_capacity_gw",  "series_name": "Global Installed Renewable Capacity (GW)", "unit": "gw"},
    {"series_id": "solar_pv_capacity_gw",          "series_name": "Global Solar PV Installed Capacity (GW)",  "unit": "gw"},
    {"series_id": "wind_capacity_gw",              "series_name": "Global Wind Power Installed Capacity (GW)", "unit": "gw"},
    {"series_id": "solar_lcoe_usd_kwh",            "series_name": "Utility-Scale Solar PV LCOE (USD/kWh)",    "unit": "usd_kwh"},
    {"series_id": "onshore_wind_lcoe_usd_kwh",     "series_name": "Onshore Wind LCOE (USD/kWh)",              "unit": "usd_kwh"},
]

_MOCK_IRENA: dict[str, float] = {
    "global_renewable_capacity_gw": 3382.0,
    "solar_pv_capacity_gw": 1177.0,
    "wind_capacity_gw": 899.0,
    "solar_lcoe_usd_kwh": 0.049,
    "onshore_wind_lcoe_usd_kwh": 0.033,
}


def _mock_irena_annual(series_id: str) -> list[dict[str, Any]]:
    base = _MOCK_IRENA.get(series_id, 100.0)
    rng = random.Random(hash("irena:" + series_id) & 0xFFFF)
    today = date.today()
    growth = -0.06 if "lcoe" in series_id else 0.10
    return [
        {
            "date": date(today.year - i, 12, 31),
            "value": round(base * (1 + growth) ** i * (1 + rng.gauss(0, 0.015)), 3),
        }
        for i in range(4, -1, -1)
    ]


async def ingest_irena_data(db: AsyncSession) -> int:
    """Fetch IRENA global renewable energy statistics (annual mock data until IRENASTAT API configured)."""
    total = 0
    for s in IRENA_SERIES:
        observations = _mock_irena_annual(s["series_id"])
        count = await _upsert_points(db, "irena", s["series_id"], s["series_name"], s["unit"], observations)
        total += count
        logger.info("market_data.irena.ingested", series_id=s["series_id"], rows=count)
    return total


# ── EU ETS / Ember ─────────────────────────────────────────────────────────────

EU_ETS_SERIES: list[dict[str, str]] = [
    {"series_id": "eua_price_eur",              "series_name": "EU Allowance Spot Price (EUR/tCO2)",          "unit": "eur_tco2"},
    {"series_id": "eu_carbon_intensity_gco2_kwh", "series_name": "EU Average Grid Carbon Intensity (gCO2/kWh)", "unit": "gco2_kwh"},
    {"series_id": "global_coal_share_pct",      "series_name": "Global Coal Share of Electricity (%)",        "unit": "percent"},
    {"series_id": "global_renewable_share_pct", "series_name": "Global Renewable Share of Electricity (%)",   "unit": "percent"},
]

_MOCK_EU_ETS: dict[str, float] = {
    "eua_price_eur": 62.5,
    "eu_carbon_intensity_gco2_kwh": 233.0,
    "global_coal_share_pct": 36.0,
    "global_renewable_share_pct": 30.0,
}


def _mock_eu_ets(series_id: str, days: int = 90) -> list[dict[str, Any]]:
    base = _MOCK_EU_ETS.get(series_id, 50.0)
    rng = random.Random(hash("eu_ets:" + series_id) & 0xFFFF)
    today = date.today()
    value = base
    result = []
    for i in range(days, 0, -1):
        d = today - timedelta(days=i)
        if d.weekday() >= 5:
            continue
        value = max(0.1, value + rng.gauss(0, base * 0.015))
        result.append({"date": d, "value": round(value, 4)})
    return result


async def ingest_eu_ets_data(db: AsyncSession) -> int:
    """Fetch EU ETS carbon price data. Falls back to mock if Ember API key not set."""
    api_key: str = getattr(settings, "EMBER_API_KEY", "")
    total = 0

    for s in EU_ETS_SERIES:
        if api_key and s["series_id"] == "eua_price_eur":
            observations = await _fetch_ember_carbon_price(api_key)
        else:
            observations = _mock_eu_ets(s["series_id"])

        count = await _upsert_points(db, "eu_ets", s["series_id"], s["series_name"], s["unit"], observations)
        total += count
        logger.info("market_data.eu_ets.ingested", series_id=s["series_id"], rows=count)

    return total


async def _fetch_ember_carbon_price(api_key: str) -> list[dict[str, Any]]:
    """Fetch EUA carbon price from Ember API."""
    url = "https://api.ember-climate.org/v1/carbon-price-data"
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(
                url,
                headers={"Authorization": f"Bearer {api_key}"},
                params={"format": "json", "limit": 90},
            )
            resp.raise_for_status()
            data = resp.json()
            observations = []
            for row in data.get("data", []):
                obs_date = date.fromisoformat(str(row.get("date", ""))[:10]) if row.get("date") else None
                value = row.get("price")
                if obs_date and value is not None:
                    observations.append({"date": obs_date, "value": value})
            return observations or _mock_eu_ets("eua_price_eur")
    except Exception as exc:
        logger.warning("market_data.eu_ets.fetch_error", error=str(exc))
        return _mock_eu_ets("eua_price_eur")


# ── Companies House ────────────────────────────────────────────────────────────

CH_SERIES: list[dict[str, str]] = [
    {"series_id": "uk_new_incorporations_monthly", "series_name": "UK New Company Incorporations (monthly)", "unit": "count"},
    {"series_id": "uk_dissolutions_monthly",       "series_name": "UK Company Dissolutions (monthly)",       "unit": "count"},
    {"series_id": "uk_active_companies_total",     "series_name": "UK Total Active Companies",               "unit": "count"},
]

_MOCK_CH: dict[str, float] = {
    "uk_new_incorporations_monthly": 65000.0,
    "uk_dissolutions_monthly": 15000.0,
    "uk_active_companies_total": 5_100_000.0,
}


def _mock_companies_house(series_id: str) -> list[dict[str, Any]]:
    base = _MOCK_CH.get(series_id, 50000.0)
    rng = random.Random(hash("ch:" + series_id) & 0xFFFF)
    today = date.today()
    return [
        {
            "date": date(today.year, today.month - i if today.month > i else today.month + 12 - i,
                         1) if today.month > i else date(today.year - 1, today.month + 12 - i, 1),
            "value": round(base * (1 + rng.gauss(0, 0.08)), 0),
        }
        for i in range(11, -1, -1)
    ]


async def ingest_companies_house_data(db: AsyncSession) -> int:
    """Fetch UK corporate formation statistics from Companies House."""
    api_key: str = getattr(settings, "COMPANIES_HOUSE_API_KEY", "")
    total = 0

    for s in CH_SERIES:
        if api_key:
            observations = await _fetch_ch_stats(api_key, s["series_id"])
        else:
            observations = _mock_companies_house(s["series_id"])

        count = await _upsert_points(db, "companies_house", s["series_id"], s["series_name"], s["unit"], observations)
        total += count
        logger.info("market_data.companies_house.ingested", series_id=s["series_id"], rows=count)

    return total


async def _fetch_ch_stats(api_key: str, series_id: str) -> list[dict[str, Any]]:
    """Fetch Companies House filing statistics."""
    import base64

    encoded_key = base64.b64encode(f"{api_key}:".encode()).decode()
    url = "https://api.company-information.service.gov.uk/company"
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(
                url,
                params={"q": "incorporated", "items_per_page": 1},
                headers={"Authorization": f"Basic {encoded_key}"},
            )
            resp.raise_for_status()
            data = resp.json()
            total_results = data.get("total_results", 0)
            if total_results:
                today = date.today()
                return [{"date": date(today.year, today.month, 1), "value": total_results}]
            return _mock_companies_house(series_id)
    except Exception as exc:
        logger.warning("market_data.companies_house.fetch_error", error=str(exc))
        return _mock_companies_house(series_id)


# ── Alpha Vantage ──────────────────────────────────────────────────────────────

AV_SERIES: list[dict[str, str]] = [
    {"series_id": "WTI",    "series_name": "WTI Crude Oil Price (USD/barrel)", "unit": "usd_barrel"},
    {"series_id": "BRENT",  "series_name": "Brent Crude Oil Price (USD/barrel)", "unit": "usd_barrel"},
    {"series_id": "NATURAL_GAS", "series_name": "Henry Hub Natural Gas (USD/MMBtu)", "unit": "usd_mmbtu"},
    {"series_id": "COPPER", "series_name": "Copper Price (USD/lb)",            "unit": "usd_lb"},
    {"series_id": "XLE",    "series_name": "Energy Select Sector ETF (USD)",   "unit": "usd"},
    {"series_id": "ICLN",   "series_name": "iShares Global Clean Energy ETF (USD)", "unit": "usd"},
    {"series_id": "VIX",    "series_name": "CBOE Volatility Index",            "unit": "index"},
]

_MOCK_AV: dict[str, float] = {
    "WTI": 78.5, "BRENT": 82.3, "NATURAL_GAS": 2.45, "COPPER": 4.15,
    "XLE": 91.0, "ICLN": 14.2, "VIX": 18.5,
}

# AV commodity function mapping
_AV_COMMODITY_FUNCTIONS: dict[str, str] = {
    "WTI": "WTI", "BRENT": "BRENT", "NATURAL_GAS": "NATURAL_GAS", "COPPER": "COPPER",
}
_AV_QUOTE_SYMBOLS: dict[str, str] = {
    "XLE": "XLE", "ICLN": "ICLN", "VIX": "^VIX",
}


def _mock_av(series_id: str, days: int = 90) -> list[dict[str, Any]]:
    base = _MOCK_AV.get(series_id, 50.0)
    rng = random.Random(hash("av:" + series_id) & 0xFFFF)
    today = date.today()
    value = base
    result = []
    for i in range(days, 0, -1):
        d = today - timedelta(days=i)
        if d.weekday() >= 5:
            continue
        value = max(0.01, value + rng.gauss(0, base * 0.012))
        result.append({"date": d, "value": round(value, 4)})
    return result


async def ingest_alpha_vantage_data(db: AsyncSession) -> int:
    """Fetch commodity and ETF prices from Alpha Vantage. Falls back to mock if no API key."""
    api_key: str = getattr(settings, "ALPHA_VANTAGE_API_KEY", "")
    total = 0

    for s in AV_SERIES:
        if api_key:
            observations = await _fetch_av_series(s["series_id"], api_key)
        else:
            logger.debug("market_data.alpha_vantage.no_api_key_mock", series_id=s["series_id"])
            observations = _mock_av(s["series_id"])

        count = await _upsert_points(db, "alpha_vantage", s["series_id"], s["series_name"], s["unit"], observations)
        total += count
        logger.info("market_data.alpha_vantage.ingested", series_id=s["series_id"], rows=count)

    return total


async def _fetch_av_series(series_id: str, api_key: str) -> list[dict[str, Any]]:
    """Fetch a single Alpha Vantage commodity or global quote."""
    base_url = "https://www.alphavantage.co/query"
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            if series_id in _AV_COMMODITY_FUNCTIONS:
                resp = await client.get(base_url, params={
                    "function": series_id, "interval": "monthly", "apikey": api_key,
                })
                resp.raise_for_status()
                data = resp.json()
                rows = data.get("data", [])
                return [
                    {"date": date.fromisoformat(r["date"]), "value": float(r["value"])}
                    for r in rows[:90]
                    if r.get("value") not in (None, ".", "")
                ]
            else:
                symbol = _AV_QUOTE_SYMBOLS.get(series_id, series_id)
                resp = await client.get(base_url, params={
                    "function": "GLOBAL_QUOTE", "symbol": symbol, "apikey": api_key,
                })
                resp.raise_for_status()
                data = resp.json()
                quote = data.get("Global Quote", {})
                price = quote.get("05. price")
                if price:
                    return [{"date": date.today(), "value": float(price)}]
                return _mock_av(series_id)
    except Exception as exc:
        logger.warning("market_data.alpha_vantage.fetch_error", series_id=series_id, error=str(exc))
        return _mock_av(series_id)


# ── ENTSOE ─────────────────────────────────────────────────────────────────────

ENTSOE_SERIES: list[dict[str, str]] = [
    {"series_id": "day_ahead_price_de",  "series_name": "Germany Day-Ahead Electricity Price (EUR/MWh)", "unit": "eur_mwh"},
    {"series_id": "day_ahead_price_fr",  "series_name": "France Day-Ahead Electricity Price (EUR/MWh)",  "unit": "eur_mwh"},
    {"series_id": "day_ahead_price_es",  "series_name": "Spain Day-Ahead Electricity Price (EUR/MWh)",   "unit": "eur_mwh"},
    {"series_id": "day_ahead_price_gb",  "series_name": "GB Day-Ahead Electricity Price (GBP/MWh)",      "unit": "gbp_mwh"},
    {"series_id": "day_ahead_price_nl",  "series_name": "Netherlands Day-Ahead Electricity Price (EUR/MWh)", "unit": "eur_mwh"},
]

_MOCK_ENTSOE: dict[str, float] = {
    "day_ahead_price_de": 95.0, "day_ahead_price_fr": 92.0, "day_ahead_price_es": 88.0,
    "day_ahead_price_gb": 85.0, "day_ahead_price_nl": 96.0,
}

# ENTSOE bidding zone EIC codes
_ENTSOE_ZONES: dict[str, str] = {
    "day_ahead_price_de": "10Y1001A1001A63L",  # DE-LU
    "day_ahead_price_fr": "10YFR-RTE------C",
    "day_ahead_price_es": "10YES-REE------0",
    "day_ahead_price_gb": "10YGB----------A",
    "day_ahead_price_nl": "10YNL----------L",
}


def _mock_entsoe(series_id: str, days: int = 30) -> list[dict[str, Any]]:
    base = _MOCK_ENTSOE.get(series_id, 90.0)
    rng = random.Random(hash("entsoe:" + series_id) & 0xFFFF)
    today = date.today()
    value = base
    result = []
    for i in range(days, 0, -1):
        d = today - timedelta(days=i)
        value = max(0.0, value + rng.gauss(0, base * 0.05))
        result.append({"date": d, "value": round(value, 2)})
    return result


async def ingest_entsoe_data(db: AsyncSession) -> int:
    """Fetch ENTSOE day-ahead electricity prices for European bidding zones."""
    api_key: str = getattr(settings, "ENTSOE_API_KEY", "")
    total = 0

    for s in ENTSOE_SERIES:
        if api_key:
            observations = await _fetch_entsoe_prices(api_key, s["series_id"], _ENTSOE_ZONES[s["series_id"]])
        else:
            logger.debug("market_data.entsoe.no_api_key_mock", series_id=s["series_id"])
            observations = _mock_entsoe(s["series_id"])

        count = await _upsert_points(db, "entsoe", s["series_id"], s["series_name"], s["unit"], observations)
        total += count
        logger.info("market_data.entsoe.ingested", series_id=s["series_id"], rows=count)

    return total


async def _fetch_entsoe_prices(api_key: str, series_id: str, in_domain: str) -> list[dict[str, Any]]:
    """Fetch ENTSOE day-ahead prices via transparency REST API (XML format)."""
    import xml.etree.ElementTree as ET

    period_start = (date.today() - timedelta(days=7)).strftime("%Y%m%d0000")
    period_end = date.today().strftime("%Y%m%d2300")

    url = "https://web-api.tp.entsoe.eu/api"
    params = {
        "securityToken": api_key,
        "documentType": "A44",
        "in_Domain": in_domain,
        "out_Domain": in_domain,
        "periodStart": period_start,
        "periodEnd": period_end,
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            root = ET.fromstring(resp.text)
            ns = {"ns": "urn:iec62325.351:tc57wg16:451-3:publicationdocument:7:0"}

            observations: list[dict[str, Any]] = []
            for point in root.findall(".//ns:Point", ns):
                pos = point.findtext("ns:position", namespaces=ns)
                price = point.findtext("ns:price.amount", namespaces=ns)
                if pos and price:
                    obs_date = date.today() - timedelta(days=7) + timedelta(hours=int(pos) - 1)
                    observations.append({"date": obs_date.date() if hasattr(obs_date, "date") else obs_date, "value": float(price)})

            return observations or _mock_entsoe(series_id)
    except Exception as exc:
        logger.warning("market_data.entsoe.fetch_error", series_id=series_id, error=str(exc))
        return _mock_entsoe(series_id)


# ── OpenWeather ────────────────────────────────────────────────────────────────

# Pre-defined European energy hub locations
OW_LOCATIONS: list[dict[str, Any]] = [
    {"series_id": "berlin_de",    "series_name": "Berlin, Germany",     "lat": 52.52,  "lon": 13.40},
    {"series_id": "madrid_es",    "series_name": "Madrid, Spain",       "lat": 40.42,  "lon": -3.70},
    {"series_id": "london_gb",    "series_name": "London, UK",          "lat": 51.51,  "lon": -0.13},
    {"series_id": "amsterdam_nl", "series_name": "Amsterdam, NL",       "lat": 52.37,  "lon": 4.90},
    {"series_id": "oslo_no",      "series_name": "Oslo, Norway",        "lat": 59.91,  "lon": 10.75},
]

OW_INDICATORS: list[dict[str, str]] = [
    {"indicator": "wind_speed_ms", "series_name_suffix": "Wind Speed (m/s)",     "unit": "ms"},
    {"indicator": "temperature_c", "series_name_suffix": "Temperature (°C)",      "unit": "celsius"},
    {"indicator": "cloud_cover_pct", "series_name_suffix": "Cloud Cover (%)",     "unit": "percent"},
]


def _mock_openweather(series_id: str, indicator: str) -> list[dict[str, Any]]:
    bases = {"wind_speed_ms": 6.5, "temperature_c": 12.0, "cloud_cover_pct": 55.0}
    base = bases.get(indicator, 10.0)
    rng = random.Random(hash(f"ow:{series_id}:{indicator}") & 0xFFFF)
    today = date.today()
    return [
        {"date": today - timedelta(days=i), "value": round(base + rng.gauss(0, base * 0.15), 2)}
        for i in range(14, 0, -1)
    ]


async def ingest_openweather_data(db: AsyncSession) -> int:
    """Fetch current weather for European energy hub locations via OpenWeather."""
    api_key: str = getattr(settings, "OPENWEATHER_API_KEY", "")
    total = 0

    for loc in OW_LOCATIONS:
        for ind in OW_INDICATORS:
            series_id = f"{loc['series_id']}_{ind['indicator']}"
            series_name = f"{loc['series_name']} — {ind['series_name_suffix']}"

            if api_key:
                observations = await _fetch_openweather_point(api_key, loc["lat"], loc["lon"], ind["indicator"])
            else:
                observations = _mock_openweather(loc["series_id"], ind["indicator"])

            count = await _upsert_points(db, "openweather", series_id, series_name, ind["unit"], observations)
            total += count

    logger.info("market_data.openweather.ingested", rows=total)
    return total


async def _fetch_openweather_point(api_key: str, lat: float, lon: float, indicator: str) -> list[dict[str, Any]]:
    """Fetch current weather for a location from OpenWeather API."""
    url = "https://api.openweathermap.org/data/2.5/weather"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, params={"lat": lat, "lon": lon, "appid": api_key, "units": "metric"})
            resp.raise_for_status()
            data = resp.json()
            value: float | None = None
            if indicator == "wind_speed_ms":
                value = data.get("wind", {}).get("speed")
            elif indicator == "temperature_c":
                value = data.get("main", {}).get("temp")
            elif indicator == "cloud_cover_pct":
                value = data.get("clouds", {}).get("all")
            if value is not None:
                return [{"date": date.today(), "value": float(value)}]
            return []
    except Exception as exc:
        logger.warning("market_data.openweather.fetch_error", error=str(exc))
        return []


# ── Eurostat ───────────────────────────────────────────────────────────────────

EUROSTAT_SERIES: list[dict[str, str]] = [
    {"series_id": "eu_renewable_share_pct",        "series_name": "EU Renewable Share of Gross Final Energy (%)", "unit": "percent"},
    {"series_id": "eu_gdp_growth_pct",             "series_name": "EU GDP Growth Rate (%)",                       "unit": "percent"},
    {"series_id": "eu_unemployment_pct",           "series_name": "EU Unemployment Rate (%)",                     "unit": "percent"},
    {"series_id": "eu_energy_intensity_toe_keur",  "series_name": "EU Energy Intensity (toe per €1000 GDP)",      "unit": "toe_keur"},
    {"series_id": "eu_co2_emissions_index",        "series_name": "EU Greenhouse Gas Emissions Index (2005=100)",  "unit": "index"},
]

# Eurostat dataset codes
_EUROSTAT_DATASETS: dict[str, tuple[str, dict[str, str]]] = {
    "eu_renewable_share_pct":        ("nrg_ind_ren",  {"unit": "PC", "nrg_bal": "REN", "geo": "EU27_2020"}),
    "eu_gdp_growth_pct":             ("tec00115",     {"unit": "PCH_PRE_PER", "geo": "EU27_2020"}),
    "eu_unemployment_pct":           ("une_rt_m",     {"unit": "PC_ACT", "s_adj": "NSA", "age": "TOTAL", "sex": "T", "geo": "EU27_2020"}),
    "eu_energy_intensity_toe_keur":  ("nrg_ind_ei",   {"unit": "KTOE_KEUR", "geo": "EU27_2020"}),
    "eu_co2_emissions_index":        ("t2020_30",     {"unit": "INX_2005_100", "geo": "EU27_2020"}),
}

_MOCK_EUROSTAT: dict[str, float] = {
    "eu_renewable_share_pct": 22.5,
    "eu_gdp_growth_pct": 1.2,
    "eu_unemployment_pct": 6.0,
    "eu_energy_intensity_toe_keur": 0.08,
    "eu_co2_emissions_index": 63.0,
}


def _mock_eurostat_annual(series_id: str) -> list[dict[str, Any]]:
    base = _MOCK_EUROSTAT.get(series_id, 5.0)
    rng = random.Random(hash("eurostat:" + series_id) & 0xFFFF)
    today = date.today()
    trend = 0.02 if "renewable" in series_id else -0.01 if "co2" in series_id or "intensity" in series_id else 0.0
    return [
        {
            "date": date(today.year - i, 12, 31),
            "value": round(base * (1 + trend) ** i * (1 + rng.gauss(0, 0.03)), 4),
        }
        for i in range(4, -1, -1)
    ]


async def ingest_eurostat_data(db: AsyncSession) -> int:
    """Fetch EU energy and economic statistics from Eurostat (public API, no key needed)."""
    total = 0

    for s in EUROSTAT_SERIES:
        observations = await _fetch_eurostat_indicator(s["series_id"])
        if not observations:
            observations = _mock_eurostat_annual(s["series_id"])

        count = await _upsert_points(db, "eurostat", s["series_id"], s["series_name"], s["unit"], observations)
        total += count
        logger.info("market_data.eurostat.ingested", series_id=s["series_id"], rows=count)

    return total


async def _fetch_eurostat_indicator(series_id: str) -> list[dict[str, Any]]:
    """Fetch an indicator from the Eurostat REST API."""
    dataset_info = _EUROSTAT_DATASETS.get(series_id)
    if not dataset_info:
        return []
    dataset_code, params = dataset_info
    url = f"https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/{dataset_code}"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, params={"format": "JSON", "lang": "EN", **params})
            resp.raise_for_status()
            data = resp.json()
            values = data.get("value", {})
            dimension = data.get("dimension", {})
            time_dim = dimension.get("time", {}).get("category", {}).get("index", {})
            observations = []
            for time_str, idx in sorted(time_dim.items()):
                val = values.get(str(idx))
                if val is not None:
                    try:
                        year = int(time_str[:4])
                        obs_date = date(year, 12, 31)
                        observations.append({"date": obs_date, "value": float(val)})
                    except (ValueError, TypeError):
                        continue
            return observations
    except Exception as exc:
        logger.warning("market_data.eurostat.fetch_error", series_id=series_id, error=str(exc))
        return []


# ── IEA ───────────────────────────────────────────────────────────────────────

IEA_SERIES: list[dict[str, str]] = [
    {"series_id": "global_clean_energy_investment_bn_usd", "series_name": "Global Clean Energy Investment ($bn)",      "unit": "bn_usd"},
    {"series_id": "global_renewable_capacity_additions_gw", "series_name": "Global Renewable Capacity Additions (GW)", "unit": "gw"},
    {"series_id": "global_ev_sales_millions",              "series_name": "Global Electric Vehicle Sales (millions)",  "unit": "millions"},
    {"series_id": "fossil_fuel_subsidies_bn_usd",          "series_name": "Global Fossil Fuel Subsidies ($bn)",        "unit": "bn_usd"},
]

_MOCK_IEA: dict[str, float] = {
    "global_clean_energy_investment_bn_usd": 1740.0,
    "global_renewable_capacity_additions_gw": 295.0,
    "global_ev_sales_millions": 10.5,
    "fossil_fuel_subsidies_bn_usd": 7000.0,
}


def _mock_iea_annual(series_id: str) -> list[dict[str, Any]]:
    base = _MOCK_IEA.get(series_id, 100.0)
    rng = random.Random(hash("iea:" + series_id) & 0xFFFF)
    today = date.today()
    growth = 0.12 if "clean_energy" in series_id or "ev" in series_id or "renewable" in series_id else -0.04
    return [
        {
            "date": date(today.year - i, 12, 31),
            "value": round(base * (1 - growth) ** i * (1 + rng.gauss(0, 0.05)), 2),
        }
        for i in range(4, -1, -1)
    ]


async def ingest_iea_data(db: AsyncSession) -> int:
    """Fetch IEA clean energy statistics (mock until IEA API key configured)."""
    total = 0
    for s in IEA_SERIES:
        observations = _mock_iea_annual(s["series_id"])
        count = await _upsert_points(db, "iea", s["series_id"], s["series_name"], s["unit"], observations)
        total += count
        logger.info("market_data.iea.ingested", series_id=s["series_id"], rows=count)
    return total


# ── S&P Global ────────────────────────────────────────────────────────────────

SP_SERIES: list[dict[str, str]] = [
    {"series_id": "sp500_esg_score_avg",          "series_name": "S&P 500 Average ESG Score",              "unit": "score"},
    {"series_id": "infra_sector_esg_score",       "series_name": "Infrastructure Sector ESG Score",        "unit": "score"},
    {"series_id": "renewable_energy_credit_avg",  "series_name": "Renewable Energy Credit Average Score",  "unit": "score"},
    {"series_id": "probability_of_default_bb_pct", "series_name": "BB-Rated Prob. of Default 1Y (%)",     "unit": "percent"},
]

_MOCK_SP: dict[str, float] = {
    "sp500_esg_score_avg": 54.0,
    "infra_sector_esg_score": 61.0,
    "renewable_energy_credit_avg": 68.0,
    "probability_of_default_bb_pct": 1.2,
}


def _mock_sp_annual(series_id: str) -> list[dict[str, Any]]:
    base = _MOCK_SP.get(series_id, 50.0)
    rng = random.Random(hash("sp:" + series_id) & 0xFFFF)
    today = date.today()
    return [
        {"date": date(today.year - i, 12, 31), "value": round(base + rng.gauss(0, base * 0.05), 2)}
        for i in range(4, -1, -1)
    ]


async def ingest_sp_global_data(db: AsyncSession) -> int:
    """Fetch S&P Global ESG scores (mock until subscription API key configured)."""
    # S&P Global Market Intelligence requires a paid subscription
    api_key: str = getattr(settings, "SP_GLOBAL_API_KEY", "")
    if api_key:
        logger.info("market_data.sp_global.subscription_key_set_but_not_implemented")

    total = 0
    for s in SP_SERIES:
        observations = _mock_sp_annual(s["series_id"])
        count = await _upsert_points(db, "sp_global", s["series_id"], s["series_name"], s["unit"], observations)
        total += count
        logger.info("market_data.sp_global.ingested", series_id=s["series_id"], rows=count)
    return total


# ── BNEF ──────────────────────────────────────────────────────────────────────

BNEF_SERIES: list[dict[str, str]] = [
    {"series_id": "global_clean_energy_investment_bn_usd", "series_name": "BNEF Global Clean Energy Investment ($bn)", "unit": "bn_usd"},
    {"series_id": "corporate_ppa_price_usd_mwh",          "series_name": "Corporate PPA Average Price (USD/MWh)",     "unit": "usd_mwh"},
    {"series_id": "solar_auction_price_usd_mwh",          "series_name": "Solar Auction Clearing Price (USD/MWh)",    "unit": "usd_mwh"},
    {"series_id": "wind_auction_price_usd_mwh",           "series_name": "Wind Auction Clearing Price (USD/MWh)",     "unit": "usd_mwh"},
    {"series_id": "lcoe_solar_utility_usd_mwh",           "series_name": "BNEF Solar LCOE Benchmark (USD/MWh)",       "unit": "usd_mwh"},
    {"series_id": "lcoe_wind_onshore_usd_mwh",            "series_name": "BNEF Onshore Wind LCOE Benchmark (USD/MWh)", "unit": "usd_mwh"},
]

_MOCK_BNEF: dict[str, float] = {
    "global_clean_energy_investment_bn_usd": 1740.0,
    "corporate_ppa_price_usd_mwh": 42.0,
    "solar_auction_price_usd_mwh": 31.0,
    "wind_auction_price_usd_mwh": 38.0,
    "lcoe_solar_utility_usd_mwh": 49.0,
    "lcoe_wind_onshore_usd_mwh": 33.0,
}


def _mock_bnef_annual(series_id: str) -> list[dict[str, Any]]:
    base = _MOCK_BNEF.get(series_id, 50.0)
    rng = random.Random(hash("bnef:" + series_id) & 0xFFFF)
    today = date.today()
    trend = 0.15 if "investment" in series_id else -0.08
    return [
        {
            "date": date(today.year - i, 12, 31),
            "value": round(base * (1 - trend) ** i * (1 + rng.gauss(0, 0.04)), 2),
        }
        for i in range(4, -1, -1)
    ]


async def ingest_bnef_data(db: AsyncSession) -> int:
    """Fetch BNEF clean energy market data (mock until Bloomberg NEF API key configured)."""
    api_key: str = getattr(settings, "BNEF_API_KEY", "")
    if api_key:
        logger.info("market_data.bnef.subscription_key_set_but_not_implemented")

    total = 0
    for s in BNEF_SERIES:
        observations = _mock_bnef_annual(s["series_id"])
        count = await _upsert_points(db, "bnef", s["series_id"], s["series_name"], s["unit"], observations)
        total += count
        logger.info("market_data.bnef.ingested", series_id=s["series_id"], rows=count)
    return total


# ── MSCI ESG ──────────────────────────────────────────────────────────────────

MSCI_SERIES: list[dict[str, str]] = [
    {"series_id": "infra_sector_esg_score",       "series_name": "MSCI Infrastructure Sector ESG Score (0-10)", "unit": "score"},
    {"series_id": "renewable_energy_esg_score",   "series_name": "MSCI Renewable Energy ESG Score (0-10)",      "unit": "score"},
    {"series_id": "infra_carbon_intensity_avg",   "series_name": "Infra Sector Avg Carbon Intensity (tCO2/$M)", "unit": "tco2_musd"},
    {"series_id": "implied_temp_rise_infra_c",    "series_name": "Infrastructure Sector Implied Temperature Rise (°C)", "unit": "celsius"},
    {"series_id": "climate_var_infra_pct",        "series_name": "Infrastructure Climate Value-at-Risk (%)",    "unit": "percent"},
]

_MOCK_MSCI: dict[str, float] = {
    "infra_sector_esg_score": 6.2,
    "renewable_energy_esg_score": 7.8,
    "infra_carbon_intensity_avg": 125.0,
    "implied_temp_rise_infra_c": 2.4,
    "climate_var_infra_pct": -8.5,
}


def _mock_msci_annual(series_id: str) -> list[dict[str, Any]]:
    base = _MOCK_MSCI.get(series_id, 5.0)
    rng = random.Random(hash("msci:" + series_id) & 0xFFFF)
    today = date.today()
    trend = 0.03 if "esg" in series_id else -0.04 if "carbon" in series_id or "temp" in series_id else 0.0
    return [
        {"date": date(today.year - i, 12, 31), "value": round(base * (1 + trend * i) * (1 + rng.gauss(0, 0.03)), 3)}
        for i in range(4, -1, -1)
    ]


async def ingest_msci_esg_data(db: AsyncSession) -> int:
    """Fetch MSCI ESG ratings and climate metrics (mock until MSCI ESG API key configured)."""
    api_key: str = getattr(settings, "MSCI_ESG_API_KEY", "")
    if api_key:
        logger.info("market_data.msci_esg.subscription_key_set_but_not_implemented")

    total = 0
    for s in MSCI_SERIES:
        observations = _mock_msci_annual(s["series_id"])
        count = await _upsert_points(db, "msci_esg", s["series_id"], s["series_name"], s["unit"], observations)
        total += count
        logger.info("market_data.msci_esg.ingested", series_id=s["series_id"], rows=count)
    return total


# ── UN SDG ─────────────────────────────────────────────────────────────────────

UN_SDG_SERIES: list[dict[str, str]] = [
    {"series_id": "7.2.1_renewable_share_pct",    "series_name": "SDG 7.2.1 Renewable Energy Share (%)",        "unit": "percent"},
    {"series_id": "7.3.1_energy_intensity",       "series_name": "SDG 7.3.1 Energy Intensity (MJ/$2017 GDP)",   "unit": "mj_gdp"},
    {"series_id": "9.4.1_co2_per_gdp",            "series_name": "SDG 9.4.1 CO2 Emissions per unit GDP",        "unit": "kgco2_gdp"},
    {"series_id": "13.a.1_climate_finance_bn_usd","series_name": "SDG 13.a.1 Climate Finance Mobilized ($bn)",  "unit": "bn_usd"},
]

_MOCK_UN_SDG: dict[str, float] = {
    "7.2.1_renewable_share_pct": 19.1,
    "7.3.1_energy_intensity": 4.7,
    "9.4.1_co2_per_gdp": 0.28,
    "13.a.1_climate_finance_bn_usd": 83.3,
}


def _mock_un_sdg_annual(series_id: str) -> list[dict[str, Any]]:
    base = _MOCK_UN_SDG.get(series_id, 10.0)
    rng = random.Random(hash("unsdg:" + series_id) & 0xFFFF)
    today = date.today()
    trend = 0.03 if "renewable" in series_id or "finance" in series_id else -0.02
    return [
        {
            "date": date(today.year - i, 12, 31),
            "value": round(base * (1 + trend) ** (4 - i) * (1 + rng.gauss(0, 0.03)), 3),
        }
        for i in range(4, -1, -1)
    ]


async def ingest_un_sdg_data(db: AsyncSession) -> int:
    """Fetch UN SDG indicator data (public API, no key required)."""
    total = 0

    for s in UN_SDG_SERIES:
        indicator_code = s["series_id"].split("_")[0]
        observations = await _fetch_un_sdg_indicator(indicator_code)
        if not observations:
            observations = _mock_un_sdg_annual(s["series_id"])

        count = await _upsert_points(db, "un_sdg", s["series_id"], s["series_name"], s["unit"], observations)
        total += count
        logger.info("market_data.un_sdg.ingested", series_id=s["series_id"], rows=count)

    return total


async def _fetch_un_sdg_indicator(indicator_code: str) -> list[dict[str, Any]]:
    """Fetch a UN SDG indicator from the official REST API."""
    url = "https://unstats.un.org/sdgs/UNSDGAPIV5/v1/sdg/Indicator/Data"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, params={"indicator": indicator_code, "areaCode": "WORLD", "limit": 10})
            resp.raise_for_status()
            data = resp.json()
            observations = []
            for item in data.get("data", []):
                year = item.get("timePeriodStart")
                value = item.get("value")
                if year and value not in (None, "", "N"):
                    try:
                        obs_date = date(int(year), 12, 31)
                        observations.append({"date": obs_date, "value": float(value)})
                    except (ValueError, TypeError):
                        continue
            return sorted(observations, key=lambda x: x["date"])
    except Exception as exc:
        logger.warning("market_data.un_sdg.fetch_error", indicator=indicator_code, error=str(exc))
        return []


# ── Preqin ────────────────────────────────────────────────────────────────────

PREQIN_SERIES: list[dict[str, str]] = [
    {"series_id": "infra_fund_irr_median_pct",        "series_name": "Infra Fund Median Net IRR (%)",           "unit": "percent"},
    {"series_id": "infra_fund_irr_top_quartile_pct",  "series_name": "Infra Fund Top Quartile Net IRR (%)",     "unit": "percent"},
    {"series_id": "infra_dry_powder_bn_usd",          "series_name": "Infrastructure Dry Powder ($bn)",         "unit": "bn_usd"},
    {"series_id": "infra_deal_count_quarterly",       "series_name": "Quarterly Infrastructure Deal Count",     "unit": "count"},
    {"series_id": "infra_avg_deal_size_m_usd",        "series_name": "Average Infrastructure Deal Size ($M)",   "unit": "m_usd"},
    {"series_id": "renewable_fund_irr_median_pct",    "series_name": "Renewable Energy Fund Median IRR (%)",    "unit": "percent"},
]

_MOCK_PREQIN: dict[str, float] = {
    "infra_fund_irr_median_pct": 9.1,
    "infra_fund_irr_top_quartile_pct": 14.3,
    "infra_dry_powder_bn_usd": 412.0,
    "infra_deal_count_quarterly": 385.0,
    "infra_avg_deal_size_m_usd": 580.0,
    "renewable_fund_irr_median_pct": 11.4,
}


def _mock_preqin_quarterly(series_id: str) -> list[dict[str, Any]]:
    base = _MOCK_PREQIN.get(series_id, 10.0)
    rng = random.Random(hash("preqin:" + series_id) & 0xFFFF)
    today = date.today()
    quarter_starts = []
    y, q = today.year, (today.month - 1) // 3
    for _ in range(12):
        quarter_starts.append(date(y, q * 3 + 1, 1))
        q -= 1
        if q < 0:
            q = 3
            y -= 1
    return [
        {"date": d, "value": round(base * (1 + rng.gauss(0, 0.08)), 2)}
        for d in reversed(quarter_starts)
    ]


async def ingest_preqin_data(db: AsyncSession) -> int:
    """Fetch Preqin private markets benchmarks (mock until Preqin Pro API key configured)."""
    api_key: str = getattr(settings, "PREQIN_API_KEY", "")
    if api_key:
        logger.info("market_data.preqin.subscription_key_set_but_not_implemented")

    total = 0
    for s in PREQIN_SERIES:
        observations = _mock_preqin_quarterly(s["series_id"])
        count = await _upsert_points(db, "preqin", s["series_id"], s["series_name"], s["unit"], observations)
        total += count
        logger.info("market_data.preqin.ingested", series_id=s["series_id"], rows=count)
    return total


# ── EIA ───────────────────────────────────────────────────────────────────────

EIA_SERIES: list[dict[str, str]] = [
    {"series_id": "us_solar_generation_gwh",      "series_name": "US Solar Electricity Generation (GWh)",     "unit": "gwh"},
    {"series_id": "us_wind_generation_gwh",       "series_name": "US Wind Electricity Generation (GWh)",      "unit": "gwh"},
    {"series_id": "us_total_generation_gwh",      "series_name": "US Total Electricity Generation (GWh)",     "unit": "gwh"},
    {"series_id": "us_renewable_share_pct",       "series_name": "US Renewable Share of Generation (%)",      "unit": "percent"},
    {"series_id": "us_solar_capacity_factor_pct", "series_name": "US Average Solar Capacity Factor (%)",      "unit": "percent"},
    {"series_id": "us_wind_capacity_factor_pct",  "series_name": "US Average Wind Capacity Factor (%)",       "unit": "percent"},
    {"series_id": "us_interconnection_queue_gw",  "series_name": "US Total Interconnection Queue Capacity (GW)", "unit": "gw"},
]

_MOCK_EIA: dict[str, float] = {
    "us_solar_generation_gwh": 23500.0,
    "us_wind_generation_gwh": 38200.0,
    "us_total_generation_gwh": 382000.0,
    "us_renewable_share_pct": 22.0,
    "us_solar_capacity_factor_pct": 25.5,
    "us_wind_capacity_factor_pct": 34.2,
    "us_interconnection_queue_gw": 2600.0,
}

# EIA v2 API route and facet for each series
_EIA_ROUTES: dict[str, dict[str, Any]] = {
    "us_solar_generation_gwh":      {"route": "electricity/electric-power-operational-data", "fueltypeid": "SUN"},
    "us_wind_generation_gwh":       {"route": "electricity/electric-power-operational-data", "fueltypeid": "WND"},
    "us_total_generation_gwh":      {"route": "electricity/electric-power-operational-data", "fueltypeid": "ALL"},
    "us_solar_capacity_factor_pct": {"route": "electricity/electric-power-operational-data", "fueltypeid": "SUN"},
    "us_wind_capacity_factor_pct":  {"route": "electricity/electric-power-operational-data", "fueltypeid": "WND"},
}


def _mock_eia_monthly(series_id: str, months: int = 24) -> list[dict[str, Any]]:
    base = _MOCK_EIA.get(series_id, 1000.0)
    rng = random.Random(hash("eia:" + series_id) & 0xFFFF)
    today = date.today()
    result = []
    for i in range(months, 0, -1):
        month = today.month - i
        year = today.year
        while month <= 0:
            month += 12
            year -= 1
        seasonal = 1 + 0.15 * (1 if month in (6, 7, 8) else -0.05)
        result.append({
            "date": date(year, month, 1),
            "value": round(base * seasonal * (1 + rng.gauss(0, 0.05)), 2),
        })
    return result


async def ingest_eia_data(db: AsyncSession) -> int:
    """Fetch US electricity generation data from EIA Open Data API."""
    api_key: str = getattr(settings, "EIA_API_KEY", "")
    total = 0

    for s in EIA_SERIES:
        if api_key and s["series_id"] in _EIA_ROUTES:
            observations = await _fetch_eia_series(api_key, s["series_id"])
        else:
            logger.debug("market_data.eia.no_api_key_mock", series_id=s["series_id"])
            observations = _mock_eia_monthly(s["series_id"])

        count = await _upsert_points(db, "eia", s["series_id"], s["series_name"], s["unit"], observations)
        total += count
        logger.info("market_data.eia.ingested", series_id=s["series_id"], rows=count)

    return total


async def _fetch_eia_series(api_key: str, series_id: str) -> list[dict[str, Any]]:
    """Fetch monthly electricity data from EIA v2 API."""
    route_config = _EIA_ROUTES.get(series_id, {})
    route = route_config.get("route", "electricity/electric-power-operational-data")
    fuel = route_config.get("fueltypeid", "ALL")

    url = f"https://api.eia.gov/v2/{route}/data/"
    params = {
        "api_key": api_key,
        "frequency": "monthly",
        "data[0]": "generation",
        "facets[fueltypeid][]": fuel,
        "facets[location][]": "US-48",
        "sort[0][column]": "period",
        "sort[0][direction]": "desc",
        "length": 24,
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            observations = []
            for row in data.get("response", {}).get("data", []):
                period = row.get("period", "")
                value = row.get("generation")
                if period and value is not None:
                    try:
                        year, month = int(period[:4]), int(period[5:7])
                        observations.append({"date": date(year, month, 1), "value": float(value)})
                    except (ValueError, TypeError):
                        continue
            return sorted(observations, key=lambda x: x["date"]) or _mock_eia_monthly(series_id)
    except Exception as exc:
        logger.warning("market_data.eia.fetch_error", series_id=series_id, error=str(exc))
        return _mock_eia_monthly(series_id)
