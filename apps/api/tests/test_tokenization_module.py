"""Unit tests for the tokenization module — no DB or network required."""

from __future__ import annotations

import inspect
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.tokenization import (
    TokenHolding,
    TokenizationRecord,
    TokenizationStatus,
    TokenTransfer,
    TransferType,
)
from app.modules.tokenization import service as tok_service
from app.modules.tokenization.schemas import (
    HoldingRequest,
    StatusUpdateRequest,
    TokenizationRequest,
    TransferRequest,
)

# ── Helpers ─────────────────────────────────────────────────────────────────────


def _make_record(
    org_id: uuid.UUID | None = None,
    project_id: uuid.UUID | None = None,
    token_symbol: str = "SCR",
    total_supply: Decimal = Decimal("1000000"),
    token_price_usd: Decimal = Decimal("1.00"),
    status: str = TokenizationStatus.DRAFT.value,
    holdings: list[TokenHolding] | None = None,
) -> TokenizationRecord:
    now = datetime.now(UTC)
    r = TokenizationRecord()
    r.id = uuid.uuid4()
    r.org_id = org_id or uuid.uuid4()
    r.project_id = project_id or uuid.uuid4()
    r.token_name = "SCR Token"
    r.token_symbol = token_symbol
    r.total_supply = total_supply
    r.token_price_usd = token_price_usd
    r.blockchain = "Ethereum"
    r.token_type = "security"
    r.regulatory_framework = "Reg D"
    r.minimum_investment_usd = Decimal("1000")
    r.lock_up_period_days = 365
    r.status = status
    r.status_changed_at = now
    r.created_by = uuid.uuid4()
    r.created_at = now
    r.updated_at = now
    r.is_deleted = False
    r.record_metadata = {}
    r.holdings = holdings or []
    r.transfers = []
    return r


def _make_holding(
    tokenization_id: uuid.UUID | None = None,
    holder_name: str = "Founders",
    tokens: Decimal = Decimal("600000"),
    percentage: Decimal = Decimal("60.00"),
) -> TokenHolding:
    now = datetime.now(UTC)
    h = TokenHolding()
    h.id = uuid.uuid4()
    h.tokenization_id = tokenization_id or uuid.uuid4()
    h.holder_name = holder_name
    h.holder_type = "GP"
    h.tokens = tokens
    h.percentage = percentage
    h.locked_until = None
    h.created_at = now
    h.updated_at = now
    h.is_deleted = False
    h.outgoing_transfers = []
    h.incoming_transfers = []
    return h


# ── Schema validation ───────────────────────────────────────────────────────────


