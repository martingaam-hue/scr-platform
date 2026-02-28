"""External data feed service — FRED, World Bank, Yahoo Finance, NOAA, Regulations.gov."""
from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx
import structlog

from app.core.config import settings

logger = structlog.get_logger()

# Feed configuration
FEEDS: dict[str, dict[str, Any]] = {
    "fred": {
        "name": "Federal Reserve Economic Data",
        "base_url": "https://api.stlouisfed.org/fred/series/observations",
        "refresh_seconds": 3600,
        "used_by": ["signal_score", "risk_assessment", "market_analysis"],
        "series": ["FEDFUNDS", "T10YIE", "VIXCLS", "DCOILWTICO"],  # Rate, inflation, volatility, oil
    },
    "world_bank": {
        "name": "World Bank Open Data",
        "base_url": settings.WORLD_BANK_BASE_URL,
        "refresh_seconds": 86400,
        "used_by": ["signal_score", "esg_scoring"],
        "indicators": ["NY.GDP.MKTP.KD.ZG", "EN.ATM.CO2E.PC"],  # GDP growth, CO2
    },
    "yahoo_finance": {
        "name": "Yahoo Finance (via yfinance)",
        "refresh_seconds": 3600,
        "used_by": ["risk_assessment", "valuation"],
        "symbols": ["^GSPC", "^VIX", "CL=F", "NG=F"],  # S&P, VIX, Crude, NatGas
    },
    "noaa_climate": {
        "name": "NOAA Climate Data",
        "base_url": "https://www.ncdc.noaa.gov/cdo-web/api/v2",
        "refresh_seconds": 43200,
        "used_by": ["risk_assessment", "climate_risk"],
    },
    "regulations_gov": {
        "name": "Regulations.gov",
        "base_url": "https://api.regulations.gov/v4",
        "refresh_seconds": 21600,
        "used_by": ["risk_assessment", "compliance"],
    },
}

# In-memory cache: {feed_name: {"data": ..., "fetched_at": timestamp}}
_cache: dict[str, dict[str, Any]] = {}


