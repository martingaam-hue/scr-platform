"""Main Locust load test — simulates a typical SCR Platform user session.

Usage:
    # Headless against staging (50 users, 5/s ramp, 5 minutes)
    poetry run locust -f tests/load/locustfile.py \
        --host=https://api.pampgroup.com \
        --users=50 --spawn-rate=5 --run-time=5m \
        --headless --csv=tests/load/results/baseline

    # Interactive UI (localhost:8089)
    poetry run locust -f tests/load/locustfile.py --host=https://api.pampgroup.com
"""

from __future__ import annotations

import os
import uuid

from locust import HttpUser, between, task


# Pre-configured test credentials — set via environment variables so secrets
# are never committed.  Tests degrade gracefully when credentials are absent.
_TEST_TOKEN = os.getenv("LOAD_TEST_JWT", "")
_TEST_PROJECT_ID = os.getenv("LOAD_TEST_PROJECT_ID", str(uuid.UUID(int=1)))
_TEST_PORTFOLIO_ID = os.getenv("LOAD_TEST_PORTFOLIO_ID", str(uuid.UUID(int=2)))


class SCRUser(HttpUser):
    """Simulates a typical investor/analyst browsing the platform."""

    wait_time = between(1, 3)

    def on_start(self) -> None:
        self.token = _TEST_TOKEN
        self.project_id = _TEST_PROJECT_ID
        self.portfolio_id = _TEST_PORTFOLIO_ID
        self._auth = {"Authorization": f"Bearer {self.token}"}

    # ── Read-heavy tasks (most traffic) ───────────────────────────────────────

    @task(5)
    def list_projects(self) -> None:
        self.client.get("/v1/projects", headers=self._auth, name="/v1/projects")

    @task(4)
    def health_check(self) -> None:
        self.client.get("/health", name="/health")

    @task(3)
    def get_signal_score(self) -> None:
        self.client.get(
            f"/v1/signal-score/{self.project_id}",
            headers=self._auth,
            name="/v1/signal-score/[id]",
        )

    @task(3)
    def list_deal_flow(self) -> None:
        self.client.get("/v1/deal-flow", headers=self._auth, name="/v1/deal-flow")

    @task(2)
    def get_risk_dashboard(self) -> None:
        self.client.get(
            f"/v1/risk/{self.project_id}",
            headers=self._auth,
            name="/v1/risk/[id]",
        )

    @task(2)
    def list_portfolio(self) -> None:
        self.client.get("/v1/portfolio", headers=self._auth, name="/v1/portfolio")

    @task(2)
    def list_reports(self) -> None:
        self.client.get("/v1/reports", headers=self._auth, name="/v1/reports")

    @task(1)
    def get_valuation(self) -> None:
        self.client.get(
            f"/v1/valuation/{self.project_id}",
            headers=self._auth,
            name="/v1/valuation/[id]",
        )

    @task(1)
    def list_notifications(self) -> None:
        self.client.get(
            "/v1/notifications", headers=self._auth, name="/v1/notifications"
        )

    @task(1)
    def list_watchlists(self) -> None:
        self.client.get(
            "/v1/watchlists", headers=self._auth, name="/v1/watchlists"
        )
