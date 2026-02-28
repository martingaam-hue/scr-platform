"""Companies House connector — UK company data (free API key)."""

from __future__ import annotations

from typing import Any

from app.modules.connectors.base import BaseConnector


class CompaniesHouseConnector(BaseConnector):
    """UK Companies House public data API — free with API key."""

    name = "companies_house"
    base_url = "https://api.company-information.service.gov.uk"
    rate_limit_per_minute = 60

    def _get_headers(self) -> dict[str, str]:
        if self.api_key:
            import base64
            token = base64.b64encode(f"{self.api_key}:".encode()).decode()
            return {"Authorization": f"Basic {token}"}
        return {}

    async def search_company(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        data = await self.fetch("/search/companies", params={"q": query, "items_per_page": limit})
        return data.get("items", [])

    async def get_company(self, company_number: str) -> dict[str, Any]:
        return await self.fetch(f"/company/{company_number}")

    async def get_filing_history(self, company_number: str, limit: int = 20) -> list[dict[str, Any]]:
        data = await self.fetch(f"/company/{company_number}/filing-history", params={"items_per_page": limit})
        return data.get("items", [])

    async def get_officers(self, company_number: str) -> list[dict[str, Any]]:
        data = await self.fetch(f"/company/{company_number}/officers")
        return data.get("items", [])

    async def health_check(self) -> bool:
        try:
            results = await self.search_company("test", limit=1)
            return isinstance(results, list)
        except Exception:
            return False

    async def test(self) -> dict[str, Any]:
        results = await self.search_company("Aston Martin", limit=3)
        return {
            "connector": self.name,
            "status": "ok",
            "sample": {"query": "Aston Martin", "results_count": len(results), "sample": results[:2]},
        }
