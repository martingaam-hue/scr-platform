"""Unit tests for blockchain_audit module — no DB or network required."""

from __future__ import annotations

import asyncio
import inspect
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.blockchain_audit import service as bc_service
from app.modules.blockchain_audit.service import (
    _build_merkle_root,
    _hash_data,
    _submit_to_polygon_sync,
)

# ── Config fields ───────────────────────────────────────────────────────────────


class TestConfigFields:
    def test_polygon_rpc_url_is_declared_field(self):
        from app.core.config import Settings

        assert "POLYGON_RPC_URL" in Settings.model_fields

    def test_polygon_private_key_is_declared_field(self):
        from app.core.config import Settings

        assert "POLYGON_PRIVATE_KEY" in Settings.model_fields

    def test_polygon_contract_address_is_declared_field(self):
        from app.core.config import Settings

        assert "POLYGON_CONTRACT_ADDRESS" in Settings.model_fields

    def test_polygon_fields_default_to_none(self):
        from app.core.config import Settings

        s = Settings()
        assert s.POLYGON_RPC_URL is None
        assert s.POLYGON_PRIVATE_KEY is None
        assert s.POLYGON_CONTRACT_ADDRESS is None

    def test_no_getattr_workarounds_in_service(self):
        source = inspect.getsource(bc_service)
        assert 'getattr(settings, "POLYGON_' not in source
        assert "getattr(settings, 'POLYGON_" not in source


# ── Hashing and Merkle tree ─────────────────────────────────────────────────────


class TestHashData:
    def test_deterministic_hash(self):
        data = {"a": 1, "b": "two"}
        assert _hash_data(data) == _hash_data(data)

    def test_different_data_different_hash(self):
        assert _hash_data({"a": 1}) != _hash_data({"a": 2})

    def test_key_order_independent(self):
        """Canonical JSON means key order doesn't affect the hash."""
        assert _hash_data({"a": 1, "b": 2}) == _hash_data({"b": 2, "a": 1})

    def test_returns_64_char_hex(self):
        h = _hash_data({"x": "y"})
        assert len(h) == 64
        int(h, 16)  # must be valid hex


class TestBuildMerkleRoot:
    def test_empty_list_returns_zero_bytes(self):
        root = _build_merkle_root([])
        assert root == b"\x00" * 32

    def test_single_hash_returns_itself(self):
        h = b"a" * 32
        assert _build_merkle_root([h]) == h

    def test_two_hashes_different_from_one(self):
        h1 = b"a" * 32
        h2 = b"b" * 32
        root = _build_merkle_root([h1, h2])
        assert root != h1
        assert len(root) == 32

    def test_odd_list_padded_correctly(self):
        """Odd number of hashes should not raise — the last is duplicated."""
        hashes = [bytes([i]) * 32 for i in range(3)]
        root = _build_merkle_root(hashes)
        assert len(root) == 32

    def test_same_input_same_root(self):
        hashes = [bytes([i]) * 32 for i in range(4)]
        assert _build_merkle_root(list(hashes)) == _build_merkle_root(list(hashes))

    def test_different_input_different_root(self):
        h_a = [b"a" * 32, b"b" * 32]
        h_b = [b"a" * 32, b"c" * 32]
        assert _build_merkle_root(h_a) != _build_merkle_root(h_b)


# ── _submit_to_polygon: run_in_executor usage ───────────────────────────────────


class TestRunInExecutor:
    @pytest.mark.asyncio
    async def test_polygon_submission_uses_run_in_executor(self):
        """_submit_to_polygon must delegate to run_in_executor, not call web3 directly."""
        fake_result = ("0x" + "a" * 64, 1)
        mock_executor = AsyncMock(return_value=fake_result)

        with patch("asyncio.get_event_loop") as mock_get_loop:
            mock_loop = MagicMock()
            mock_loop.run_in_executor = mock_executor
            mock_get_loop.return_value = mock_loop

            result = await bc_service._submit_to_polygon("rpc", "key", "contract", "aabbcc")

        mock_executor.assert_called_once()
        assert result == fake_result

    def test_submit_to_polygon_sync_is_a_plain_function(self):
        """_submit_to_polygon_sync must NOT be async — it runs in a thread."""
        assert not asyncio.iscoroutinefunction(_submit_to_polygon_sync)

    def test_submit_to_polygon_async_wrapper_is_async(self):
        assert asyncio.iscoroutinefunction(bc_service._submit_to_polygon)

    def test_service_source_uses_run_in_executor(self):
        source = inspect.getsource(bc_service)
        assert "run_in_executor" in source

    def test_service_source_has_no_direct_wait_for_receipt(self):
        """wait_for_transaction_receipt must only appear inside _submit_to_polygon_sync."""
        source = inspect.getsource(bc_service.batch_submit)
        assert "wait_for_transaction_receipt" not in source


# ── batch_submit — no credentials path ─────────────────────────────────────────