class TestTokenizationRequest:
    def test_valid_request_with_holdings(self):
        req = TokenizationRequest(
            project_id=uuid.uuid4(),
            token_name="SCR Token",
            token_symbol="SCR",
            total_supply=Decimal("1000000"),
            token_price_usd=Decimal("1.00"),
            holdings=[
                HoldingRequest(
                    holder_name="Founders",
                    holder_type="GP",
                    tokens=Decimal("600000"),
                    percentage=Decimal("60"),
                ),
                HoldingRequest(
                    holder_name="Treasury",
                    holder_type="Institutional",
                    tokens=Decimal("200000"),
                    percentage=Decimal("20"),
                ),
                HoldingRequest(
                    holder_name="Investors",
                    holder_type="LP",
                    tokens=Decimal("200000"),
                    percentage=Decimal("20"),
                ),
            ],
        )
        assert req.token_symbol == "SCR"

    def test_holdings_must_sum_to_100(self):
        with pytest.raises(ValueError, match="sum to 100"):
            TokenizationRequest(
                project_id=uuid.uuid4(),
                token_name="SCR Token",
                token_symbol="SCR",
                total_supply=Decimal("1000000"),
                token_price_usd=Decimal("1.00"),
                holdings=[
                    HoldingRequest(
                        holder_name="Founders",
                        holder_type="GP",
                        tokens=Decimal("600000"),
                        percentage=Decimal("60"),
                    ),
                    HoldingRequest(
                        holder_name="Investors",
                        holder_type="LP",
                        tokens=Decimal("200000"),
                        percentage=Decimal("30"),
                    ),
                ],
            )

    def test_holdings_sum_tolerance(self):
        """Percentages within 0.01 of 100 should pass."""
        req = TokenizationRequest(
            project_id=uuid.uuid4(),
            token_name="SCR Token",
            token_symbol="SCR",
            total_supply=Decimal("1000000"),
            token_price_usd=Decimal("1.00"),
            holdings=[
                HoldingRequest(
                    holder_name="A",
                    holder_type="GP",
                    tokens=Decimal("1"),
                    percentage=Decimal("99.995"),
                ),
                HoldingRequest(
                    holder_name="B",
                    holder_type="LP",
                    tokens=Decimal("1"),
                    percentage=Decimal("0.005"),
                ),
            ],
        )
        assert req.holdings is not None

    def test_token_symbol_uppercased(self):
        req = TokenizationRequest(
            project_id=uuid.uuid4(),
            token_name="Token",
            token_symbol="scr",
            total_supply=Decimal("100"),
            token_price_usd=Decimal("1"),
        )
        assert req.token_symbol == "SCR"

    def test_token_symbol_max_10_chars(self):
        with pytest.raises(ValueError, match="10 characters"):
            TokenizationRequest(
                project_id=uuid.uuid4(),
                token_name="Token",
                token_symbol="TOOLONGSYMBOL",
                total_supply=Decimal("100"),
                token_price_usd=Decimal("1"),
            )

    def test_total_supply_must_be_positive(self):
        with pytest.raises(ValueError, match="positive"):
            TokenizationRequest(
                project_id=uuid.uuid4(),
                token_name="Token",
                token_symbol="SCR",
                total_supply=Decimal("0"),
                token_price_usd=Decimal("1"),
            )

    def test_no_holdings_is_valid(self):
        """Holdings are optional — default cap table will be generated."""
        req = TokenizationRequest(
            project_id=uuid.uuid4(),
            token_name="Token",
            token_symbol="SCR",
            total_supply=Decimal("1000000"),
            token_price_usd=Decimal("1"),
        )
        assert req.holdings is None


class TestHoldingRequest:
    def test_negative_tokens_rejected(self):
        with pytest.raises(ValueError, match="positive"):
            HoldingRequest(
                holder_name="A", holder_type="GP", tokens=Decimal("-1"), percentage=Decimal("100")
            )

    def test_zero_percentage_rejected(self):
        with pytest.raises(ValueError, match="positive"):
            HoldingRequest(
                holder_name="A", holder_type="GP", tokens=Decimal("100"), percentage=Decimal("0")
            )


class TestTransferRequest:
    def test_mint_requires_to_holding(self):
        with pytest.raises(ValueError, match="to_holding_id"):
            TransferRequest(amount=Decimal("100"), transfer_type=TransferType.MINT)

    def test_burn_requires_from_holding(self):
        with pytest.raises(ValueError, match="from_holding_id"):
            TransferRequest(amount=Decimal("100"), transfer_type=TransferType.BURN)

    def test_transfer_requires_both_sides(self):
        with pytest.raises(ValueError, match="from_holding_id and to_holding_id"):
            TransferRequest(
                amount=Decimal("100"),
                transfer_type=TransferType.TRANSFER,
                from_holding_id=uuid.uuid4(),
            )

    def test_amount_must_be_positive(self):
        with pytest.raises(ValueError, match="positive"):
            TransferRequest(
                amount=Decimal("0"),
                transfer_type=TransferType.MINT,
                to_holding_id=uuid.uuid4(),
            )

    def test_valid_mint(self):
        r = TransferRequest(
            amount=Decimal("1000"),
            transfer_type=TransferType.MINT,
            to_holding_id=uuid.uuid4(),
        )
        assert r.transfer_type == TransferType.MINT

    def test_valid_transfer(self):
        r = TransferRequest(
            amount=Decimal("100"),
            transfer_type=TransferType.TRANSFER,
            from_holding_id=uuid.uuid4(),
            to_holding_id=uuid.uuid4(),
        )
        assert r.from_holding_id is not None


