"""AI-endpoint load test — lower concurrency, measures latency of AI-backed calls.

Usage:
    poetry run locust -f tests/load/test_ai_latency.py \
        --host=https://api.pampgroup.com \
        --users=10 --spawn-rate=1 --run-time=5m \
        --headless --csv=tests/load/results/ai_latency
"""

from __future__ import annotations

import json
import os
import time
import uuid

from locust import HttpUser, between, task

_TEST_TOKEN = os.getenv("LOAD_TEST_JWT", "")
_TEST_PROJECT_ID = os.getenv("LOAD_TEST_PROJECT_ID", str(uuid.UUID(int=1)))


class AIUser(HttpUser):
    """Simulates users triggering AI-backed operations."""

    # AI calls are expensive — longer wait between requests
    wait_time = between(5, 15)

    def on_start(self) -> None:
        self.token = _TEST_TOKEN
        self.project_id = _TEST_PROJECT_ID
        self._auth = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        # Create a Ralph conversation to reuse across tasks
        self._conversation_id: str | None = None

    # ── Ralph AI ──────────────────────────────────────────────────────────────

    @task(3)
    def ralph_start_conversation(self) -> None:
        """Measure time to create a new Ralph conversation."""
        with self.client.post(
            "/v1/ralph/conversations",
            json={"title": "Load test conversation"},
            headers=self._auth,
            name="/v1/ralph/conversations [POST]",
            catch_response=True,
        ) as resp:
            if resp.status_code == 201:
                data = resp.json()
                self._conversation_id = data.get("id")
                resp.success()
            else:
                resp.failure(f"HTTP {resp.status_code}")

    @task(2)
    def ralph_send_message(self) -> None:
        """Measure time to first response from Ralph AI."""
        if not self._conversation_id:
            return
        start = time.perf_counter()
        with self.client.post(
            f"/v1/ralph/conversations/{self._conversation_id}/message",
            json={"content": "Summarise the key risks for this project."},
            headers=self._auth,
            name="/v1/ralph/[id]/message [POST]",
            catch_response=True,
        ) as resp:
            elapsed_ms = (time.perf_counter() - start) * 1000
            if resp.status_code == 200:
                resp.success()
            elif resp.status_code == 404:
                # Conversation may have expired — reset
                self._conversation_id = None
                resp.success()
            else:
                resp.failure(f"HTTP {resp.status_code} ({elapsed_ms:.0f}ms)")

    # ── Signal Score ──────────────────────────────────────────────────────────

    @task(2)
    def trigger_signal_score(self) -> None:
        """Trigger an async signal score computation and measure queue time."""
        with self.client.post(
            f"/v1/signal-score/{self.project_id}/calculate",
            headers=self._auth,
            name="/v1/signal-score/[id]/calculate [POST]",
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 202):
                resp.success()
            elif resp.status_code == 429:
                resp.success()  # Rate limited — expected under load
            else:
                resp.failure(f"HTTP {resp.status_code}")

    # ── Document analysis ─────────────────────────────────────────────────────

    @task(1)
    def get_ai_feedback(self) -> None:
        """Measure AI feedback retrieval latency."""
        self.client.get(
            f"/v1/ai-feedback/{self.project_id}",
            headers=self._auth,
            name="/v1/ai-feedback/[id]",
        )