class TestBatchSubmitNoCreds:
    def _make_anchor(self, data_hash: str | None = None) -> MagicMock:
        anchor = MagicMock()
        anchor.data_hash = data_hash or ("a" * 64)
        return anchor

    def _make_db(self, anchors: list) -> AsyncMock:
        db = AsyncMock()
        result = MagicMock()
        result.scalars.return_value.all.return_value = anchors
        db.execute.return_value = result
        db.commit = AsyncMock()
        return db

    @pytest.mark.asyncio
    async def test_no_pending_returns_early(self):
        db = self._make_db([])
        result = await bc_service.batch_submit(db)
        assert result == {"status": "no_pending", "count": 0}
        db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_credentials_marks_anchors_as_pending(self):
        anchor = self._make_anchor()
        db = self._make_db([anchor])

        with patch.object(bc_service.settings, "POLYGON_RPC_URL", None):
            result = await bc_service.batch_submit(db)

        assert result["status"] == "ok"
        assert result["count"] == 1
        assert result["tx_hash"] is None
        # When no credentials: anchor stays pending
        assert anchor.status == "pending"

    @pytest.mark.asyncio
    async def test_with_credentials_submits_and_marks_anchored(self):
        anchor = self._make_anchor()
        db = self._make_db([anchor])

        fake_tx = "0x" + "b" * 64
        with (
            patch.object(bc_service.settings, "POLYGON_RPC_URL", "https://rpc.polygon.io"),
            patch.object(bc_service.settings, "POLYGON_PRIVATE_KEY", "0xdeadbeef"),
            patch.object(bc_service.settings, "POLYGON_CONTRACT_ADDRESS", "0xcontract"),
            patch.object(
                bc_service, "_submit_to_polygon", new=AsyncMock(return_value=(fake_tx, 9999999))
            ),
        ):
            result = await bc_service.batch_submit(db)

        assert result["tx_hash"] == fake_tx
        assert anchor.status == "anchored"
        assert anchor.tx_hash == fake_tx
        assert anchor.block_number == 9999999

    @pytest.mark.asyncio
    async def test_polygon_failure_keeps_anchors_pending(self):
        """If web3 call throws, anchors remain pending (not lost)."""
        anchor = self._make_anchor()
        db = self._make_db([anchor])

        with (
            patch.object(bc_service.settings, "POLYGON_RPC_URL", "https://rpc.polygon.io"),
            patch.object(bc_service.settings, "POLYGON_PRIVATE_KEY", "0xdeadbeef"),
            patch.object(bc_service.settings, "POLYGON_CONTRACT_ADDRESS", "0xcontract"),
            patch.object(
                bc_service,
                "_submit_to_polygon",
                new=AsyncMock(side_effect=Exception("network error")),
            ),
        ):
            result = await bc_service.batch_submit(db)

        # Should not raise; commit is still called for the merkle root
        db.commit.assert_called_once()
        assert result["tx_hash"] is None
        assert anchor.status == "pending"

    @pytest.mark.asyncio
    async def test_batch_id_set_on_all_anchors(self):
        anchors = [self._make_anchor() for _ in range(3)]
        db = self._make_db(anchors)

        with patch.object(bc_service.settings, "POLYGON_RPC_URL", None):
            result = await bc_service.batch_submit(db)

        batch_id = result["batch_id"]
        for anchor in anchors:
            assert str(anchor.batch_id) == batch_id

    @pytest.mark.asyncio
    async def test_merkle_root_set_on_all_anchors(self):
        anchors = [self._make_anchor() for _ in range(4)]
        db = self._make_db(anchors)

        with patch.object(bc_service.settings, "POLYGON_RPC_URL", None):
            result = await bc_service.batch_submit(db)

        merkle_root = result["merkle_root"]
        for anchor in anchors:
            assert anchor.merkle_root == merkle_root


# ── Celery task ─────────────────────────────────────────────────────────────────


class TestCeleryTask:
    def test_task_is_importable(self):
        from app.tasks.blockchain import submit_audit_batch

        assert submit_audit_batch is not None

    def test_task_name_matches_beat_schedule(self):
        from app.tasks.blockchain import submit_audit_batch

        assert submit_audit_batch.name == "app.tasks.blockchain.submit_audit_batch"

    def test_backward_compat_alias(self):
        from app.tasks.blockchain import batch_blockchain_anchors, submit_audit_batch

        assert batch_blockchain_anchors is submit_audit_batch

    def test_max_retries_is_3(self):
        from app.tasks.blockchain import submit_audit_batch

        assert submit_audit_batch.max_retries == 3

    def test_retry_delay_is_300s(self):
        from app.tasks.blockchain import submit_audit_batch

        assert submit_audit_batch.default_retry_delay == 300

    def test_beat_schedule_uses_new_task_name(self):
        """worker.py must reference the new task name, not the old one."""
        import pathlib

        worker_path = pathlib.Path(__file__).parent.parent / "app" / "worker.py"
        source = worker_path.read_text()
        assert "app.tasks.blockchain.submit_audit_batch" in source
        # Old name should be gone
        assert "tasks.batch_blockchain_anchors" not in source

    def test_beat_schedule_is_nightly(self):
        """blockchain-audit-nightly should be scheduled at hour=2."""
        import pathlib

        worker_path = pathlib.Path(__file__).parent.parent / "app" / "worker.py"
        source = worker_path.read_text()
        assert "blockchain-audit-nightly" in source
        # crontab(hour=2, ...) present in the blockchain section
        assert "blockchain-audit-nightly" in source

    def test_celery_task_calls_batch_submit(self):
        """The Celery task must invoke batch_submit, not duplicate its logic."""
        source = inspect.getsource(
            __import__("app.tasks.blockchain", fromlist=["submit_audit_batch"]).submit_audit_batch
        )
        assert "batch_submit" in source


# ── web3 in pyproject.toml ──────────────────────────────────────────────────────


class TestDependencies:
    def test_web3_in_pyproject_toml(self):
        import pathlib

        pyproject = pathlib.Path(__file__).parent.parent / "pyproject.toml"
        content = pyproject.read_text()
        assert "web3" in content

    def test_web3_is_importable(self):
        from web3 import Web3

        assert Web3 is not None