# ── Default cap table ───────────────────────────────────────────────────────────


class TestDefaultHoldings:
    def test_three_tranches(self):
        holdings = tok_service._default_holdings(Decimal("1000000"), 365)
        assert len(holdings) == 3

    def test_percentages_sum_to_100(self):
        holdings = tok_service._default_holdings(Decimal("1000000"), 365)
        total = sum(h.percentage for h in holdings)
        assert total == Decimal("100")

    def test_token_totals_match_supply(self):
        total_supply = Decimal("1000000")
        holdings = tok_service._default_holdings(total_supply, 365)
        total_tokens = sum(h.tokens for h in holdings)
        assert total_tokens == total_supply

    def test_founders_60_percent(self):
        holdings = tok_service._default_holdings(Decimal("1000000"), 365)
        founders = next(h for h in holdings if h.holder_name == "Founders")
        assert founders.percentage == Decimal("60")

    def test_founders_have_lock_up(self):
        holdings = tok_service._default_holdings(Decimal("1000000"), 180)
        founders = next(h for h in holdings if h.holder_name == "Founders")
        assert founders.locked_until is not None


# ── record_to_response ──────────────────────────────────────────────────────────


class TestRecordToResponse:
    def test_market_cap_computed(self):
        record = _make_record(total_supply=Decimal("1000000"), token_price_usd=Decimal("2.50"))
        resp = tok_service._record_to_response(record)
        assert resp.market_cap_usd == Decimal("2500000.00")

    def test_holdings_included(self):
        h = _make_holding()
        record = _make_record(holdings=[h])
        resp = tok_service._record_to_response(record)
        assert len(resp.holdings) == 1
        assert resp.holdings[0].holder_name == "Founders"

    def test_status_passed_through(self):
        record = _make_record(status=TokenizationStatus.ACTIVE.value)
        resp = tok_service._record_to_response(record)
        assert resp.status == "active"


# ── create_tokenization ─────────────────────────────────────────────────────────


