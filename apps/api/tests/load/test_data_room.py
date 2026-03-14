"""Data room load test — uploads, downloads, concurrent access.

Usage:
    poetry run locust -f tests/load/test_data_room.py \
        --host=https://api.pampgroup.com \
        --users=20 --spawn-rate=2 --run-time=5m \
        --headless --csv=tests/load/results/data_room
"""

from __future__ import annotations

import io
import os
import uuid

from locust import HttpUser, between, task

_TEST_TOKEN = os.getenv("LOAD_TEST_JWT", "")
_TEST_PROJECT_ID = os.getenv("LOAD_TEST_PROJECT_ID", str(uuid.UUID(int=1)))
_TEST_DEAL_ROOM_ID = os.getenv("LOAD_TEST_DEAL_ROOM_ID", str(uuid.UUID(int=3)))


def _fake_file(size_bytes: int, filename: str = "test.pdf") -> tuple:
    """Generate an in-memory fake file of the given size."""
    content = b"%PDF-1.4\n" + b"x" * (size_bytes - 9)
    return (filename, io.BytesIO(content), "application/pdf")


class DataRoomUser(HttpUser):
    """Simulates concurrent data room usage: uploads, downloads, listings."""

    wait_time = between(2, 5)

    def on_start(self) -> None:
        self.token = _TEST_TOKEN
        self.project_id = _TEST_PROJECT_ID
        self.deal_room_id = _TEST_DEAL_ROOM_ID
        self._auth = {"Authorization": f"Bearer {self.token}"}
        self._uploaded_doc_id: str | None = None

    # ── Listing (most common) ─────────────────────────────────────────────────

    @task(5)
    def list_documents(self) -> None:
        self.client.get(
            f"/v1/dataroom/{self.project_id}/documents",
            headers=self._auth,
            name="/v1/dataroom/[id]/documents",
        )

    @task(3)
    def list_documents_paginated(self) -> None:
        self.client.get(
            f"/v1/dataroom/{self.project_id}/documents?page=2&page_size=20",
            headers=self._auth,
            name="/v1/dataroom/[id]/documents?page=2",
        )

    # ── Upload ────────────────────────────────────────────────────────────────

    @task(2)
    def upload_small_document(self) -> None:
        """Upload a 1 MB document."""
        with self.client.post(
            f"/v1/dataroom/{self.project_id}/documents",
            files={"file": _fake_file(1024 * 1024, "small.pdf")},
            data={"title": "Load test — 1 MB", "category": "financial"},
            headers=self._auth,
            name="/v1/dataroom/[id]/documents [POST 1MB]",
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 201):
                doc_id = resp.json().get("id")
                if doc_id:
                    self._uploaded_doc_id = doc_id
                resp.success()
            else:
                resp.failure(f"HTTP {resp.status_code}")

    @task(1)
    def upload_medium_document(self) -> None:
        """Upload a 5 MB document."""
        with self.client.post(
            f"/v1/dataroom/{self.project_id}/documents",
            files={"file": _fake_file(5 * 1024 * 1024, "medium.pdf")},
            data={"title": "Load test — 5 MB", "category": "legal"},
            headers=self._auth,
            name="/v1/dataroom/[id]/documents [POST 5MB]",
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 201):
                resp.success()
            else:
                resp.failure(f"HTTP {resp.status_code}")

    @task(1)
    def upload_large_document(self) -> None:
        """Upload a 25 MB document (near the typical deal document size)."""
        with self.client.post(
            f"/v1/dataroom/{self.project_id}/documents",
            files={"file": _fake_file(25 * 1024 * 1024, "large.pdf")},
            data={"title": "Load test — 25 MB", "category": "technical"},
            headers=self._auth,
            name="/v1/dataroom/[id]/documents [POST 25MB]",
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 201):
                resp.success()
            else:
                resp.failure(f"HTTP {resp.status_code}")

    # ── Download ──────────────────────────────────────────────────────────────

    @task(2)
    def get_document_detail(self) -> None:
        if not self._uploaded_doc_id:
            return
        self.client.get(
            f"/v1/dataroom/{self.project_id}/documents/{self._uploaded_doc_id}",
            headers=self._auth,
            name="/v1/dataroom/[id]/documents/[doc_id]",
        )

    # ── Deal room concurrent access ───────────────────────────────────────────

    @task(3)
    def get_deal_room(self) -> None:
        self.client.get(
            f"/v1/deal-rooms/{self.deal_room_id}",
            headers=self._auth,
            name="/v1/deal-rooms/[id]",
        )

    @task(2)
    def list_deal_rooms(self) -> None:
        self.client.get(
            "/v1/deal-rooms",
            headers=self._auth,
            name="/v1/deal-rooms",
        )
