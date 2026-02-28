"""OpenWeather connector — weather + solar irradiance (free tier available)."""

from __future__ import annotations

from typing import Any

from app.modules.connectors.base import BaseConnector


class OpenWeatherConnector(BaseConnector):
    """OpenWeatherMap API — weather and solar radiation data."""

    name = "open_weather"
    base_url = "https://api.openweathermap.org"
    rate_limit_per_minute = 60

    def _get_headers(self) -> dict[str, str]:
        return {}  # Key passed as query param

    async def _params(self, extra: dict | None = None) -> dict[str, str]:
        p: dict[str, str] = {}
        if self.api_key:
            p["appid"] = self.api_key
        if extra:
            p.update(extra)
        return p

    async def get_current_weather(self, lat: float, lon: float) -> dict[str, Any]:
        return await self.fetch("/data/2.5/weather", params=await self._params({"lat": str(lat), "lon": str(lon), "units": "metric"}))

    async def get_solar_irradiance(self, lat: float, lon: float) -> dict[str, Any]:
        """Solar radiation data — requires One Call API subscription."""
        return await self.fetch(
            "/data/3.0/onecall",
            params=await self._params({"lat": str(lat), "lon": str(lon), "exclude": "minutely,hourly,alerts", "units": "metric"}),
        )

    async def get_forecast(self, lat: float, lon: float, days: int = 5) -> list[dict[str, Any]]:
        data = await self.fetch("/data/2.5/forecast", params=await self._params({"lat": str(lat), "lon": str(lon), "units": "metric", "cnt": str(days * 8)}))
        return data.get("list", [])

    async def health_check(self) -> bool:
        try:
            await self.get_current_weather(51.5, -0.1)  # London
            return True
        except Exception:
            return False

    async def test(self) -> dict[str, Any]:
        weather = await self.get_current_weather(40.4, -3.7)  # Madrid
        return {
            "connector": self.name,
            "status": "ok",
            "sample": {
                "location": "Madrid",
                "temp_c": weather.get("main", {}).get("temp"),
                "description": weather.get("weather", [{}])[0].get("description"),
            },
        }