class TestCreateTokenization:
    def _make_db(self, project_exists: bool = True) -> AsyncMock:
        db = AsyncMock()
        project = MagicMock() if project_exists else None
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = project
        db.execute.return_value = execute_result
        db.add = MagicMock()  # session.add is synchronous
        db.flush = AsyncMock()
        db.refresh = AsyncMock()
        return db

    @pytest.mark.asyncio
    async def test_project_not_found_raises(self):
        db = self._make_db(project_exists=False)
        with pytest.raises(LookupError, match="Project not found"):
            await tok_service.create_tokenization(
                db,
                uuid.uuid4(),
                uuid.uuid4(),
                TokenizationRequest(
                    project_id=uuid.uuid4(),
                    token_name="SCR",
                    token_symbol="SCR",
                    total_supply=Decimal("1000000"),
                    token_price_usd=Decimal("1"),
                ),
            )

    @pytest.mark.asyncio
    async def test_creates_record_and_holdings(self):
        """create_tokenization must call db.add for the record, holdings, and mints."""
        db = self._make_db(project_exists=True)

        added_objects: list = []
        db.add.side_effect = lambda obj: (added_objects.append(obj), None)[1]

        # Patch _record_to_response to avoid fully hydrated ORM object requirement
        with patch.object(tok_service, "_record_to_response") as mock_resp:
            mock_resp.return_value = MagicMock()
            await tok_service.create_tokenization(
                db,
                uuid.uuid4(),
                uuid.uuid4(),
                TokenizationRequest(
                    project_id=uuid.uuid4(),
                    token_name="SCR Token",
                    token_symbol="SCR",
                    total_supply=Decimal("1000000"),
                    token_price_usd=Decimal("1"),
                ),
            )

        tokenization_records = [o for o in added_objects if isinstance(o, TokenizationRecord)]
        holding_records = [o for o in added_objects if isinstance(o, TokenHolding)]
        transfer_records = [o for o in added_objects if isinstance(o, TokenTransfer)]

        assert len(tokenization_records) == 1
        assert len(holding_records) == 3  # default 3-tranche cap table
        assert len(transfer_records) == 3  # one mint per holding

    @pytest.mark.asyncio
    async def test_custom_holdings_used_when_provided(self):
        db = self._make_db(project_exists=True)
        added_objects: list = []
        db.add.side_effect = lambda obj: added_objects.append(obj)

        with patch.object(tok_service, "_record_to_response"):
            await tok_service.create_tokenization(
                db,
                uuid.uuid4(),
                uuid.uuid4(),
                TokenizationRequest(
                    project_id=uuid.uuid4(),
                    token_name="Token",
                    token_symbol="TKN",
                    total_supply=Decimal("100"),
                    token_price_usd=Decimal("1"),
                    holdings=[
                        HoldingRequest(
                            holder_name="A",
                            holder_type="GP",
                            tokens=Decimal("50"),
                            percentage=Decimal("50"),
                        ),
                        HoldingRequest(
                            holder_name="B",
                            holder_type="LP",
                            tokens=Decimal("50"),
                            percentage=Decimal("50"),
                        ),
                    ],
                ),
            )

        holding_records = [o for o in added_objects if isinstance(o, TokenHolding)]
        assert len(holding_records) == 2  # caller supplied 2 holdings

    @pytest.mark.asyncio
    async def test_mint_transfers_have_no_from_holding(self):
        db = self._make_db(project_exists=True)
        added_objects: list = []
        db.add.side_effect = lambda obj: added_objects.append(obj)

        with patch.object(tok_service, "_record_to_response"):
            await tok_service.create_tokenization(
                db,
                uuid.uuid4(),
                uuid.uuid4(),
                TokenizationRequest(
                    project_id=uuid.uuid4(),
                    token_name="Token",
                    token_symbol="TKN",
                    total_supply=Decimal("1000"),
                    token_price_usd=Decimal("1"),
                ),
            )

        mints = [o for o in added_objects if isinstance(o, TokenTransfer)]
        for mint in mints:
            assert mint.from_holding_id is None
            assert mint.transfer_type == TransferType.MINT.value


# ── add_transfer ────────────────────────────────────────────────────────────────


class TestAddTransfer:
    def _make_db_with_record(self, record: TokenizationRecord) -> AsyncMock:
        db = AsyncMock()
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = record
        db.execute.return_value = execute_result
        db.add = MagicMock()
        db.flush = AsyncMock()

        async def _refresh(obj: object) -> None:
            if isinstance(obj, TokenTransfer):
                obj.id = uuid.uuid4()
                obj.created_at = datetime.now(UTC)

        db.refresh = _refresh
        return db

    @pytest.mark.asyncio
    async def test_transfer_creates_immutable_record(self):
        record = _make_record()
        from_h = _make_holding(
            tokenization_id=record.id, tokens=Decimal("600000"), percentage=Decimal("60")
        )
        to_h = _make_holding(
            tokenization_id=record.id,
            holder_name="Investors",
            tokens=Decimal("200000"),
            percentage=Decimal("20"),
        )
        record.holdings = [from_h, to_h]

        db = self._make_db_with_record(record)

        req = TransferRequest(
            amount=Decimal("100"),
            transfer_type=TransferType.TRANSFER,
            from_holding_id=from_h.id,
            to_holding_id=to_h.id,
        )
        await tok_service.add_transfer(db, record.org_id, record.id, req, uuid.uuid4())

        added = [c.args[0] for c in db.add.call_args_list]
        transfers = [o for o in added if isinstance(o, TokenTransfer)]
        assert len(transfers) == 1

    @pytest.mark.asyncio
    async def test_transfer_updates_holding_balances(self):
        record = _make_record(total_supply=Decimal("1000"))
        from_h = _make_holding(
            tokenization_id=record.id, tokens=Decimal("600"), percentage=Decimal("60")
        )
        to_h = _make_holding(
            tokenization_id=record.id,
            holder_name="Investors",
            tokens=Decimal("200"),
            percentage=Decimal("20"),
        )
        record.holdings = [from_h, to_h]

        db = self._make_db_with_record(record)

        req = TransferRequest(
            amount=Decimal("100"),
            transfer_type=TransferType.TRANSFER,
            from_holding_id=from_h.id,
            to_holding_id=to_h.id,
        )
        await tok_service.add_transfer(db, record.org_id, record.id, req, uuid.uuid4())

        assert from_h.tokens == Decimal("500")
        assert to_h.tokens == Decimal("300")

    @pytest.mark.asyncio
    async def test_transfer_invalid_from_holding_raises(self):
        record = _make_record()
        record.holdings = []

        db = self._make_db_with_record(record)

        req = TransferRequest(
            amount=Decimal("100"),
            transfer_type=TransferType.TRANSFER,
            from_holding_id=uuid.uuid4(),
            to_holding_id=uuid.uuid4(),
        )
        with pytest.raises(LookupError, match="from_holding_id"):
            await tok_service.add_transfer(db, record.org_id, record.id, req, uuid.uuid4())

    @pytest.mark.asyncio
    async def test_token_transfer_is_append_only(self):
        """TokenTransfer extends TimestampedModel — no updated_at, no is_deleted."""
        from app.models.base import TimestampedModel

        assert issubclass(TokenTransfer, TimestampedModel)
        assert not hasattr(TokenTransfer, "is_deleted")
        assert not hasattr(TokenTransfer, "updated_at")


