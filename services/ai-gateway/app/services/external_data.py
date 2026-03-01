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
    "irena": {
        "name": "IRENA Renewable Energy Statistics",
        "refresh_seconds": 86400,
        "used_by": ["signal_score", "esg_scoring", "market_analysis"],
    },
    "eu_ets": {
        "name": "EU ETS / Ember Carbon Market Data",
        "base_url": "https://api.ember-climate.org/v1",
        "refresh_seconds": 21600,
        "used_by": ["risk_assessment", "esg_scoring", "market_analysis"],
    },
    "companies_house": {
        "name": "Companies House UK",
        "base_url": "https://api.company-information.service.gov.uk",
        "refresh_seconds": 86400,
        "used_by": ["due_diligence", "risk_assessment"],
    },
    "alpha_vantage": {
        "name": "Alpha Vantage — Commodities & ETFs",
        "base_url": "https://www.alphavantage.co/query",
        "refresh_seconds": 3600,
        "used_by": ["risk_assessment", "valuation", "market_analysis"],
    },
    "entsoe": {
        "name": "ENTSOE Transparency Platform",
        "base_url": "https://web-api.tp.entsoe.eu/api",
        "refresh_seconds": 21600,
        "used_by": ["signal_score", "market_analysis"],
    },
    "openweather": {
        "name": "OpenWeather — Energy Hub Locations",
        "base_url": "https://api.openweathermap.org/data/2.5",
        "refresh_seconds": 43200,
        "used_by": ["risk_assessment", "signal_score"],
    },
    "eurostat": {
        "name": "Eurostat EU Economic & Energy Statistics",
        "base_url": "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0",
        "refresh_seconds": 604800,
        "used_by": ["signal_score", "esg_scoring", "market_analysis"],
    },
    "iea": {
        "name": "IEA Clean Energy Statistics",
        "refresh_seconds": 604800,
        "used_by": ["signal_score", "esg_scoring", "market_analysis"],
    },
    "sp_global": {
        "name": "S&P Global ESG & Credit",
        "refresh_seconds": 86400,
        "used_by": ["risk_assessment", "esg_scoring"],
    },
    "bnef": {
        "name": "Bloomberg NEF Clean Energy Markets",
        "refresh_seconds": 86400,
        "used_by": ["valuation", "signal_score", "market_analysis"],
    },
    "msci_esg": {
        "name": "MSCI ESG Ratings & Climate Metrics",
        "refresh_seconds": 86400,
        "used_by": ["esg_scoring", "risk_assessment"],
    },
    "un_sdg": {
        "name": "UN Sustainable Development Goals",
        "base_url": "https://unstats.un.org/sdgs/UNSDGAPIV5/v1",
        "refresh_seconds": 2592000,
        "used_by": ["esg_scoring", "signal_score"],
    },
    "preqin": {
        "name": "Preqin Private Markets Benchmarks",
        "refresh_seconds": 86400,
        "used_by": ["valuation", "risk_assessment"],
    },
    "eia": {
        "name": "EIA US Energy Generation Data",
        "base_url": "https://api.eia.gov/v2",
        "refresh_seconds": 604800,
        "used_by": ["signal_score", "market_analysis"],
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
        if feed_name == "irena":
            return await self._fetch_irena(config)
        if feed_name == "eu_ets":
            return await self._fetch_eu_ets(config)
        if feed_name == "companies_house":
            return await self._fetch_companies_house(config)
        if feed_name == "alpha_vantage":
            return await self._fetch_alpha_vantage(config)
        if feed_name == "entsoe":
            return await self._fetch_entsoe(config)
        if feed_name == "openweather":
            return await self._fetch_openweather(config)
        if feed_name == "eurostat":
            return await self._fetch_eurostat(config)
        if feed_name == "iea":
            return await self._fetch_iea(config)
        if feed_name == "sp_global":
            return await self._fetch_sp_global(config)
        if feed_name == "bnef":
            return await self._fetch_bnef(config)
        if feed_name == "msci_esg":
            return await self._fetch_msci_esg(config)
        if feed_name == "un_sdg":
            return await self._fetch_un_sdg(config)
        if feed_name == "preqin":
            return await self._fetch_preqin(config)
        if feed_name == "eia":
            return await self._fetch_eia(config)
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

    async def _fetch_irena(self, config: dict[str, Any]) -> dict[str, Any]:
        """IRENA renewable energy statistics (mock — IRENASTAT API requires registration)."""
        return {
            "global_renewable_capacity_gw": {"value": 3382.0, "unit": "GW", "note": "mock — IRENASTAT API registration required"},
            "solar_pv_capacity_gw": {"value": 1177.0, "unit": "GW"},
            "wind_capacity_gw": {"value": 899.0, "unit": "GW"},
            "solar_lcoe_usd_kwh": {"value": 0.049, "unit": "USD/kWh"},
            "onshore_wind_lcoe_usd_kwh": {"value": 0.033, "unit": "USD/kWh"},
        }

    async def _fetch_eu_ets(self, config: dict[str, Any]) -> dict[str, Any]:
        """EU ETS carbon price data via Ember API."""
        if not settings.EMBER_API_KEY:
            return {"eua_price_eur": {"value": 62.5, "unit": "EUR/tCO2", "note": "mock — set EMBER_API_KEY"}}
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"{config['base_url']}/carbon-price-data",
                    headers={"Authorization": f"Bearer {settings.EMBER_API_KEY}"},
                    params={"format": "json", "limit": 1},
                )
                resp.raise_for_status()
                data = resp.json()
                rows = data.get("data", [])
                if rows:
                    return {"eua_price_eur": {"value": rows[0].get("price", 62.5), "date": rows[0].get("date"), "unit": "EUR/tCO2"}}
        except Exception as e:
            logger.warning("eu_ets_feed_failed", error=str(e))
        return {"eua_price_eur": {"value": 62.5, "unit": "EUR/tCO2", "note": "api_error_fallback"}}

    async def _fetch_companies_house(self, config: dict[str, Any]) -> dict[str, Any]:
        """UK Companies House aggregate statistics."""
        if not settings.COMPANIES_HOUSE_API_KEY:
            return {"note": "COMPANIES_HOUSE_API_KEY not configured", "uk_active_companies_total": 5100000}
        import base64
        encoded_key = base64.b64encode(f"{settings.COMPANIES_HOUSE_API_KEY}:".encode()).decode()
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"{config['base_url']}/company",
                    params={"q": "limited", "items_per_page": 1},
                    headers={"Authorization": f"Basic {encoded_key}"},
                )
                resp.raise_for_status()
                data = resp.json()
                return {"uk_active_companies_total": data.get("total_results", 5100000)}
        except Exception as e:
            logger.warning("companies_house_feed_failed", error=str(e))
            return {"uk_active_companies_total": 5100000, "note": "api_error_fallback"}

    async def _fetch_alpha_vantage(self, config: dict[str, Any]) -> dict[str, Any]:
        """Alpha Vantage commodity prices and ETF quotes."""
        if not settings.ALPHA_VANTAGE_API_KEY:
            return {
                "WTI": {"value": 78.5, "unit": "USD/bbl", "note": "mock — set ALPHA_VANTAGE_API_KEY"},
                "BRENT": {"value": 82.3, "unit": "USD/bbl"},
                "NATURAL_GAS": {"value": 2.45, "unit": "USD/MMBtu"},
                "XLE": {"value": 91.0, "unit": "USD"},
                "ICLN": {"value": 14.2, "unit": "USD"},
            }
        results: dict[str, Any] = {}
        async with httpx.AsyncClient(timeout=15.0) as client:
            for symbol in ["WTI", "BRENT", "NATURAL_GAS", "XLE", "ICLN"]:
                try:
                    func = symbol if symbol in ("WTI", "BRENT", "NATURAL_GAS") else "GLOBAL_QUOTE"
                    params: dict[str, str] = {"function": func, "apikey": settings.ALPHA_VANTAGE_API_KEY}
                    if func == "GLOBAL_QUOTE":
                        params["symbol"] = symbol
                    resp = await client.get(config["base_url"], params=params)
                    resp.raise_for_status()
                    data = resp.json()
                    if func == "GLOBAL_QUOTE":
                        price = data.get("Global Quote", {}).get("05. price")
                        if price:
                            results[symbol] = {"value": float(price), "unit": "USD"}
                    else:
                        rows = data.get("data", [])
                        if rows:
                            results[symbol] = {"value": float(rows[0]["value"]), "date": rows[0]["date"], "unit": "USD"}
                except Exception as e:
                    logger.warning("alpha_vantage_symbol_failed", symbol=symbol, error=str(e))
        return results

    async def _fetch_entsoe(self, config: dict[str, Any]) -> dict[str, Any]:
        """ENTSOE day-ahead electricity prices for major European bidding zones."""
        if not settings.ENTSOE_API_KEY:
            return {
                "DE_day_ahead_eur_mwh": {"value": 95.0, "unit": "EUR/MWh", "note": "mock — set ENTSOE_API_KEY"},
                "FR_day_ahead_eur_mwh": {"value": 92.0, "unit": "EUR/MWh"},
                "ES_day_ahead_eur_mwh": {"value": 88.0, "unit": "EUR/MWh"},
            }
        import xml.etree.ElementTree as ET
        from datetime import datetime
        zones = {"DE": "10Y1001A1001A63L", "FR": "10YFR-RTE------C", "ES": "10YES-REE------0"}
        results: dict[str, Any] = {}
        period_end = datetime.utcnow().strftime("%Y%m%d%H%M")
        period_start = (datetime.utcnow().replace(hour=0, minute=0)).strftime("%Y%m%d%H%M")
        async with httpx.AsyncClient(timeout=20.0) as client:
            for country, eic in zones.items():
                try:
                    resp = await client.get(
                        config["base_url"],
                        params={
                            "securityToken": settings.ENTSOE_API_KEY,
                            "documentType": "A44",
                            "in_Domain": eic,
                            "out_Domain": eic,
                            "periodStart": period_start,
                            "periodEnd": period_end,
                        },
                    )
                    resp.raise_for_status()
                    root = ET.fromstring(resp.text)
                    ns = {"ns": "urn:iec62325.351:tc57wg16:451-3:publicationdocument:7:0"}
                    prices = [
                        float(p.findtext("ns:price.amount", namespaces=ns))
                        for p in root.findall(".//ns:Point", ns)
                        if p.findtext("ns:price.amount", namespaces=ns)
                    ]
                    if prices:
                        results[f"{country}_day_ahead_eur_mwh"] = {"value": round(sum(prices) / len(prices), 2), "unit": "EUR/MWh"}
                except Exception as e:
                    logger.warning("entsoe_zone_failed", country=country, error=str(e))
        return results or {"note": "ENTSOE API call failed — check ENTSOE_API_KEY"}

    async def _fetch_openweather(self, config: dict[str, Any]) -> dict[str, Any]:
        """OpenWeather data for key European energy hub locations."""
        if not settings.OPENWEATHER_API_KEY:
            return {
                "Berlin_wind_speed_ms": {"value": 5.2, "unit": "m/s", "note": "mock — set OPENWEATHER_API_KEY"},
                "Madrid_temperature_c": {"value": 18.5, "unit": "°C"},
            }
        locations = [
            {"name": "Berlin", "lat": 52.52, "lon": 13.40},
            {"name": "Madrid", "lat": 40.42, "lon": -3.70},
            {"name": "London", "lat": 51.51, "lon": -0.13},
        ]
        results: dict[str, Any] = {}
        async with httpx.AsyncClient(timeout=15.0) as client:
            for loc in locations:
                try:
                    resp = await client.get(
                        f"{config['base_url']}/weather",
                        params={"lat": loc["lat"], "lon": loc["lon"], "appid": settings.OPENWEATHER_API_KEY, "units": "metric"},
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    results[f"{loc['name']}_wind_speed_ms"] = {"value": data.get("wind", {}).get("speed"), "unit": "m/s"}
                    results[f"{loc['name']}_temperature_c"] = {"value": data.get("main", {}).get("temp"), "unit": "°C"}
                    results[f"{loc['name']}_cloud_cover_pct"] = {"value": data.get("clouds", {}).get("all"), "unit": "%"}
                except Exception as e:
                    logger.warning("openweather_location_failed", location=loc["name"], error=str(e))
        return results

    async def _fetch_eurostat(self, config: dict[str, Any]) -> dict[str, Any]:
        """Eurostat EU energy and economic statistics (public API, no key needed)."""
        results: dict[str, Any] = {}
        datasets = [
            ("eu_renewable_share_pct", "nrg_ind_ren", {"unit": "PC", "nrg_bal": "REN", "geo": "EU27_2020"}),
            ("eu_gdp_growth_pct", "tec00115", {"unit": "PCH_PRE_PER", "geo": "EU27_2020"}),
            ("eu_unemployment_pct", "une_rt_m", {"unit": "PC_ACT", "s_adj": "NSA", "age": "TOTAL", "sex": "T", "geo": "EU27_2020"}),
        ]
        async with httpx.AsyncClient(timeout=20.0) as client:
            for key, dataset, params in datasets:
                try:
                    resp = await client.get(
                        f"{config['base_url']}/data/{dataset}",
                        params={"format": "JSON", "lang": "EN", **params},
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    values = data.get("value", {})
                    if values:
                        last_val = list(values.values())[-1]
                        results[key] = {"value": float(last_val), "unit": "%"}
                except Exception as e:
                    logger.warning("eurostat_dataset_failed", dataset=dataset, error=str(e))
        if not results:
            results = {
                "eu_renewable_share_pct": {"value": 22.5, "unit": "%", "note": "mock"},
                "eu_gdp_growth_pct": {"value": 1.2, "unit": "%"},
            }
        return results

    async def _fetch_iea(self, config: dict[str, Any]) -> dict[str, Any]:
        """IEA clean energy investment and deployment data (mock until IEA API key configured)."""
        return {
            "global_clean_energy_investment_bn_usd": {"value": 1740.0, "unit": "$bn", "note": "mock — set IEA_API_KEY for live data"},
            "global_renewable_capacity_additions_gw": {"value": 295.0, "unit": "GW"},
            "global_ev_sales_millions": {"value": 10.5, "unit": "millions"},
            "fossil_fuel_subsidies_bn_usd": {"value": 7000.0, "unit": "$bn"},
        }

    async def _fetch_sp_global(self, config: dict[str, Any]) -> dict[str, Any]:
        """S&P Global ESG scores and credit data (mock until subscription API configured)."""
        return {
            "sp500_esg_score_avg": {"value": 54.0, "unit": "score_0_100", "note": "mock — S&P Global subscription required"},
            "infra_sector_esg_score": {"value": 61.0, "unit": "score_0_100"},
            "probability_of_default_bb_pct": {"value": 1.2, "unit": "%"},
        }

    async def _fetch_bnef(self, config: dict[str, Any]) -> dict[str, Any]:
        """Bloomberg NEF clean energy market data (mock until BNEF subscription configured)."""
        return {
            "corporate_ppa_price_usd_mwh": {"value": 42.0, "unit": "USD/MWh", "note": "mock — BNEF subscription required"},
            "solar_auction_price_usd_mwh": {"value": 31.0, "unit": "USD/MWh"},
            "wind_auction_price_usd_mwh": {"value": 38.0, "unit": "USD/MWh"},
            "lcoe_solar_utility_usd_mwh": {"value": 49.0, "unit": "USD/MWh"},
            "lcoe_wind_onshore_usd_mwh": {"value": 33.0, "unit": "USD/MWh"},
        }

    async def _fetch_msci_esg(self, config: dict[str, Any]) -> dict[str, Any]:
        """MSCI ESG ratings and climate metrics (mock until MSCI ESG subscription configured)."""
        return {
            "infra_sector_esg_score": {"value": 6.2, "unit": "score_0_10", "note": "mock — MSCI ESG subscription required"},
            "renewable_energy_esg_score": {"value": 7.8, "unit": "score_0_10"},
            "implied_temp_rise_infra_c": {"value": 2.4, "unit": "°C"},
            "climate_var_infra_pct": {"value": -8.5, "unit": "%"},
        }

    async def _fetch_un_sdg(self, config: dict[str, Any]) -> dict[str, Any]:
        """UN SDG indicator data (public API, no key needed)."""
        results: dict[str, Any] = {}
        indicators = [("7.2.1", "renewable_energy_share_pct"), ("7.3.1", "energy_intensity_mj_gdp")]
        async with httpx.AsyncClient(timeout=20.0) as client:
            for indicator_code, key in indicators:
                try:
                    resp = await client.get(
                        f"{config['base_url']}/sdg/Indicator/Data",
                        params={"indicator": indicator_code, "areaCode": "WORLD", "limit": 1},
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    rows = data.get("data", [])
                    if rows:
                        results[key] = {"value": float(rows[0].get("value", 0)), "year": rows[0].get("timePeriodStart")}
                except Exception as e:
                    logger.warning("un_sdg_indicator_failed", indicator=indicator_code, error=str(e))
        if not results:
            results = {
                "renewable_energy_share_pct": {"value": 19.1, "unit": "%", "note": "mock"},
                "energy_intensity_mj_gdp": {"value": 4.7, "unit": "MJ/$2017 GDP"},
            }
        return results

    async def _fetch_preqin(self, config: dict[str, Any]) -> dict[str, Any]:
        """Preqin private markets benchmarks (mock until Preqin Pro subscription configured)."""
        return {
            "infra_fund_irr_median_pct": {"value": 9.1, "unit": "%", "note": "mock — Preqin Pro subscription required"},
            "infra_fund_irr_top_quartile_pct": {"value": 14.3, "unit": "%"},
            "infra_dry_powder_bn_usd": {"value": 412.0, "unit": "$bn"},
            "infra_deal_count_quarterly": {"value": 385, "unit": "deals"},
            "renewable_fund_irr_median_pct": {"value": 11.4, "unit": "%"},
        }

    async def _fetch_eia(self, config: dict[str, Any]) -> dict[str, Any]:
        """US EIA electricity generation data."""
        if not settings.EIA_API_KEY:
            return {
                "us_solar_generation_gwh": {"value": 23500.0, "unit": "GWh", "note": "mock — set EIA_API_KEY"},
                "us_wind_generation_gwh": {"value": 38200.0, "unit": "GWh"},
                "us_renewable_share_pct": {"value": 22.0, "unit": "%"},
            }
        results: dict[str, Any] = {}
        url = f"{config['base_url']}/electricity/electric-power-operational-data/data/"
        async with httpx.AsyncClient(timeout=20.0) as client:
            for fuel, key in [("SUN", "us_solar_generation_gwh"), ("WND", "us_wind_generation_gwh")]:
                try:
                    resp = await client.get(url, params={
                        "api_key": settings.EIA_API_KEY,
                        "frequency": "monthly",
                        "data[0]": "generation",
                        "facets[fueltypeid][]": fuel,
                        "facets[location][]": "US-48",
                        "sort[0][column]": "period",
                        "sort[0][direction]": "desc",
                        "length": 1,
                    })
                    resp.raise_for_status()
                    data = resp.json()
                    rows = data.get("response", {}).get("data", [])
                    if rows:
                        results[key] = {"value": float(rows[0].get("generation", 0)), "period": rows[0].get("period"), "unit": "GWh"}
                except Exception as e:
                    logger.warning("eia_series_failed", fuel=fuel, error=str(e))
        return results or {"note": "EIA API call failed"}

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
