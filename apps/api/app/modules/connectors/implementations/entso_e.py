"""ENTSO-E Transparency Platform connector — European energy market data (free)."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import date
from typing import Any

import httpx

from app.modules.connectors.base import BaseConnector


class ENTSOEConnector(BaseConnector):
    """European Network of Transmission System Operators for Electricity.

    Free API — no key required for most data.
    """

    name = "entso_e"
    base_url = "https://web-api.tp.entsoe.eu/api"
    rate_limit_per_minute = 30

    _DOMAIN_CODES = {
        "DE": "10Y1001A1001A82H",
        "FR": "10YFR-RTE------C",
        "ES": "10YES-REE------0",
        "IT": "10YIT-GRTN-----B",
        "NL": "10YNL----------L",
        "PL": "10YPL-AREA-----S",
        "SE": "10YSE-1--------K",
    }

    def _get_headers(self) -> dict[str, str]:
        if self.api_key:
            return {"Content-Type": "application/xml"}
        return {}

    async def get_day_ahead_prices(self, country_code: str, target_date: str | None = None) -> list[dict[str, Any]]:
        """Get day-ahead electricity prices for a country."""
        domain = self._DOMAIN_CODES.get(country_code.upper())
        if not domain:
            raise ValueError(f"Unsupported country: {country_code}")

        d = date.fromisoformat(target_date) if target_date else date.today()
        period_start = d.strftime("%Y%m%d0000")
        period_end = d.strftime("%Y%m%d2300")

        params = {
            "documentType": "A44",
            "in_Domain": domain,
            "out_Domain": domain,
            "periodStart": period_start,
            "periodEnd": period_end,
        }
        if self.api_key:
            params["securityToken"] = self.api_key

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(self.base_url, params=params)
            resp.raise_for_status()

        root = ET.fromstring(resp.text)
        ns = {"ns": "urn:iec62325.351:tc57wg16:451-3:publicationdocument:7:0"}
        prices = []
        for period in root.findall(".//ns:Period", ns):
            for point in period.findall("ns:Point", ns):
                pos = point.findtext("ns:position", namespaces=ns)
                price = point.findtext("ns:price.amount", namespaces=ns)
                if pos and price:
                    prices.append({"hour": int(pos) - 1, "price_eur_mwh": float(price)})
        return prices

    async def health_check(self) -> bool:
        try:
            await self.get_day_ahead_prices("DE")
            return True
        except Exception:
            return False

    async def test(self) -> dict[str, Any]:
        prices = await self.get_day_ahead_prices("DE")
        return {
            "connector": self.name,
            "status": "ok",
            "sample": {"country": "DE", "day_ahead_prices_count": len(prices), "sample": prices[:3]},
        }
