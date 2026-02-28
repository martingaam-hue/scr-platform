"""Abstract base connector — authenticated HTTP client with rate limiting and logging."""

from __future__ import annotations

import time
import uuid
from abc import ABC, abstractmethod
from typing import Any

import httpx
import structlog

logger = structlog.get_logger()

_rate_limit_state: dict[str, list[float]] = {}


class BaseConnector(ABC):
    """Abstract connector interface all data integrations must implement."""

    name: str = ""
    base_url: str = ""
    rate_limit_per_minute: int = 60

    def __init__(self, api_key: str | None = None, config: dict | None = None):
        self.api_key = api_key
        self.config = config or {}
        self._client: httpx.AsyncClient | None = None

    def _get_headers(self) -> dict[str, str]:
        """Return auth headers. Override in subclass if different."""
        if self.api_key:
            return {"Authorization": f"Bearer {self.api_key}"}
        return {}

    def _check_rate_limit(self) -> bool:
        """Sliding window rate limiter. Returns False if limit exceeded."""
        now = time.time()
        key = self.name
        calls = _rate_limit_state.get(key, [])
        # Remove calls older than 60 seconds
        calls = [t for t in calls if now - t < 60]
        if len(calls) >= self.rate_limit_per_minute:
            return False
        calls.append(now)
        _rate_limit_state[key] = calls
        return True

    async def fetch(self, endpoint: str, params: dict | None = None) -> dict[str, Any]:
        """Make authenticated GET request with rate limiting."""
        if not self._check_rate_limit():
            raise RuntimeError(f"Rate limit exceeded for connector {self.name}")

        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(url, headers=self._get_headers(), params=params or {})
                elapsed_ms = int((time.time() - start) * 1000)
                logger.info(
                    "connector.fetch",
                    connector=self.name,
                    url=url,
                    status=resp.status_code,
                    ms=elapsed_ms,
                )
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(f"Connector {self.name} error {exc.response.status_code}: {exc.response.text[:200]}")
        except httpx.RequestError as exc:
            raise RuntimeError(f"Connector {self.name} network error: {exc}")

    async def post(self, endpoint: str, data: dict | None = None) -> dict[str, Any]:
        """Make authenticated POST request."""
        if not self._check_rate_limit():
            raise RuntimeError(f"Rate limit exceeded for connector {self.name}")

        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(url, headers=self._get_headers(), json=data or {})
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(f"Connector {self.name} error {exc.response.status_code}")

    @abstractmethod
    async def health_check(self) -> bool:
        """Verify connectivity and auth. Returns True if healthy."""
        ...

    @abstractmethod
    async def test(self) -> dict[str, Any]:
        """Run a test call and return sample data for UI display."""
        ...