class ExternalDataFeedService:
    """Manages connections to external data sources for live scoring and monitoring."""

    async def get_feed_data(self, feed_name: str) -> dict[str, Any] | None:
        """Return cached data if fresh, else refresh."""
        config = FEEDS.get(feed_name)
        if not config:
            logger.warning("unknown_feed", feed=feed_name)
            return None

        cached = _cache.get(feed_name)
        if cached:
            age = time.time() - cached["fetched_at"]
            if age < config["refresh_seconds"]:
                return cached["data"]

        return await self.refresh_feed(feed_name)

    async def refresh_feed(self, feed_name: str) -> dict[str, Any] | None:
        """Fetch fresh data from source."""
        config = FEEDS.get(feed_name)
        if not config:
            return None

        try:
            data = await self._fetch(feed_name, config)
            _cache[feed_name] = {"data": data, "fetched_at": time.time()}
            logger.info("feed_refreshed", feed=feed_name, records=len(data) if isinstance(data, list) else 1)
            return data
        except Exception as e:
            logger.warning("feed_refresh_failed", feed=feed_name, error=str(e))
            return _cache.get(feed_name, {}).get("data")  # Return stale data on error

    async def _fetch(self, feed_name: str, config: dict[str, Any]) -> Any:
        """Fetch data from external API."""
        if feed_name == "fred":
            return await self._fetch_fred(config)
        if feed_name == "world_bank":
            return await self._fetch_world_bank(config)
        if feed_name == "yahoo_finance":
            return await self._fetch_yahoo_finance(config)
        if feed_name == "noaa_climate":
            return await self._fetch_noaa(config)
        if feed_name == "regulations_gov":
            return await self._fetch_regulations(config)
        return {}

    async def _fetch_fred(self, config: dict[str, Any]) -> dict[str, Any]:
        """Fetch FRED economic indicators."""
        if not settings.FRED_API_KEY:
            return {"note": "FRED_API_KEY not configured", "data": {}}

        results: dict[str, Any] = {}
        async with httpx.AsyncClient(timeout=15.0) as client:
            for series_id in config.get("series", []):
                try:
                    resp = await client.get(
                        config["base_url"],
                        params={
                            "series_id": series_id,
                            "api_key": settings.FRED_API_KEY,
                            "file_type": "json",
                            "limit": 1,
                            "sort_order": "desc",
                        },
                    )
                    resp.raise_for_status()
                    obs = resp.json().get("observations", [])
                    if obs:
                        results[series_id] = {"value": obs[0]["value"], "date": obs[0]["date"]}
                except Exception as e:
                    logger.warning("fred_series_failed", series=series_id, error=str(e))
        return results

    async def _fetch_world_bank(self, config: dict[str, Any]) -> dict[str, Any]:
        """Fetch World Bank indicators."""
        results: dict[str, Any] = {}
        async with httpx.AsyncClient(timeout=15.0) as client:
            for indicator in config.get("indicators", []):
                try:
                    url = f"{config['base_url']}/country/all/indicator/{indicator}"
                    resp = await client.get(url, params={"format": "json", "per_page": 5, "mrv": 2})
                    resp.raise_for_status()
                    data = resp.json()
                    if len(data) >= 2 and data[1]:
                        results[indicator] = [
                            {"country": d.get("country", {}).get("value"), "value": d.get("value"), "date": d.get("date")}
                            for d in data[1][:5]
                            if d.get("value") is not None
                        ]
                except Exception as e:
                    logger.warning("worldbank_indicator_failed", indicator=indicator, error=str(e))
        return results

    async def _fetch_yahoo_finance(self, config: dict[str, Any]) -> dict[str, Any]:
        """Fetch market data via yfinance (installed separately)."""
        try:
            import yfinance as yf  # type: ignore[import]
            results: dict[str, Any] = {}
            for symbol in config.get("symbols", []):
                try:
                    ticker = yf.Ticker(symbol)
                    info = ticker.fast_info
                    results[symbol] = {
                        "last_price": getattr(info, "last_price", None),
                        "previous_close": getattr(info, "previous_close", None),
                        "currency": getattr(info, "currency", None),
                    }
                except Exception as e:
                    logger.warning("yfinance_symbol_failed", symbol=symbol, error=str(e))
            return results
        except ImportError:
            return {"note": "yfinance not installed — add to requirements"}

    async def _fetch_noaa(self, config: dict[str, Any]) -> dict[str, Any]:
        """Fetch NOAA climate data."""
        if not settings.NOAA_TOKEN:
            return {"note": "NOAA_TOKEN not configured"}
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                resp = await client.get(
                    f"{config['base_url']}/data",
                    params={"datasetid": "GHCND", "limit": 10},
                    headers={"token": settings.NOAA_TOKEN},
                )
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                return {"error": str(e)}

    async def _fetch_regulations(self, config: dict[str, Any]) -> dict[str, Any]:
        """Fetch recent regulatory documents."""
        if not settings.REGULATIONS_GOV_API_KEY:
            return {"note": "REGULATIONS_GOV_API_KEY not configured"}
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                resp = await client.get(
                    f"{config['base_url']}/documents",
                    params={"filter[searchTerm]": "renewable energy", "page[size]": 5},
                    headers={"X-Api-Key": settings.REGULATIONS_GOV_API_KEY},
                )
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                return {"error": str(e)}

    def get_cache_status(self) -> dict[str, Any]:
        """Return cache freshness status for all feeds."""
        status = {}
        for feed_name, config in FEEDS.items():
            cached = _cache.get(feed_name)
            if cached:
                age_s = int(time.time() - cached["fetched_at"])
                status[feed_name] = {
                    "cached": True,
                    "age_seconds": age_s,
                    "stale": age_s > config["refresh_seconds"],
                    "used_by": config["used_by"],
                }
            else:
                status[feed_name] = {"cached": False, "used_by": config["used_by"]}
        return status


_feed_service: ExternalDataFeedService | None = None


def get_feed_service() -> ExternalDataFeedService:
    global _feed_service
    if _feed_service is None:
        _feed_service = ExternalDataFeedService()
    return _feed_service
