"""ECB connector — European Central Bank exchange rates and economic data (free, no key)."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

import httpx

from app.modules.connectors.base import BaseConnector


class ECBConnector(BaseConnector):
    """European Central Bank Statistical Data Warehouse — free, no API key."""

    name = "ecb"
    base_url = "https://data-api.ecb.europa.eu/service"
    rate_limit_per_minute = 60

    _FX_FEED = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"

    async def get_exchange_rates(self) -> dict[str, float]:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(self._FX_FEED)
            resp.raise_for_status()
        root = ET.fromstring(resp.text)
        ns = {
            "gesmes": "http://www.gesmes.org/xml/2002-08-01",
            "ecb": "http://www.ecb.int/vocabulary/2002-08-01/eurofxref",
        }
        rates: dict[str, float] = {"EUR": 1.0}
        for cube in root.findall(".//ecb:Cube[@currency]", ns):
            currency = cube.get("currency")
            rate = cube.get("rate")
            if currency and rate:
                rates[currency] = float(rate)
        return rates

    async def get_series(self, series_key: str) -> list[dict[str, Any]]:
        """Fetch an ECB statistical time series."""
        data = await self.fetch(f"/data/{series_key}", params={"format": "jsondata", "lastNObservations": "12"})
        return data

    async def health_check(self) -> bool:
        try:
            rates = await self.get_exchange_rates()
            return len(rates) > 5
        except Exception:
            return False

    async def test(self) -> dict[str, Any]:
        rates = await self.get_exchange_rates()
        return {
            "connector": self.name,
            "status": "ok",
            "sample": {"currencies": len(rates), "USD": rates.get("USD"), "GBP": rates.get("GBP")},
        }