# ── update_status ───────────────────────────────────────────────────────────────


class TestUpdateStatus:
    @pytest.mark.asyncio
    async def test_status_transition_updates_timestamp(self):
        record = _make_record(status=TokenizationStatus.DRAFT.value)
        old_ts = record.status_changed_at

        db = AsyncMock()
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = record
        db.execute.return_value = execute_result
        db.flush = AsyncMock()
        db.refresh = AsyncMock()

        with patch.object(tok_service, "_record_to_response") as mock_resp:
            mock_resp.return_value = MagicMock()
            await tok_service.update_status(
                db,
                record.org_id,
                record.id,
                StatusUpdateRequest(status=TokenizationStatus.ACTIVE),
            )

        assert record.status == TokenizationStatus.ACTIVE.value
        assert record.status_changed_at >= old_ts

    @pytest.mark.asyncio
    async def test_status_not_found_raises(self):
        db = AsyncMock()
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = None
        db.execute.return_value = execute_result

        with pytest.raises(LookupError, match="not found"):
            await tok_service.update_status(
                db,
                uuid.uuid4(),
                uuid.uuid4(),
                StatusUpdateRequest(status=TokenizationStatus.ACTIVE),
            )


# ── Unique constraint (DB-level guard verified by migration) ────────────────────


class TestUniqueConstraint:
    def test_unique_constraint_defined_on_model(self):
        """The model must declare the (org_id, project_id, token_symbol) unique constraint."""
        constraints = {c.name for c in TokenizationRecord.__table__.constraints}
        assert "uq_tokenization_org_project_symbol" in constraints

    def test_tokenization_status_enum_values(self):
        assert TokenizationStatus.DRAFT.value == "draft"
        assert TokenizationStatus.ACTIVE.value == "active"
        assert TokenizationStatus.PAUSED.value == "paused"
        assert TokenizationStatus.RETIRED.value == "retired"

    def test_transfer_type_enum_values(self):
        assert TransferType.MINT.value == "mint"
        assert TransferType.TRANSFER.value == "transfer"
        assert TransferType.BURN.value == "burn"


# ── No AITaskLog dependency ─────────────────────────────────────────────────────


class TestNoAITaskLogDependency:
    def test_service_does_not_import_ai_task_log(self):
        source = inspect.getsource(tok_service)
        assert "AITaskLog" not in source

    def test_service_does_not_import_ai_agent_type(self):
        source = inspect.getsource(tok_service)
        assert "AIAgentType" not in source

    def test_router_does_not_import_ai_task_log(self):
        import pathlib

        router_file = pathlib.Path(inspect.getfile(tok_service)).parent / "router.py"
        source = router_file.read_text()
        assert "AITaskLog" not in source
