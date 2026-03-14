"""Tokenization service — proper data model, immutable transfer audit trail."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.projects import Project
from app.models.tokenization import (
    TokenHolding,
    TokenizationRecord,
    TokenizationStatus,
    TokenTransfer,
    TransferType,
)
from app.modules.tokenization.schemas import (
    HoldingRequest,
    HoldingResponse,
    StatusUpdateRequest,
    TokenizationRequest,
    TokenizationResponse,
    TransferRequest,
    TransferResponse,
)


def _default_holdings(total_supply: Decimal, lock_up_days: int) -> list[HoldingRequest]:
    """Generate a default 60/20/20 cap table if the caller didn't supply one."""
    locked_until = datetime.now(UTC) + timedelta(days=lock_up_days)
    return [
        HoldingRequest(
            holder_name="Founders",
            holder_type="GP",
            tokens=total_supply * Decimal("0.60"),
            percentage=Decimal("60"),
            locked_until=locked_until,
        ),
        HoldingRequest(
            holder_name="Treasury",
            holder_type="Institutional",
            tokens=total_supply * Decimal("0.20"),
            percentage=Decimal("20"),
            locked_until=None,
        ),
        HoldingRequest(
            holder_name="Investors",
            holder_type="LP",
            tokens=total_supply * Decimal("0.20"),
            percentage=Decimal("20"),
            locked_until=None,
        ),
    ]


def _record_to_response(record: TokenizationRecord) -> TokenizationResponse:
    holdings = [HoldingResponse.model_validate(h) for h in (record.holdings or [])]
    return TokenizationResponse(
        id=record.id,
        org_id=record.org_id,
        project_id=record.project_id,
        token_name=record.token_name,
        token_symbol=record.token_symbol,
        total_supply=Decimal(str(record.total_supply)),
        token_price_usd=Decimal(str(record.token_price_usd)),
        market_cap_usd=Decimal(str(record.total_supply)) * Decimal(str(record.token_price_usd)),
        blockchain=record.blockchain,
        token_type=record.token_type,
        regulatory_framework=record.regulatory_framework,
        minimum_investment_usd=Decimal(str(record.minimum_investment_usd)),
        lock_up_period_days=record.lock_up_period_days,
        status=record.status,
        status_changed_at=record.status_changed_at,
        created_by=record.created_by,
        created_at=record.created_at,
        updated_at=record.updated_at,
        holdings=holdings,
    )


async def _load_record(
    db: AsyncSession,
    org_id: uuid.UUID,
    record_id: uuid.UUID,
) -> TokenizationRecord:
    stmt = (
        select(TokenizationRecord)
        .options(
            selectinload(TokenizationRecord.holdings),
        )
        .where(
            TokenizationRecord.id == record_id,
            TokenizationRecord.org_id == org_id,
            TokenizationRecord.is_deleted.is_(False),
        )
    )
    record: TokenizationRecord | None = (await db.execute(stmt)).scalar_one_or_none()
    if not record:
        raise LookupError("Tokenization record not found")
    return record


async def create_tokenization(
    db: AsyncSession,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    body: TokenizationRequest,
) -> TokenizationResponse:
    """Create a TokenizationRecord + initial TokenHolding rows + mint TokenTransfers."""
    stmt = select(Project).where(
        Project.id == body.project_id,
        Project.org_id == org_id,
        Project.is_deleted.is_(False),
    )
    project: Project | None = (await db.execute(stmt)).scalar_one_or_none()
    if not project:
        raise LookupError("Project not found")

    now = datetime.now(UTC)
    record = TokenizationRecord(
        org_id=org_id,
        project_id=body.project_id,
        token_name=body.token_name,
        token_symbol=body.token_symbol,
        total_supply=body.total_supply,
        token_price_usd=body.token_price_usd,
        blockchain=body.blockchain,
        token_type=body.token_type,
        regulatory_framework=body.regulatory_framework,
        minimum_investment_usd=body.minimum_investment_usd,
        lock_up_period_days=body.lock_up_period_days,
        status=TokenizationStatus.DRAFT.value,
        status_changed_at=now,
        created_by=user_id,
        record_metadata=body.metadata or {},
    )
    db.add(record)
    await db.flush()

    holding_specs = body.holdings or _default_holdings(body.total_supply, body.lock_up_period_days)
    holding_objs: list[TokenHolding] = []
    for spec in holding_specs:
        holding = TokenHolding(
            tokenization_id=record.id,
            holder_name=spec.holder_name,
            holder_type=spec.holder_type,
            tokens=spec.tokens,
            percentage=spec.percentage,
            locked_until=spec.locked_until,
        )
        db.add(holding)
        holding_objs.append(holding)

    await db.flush()

    # Mint record for each initial holding (immutable audit trail)
    for holding in holding_objs:
        mint = TokenTransfer(
            tokenization_id=record.id,
            from_holding_id=None,
            to_holding_id=holding.id,
            amount=holding.tokens,
            transfer_type=TransferType.MINT.value,
            executed_at=now,
            executed_by=user_id,
        )
        db.add(mint)

    await db.flush()
    await db.refresh(record)
    return _record_to_response(record)


async def get_tokenization(
    db: AsyncSession,
    org_id: uuid.UUID,
    record_id: uuid.UUID,
) -> TokenizationResponse | None:
    """Get a single tokenization record by its ID."""
    stmt = (
        select(TokenizationRecord)
        .options(selectinload(TokenizationRecord.holdings))
        .where(
            TokenizationRecord.id == record_id,
            TokenizationRecord.org_id == org_id,
            TokenizationRecord.is_deleted.is_(False),
        )
    )
    record: TokenizationRecord | None = (await db.execute(stmt)).scalar_one_or_none()
    if not record:
        return None
    return _record_to_response(record)


async def list_tokenizations(
    db: AsyncSession,
    org_id: uuid.UUID,
) -> list[TokenizationResponse]:
    """List all active tokenization records for an org."""
    stmt = (
        select(TokenizationRecord)
        .options(selectinload(TokenizationRecord.holdings))
        .where(
            TokenizationRecord.org_id == org_id,
            TokenizationRecord.is_deleted.is_(False),
        )
        .order_by(TokenizationRecord.created_at.desc())
    )
    rows = (await db.execute(stmt)).scalars().all()
    return [_record_to_response(r) for r in rows]


async def add_transfer(
    db: AsyncSession,
    org_id: uuid.UUID,
    record_id: uuid.UUID,
    body: TransferRequest,
    user_id: uuid.UUID,
) -> TransferResponse:
    """Create an immutable TokenTransfer and update affected holdings."""
    record = await _load_record(db, org_id, record_id)

    # Validate that referenced holdings belong to this tokenization
    if body.from_holding_id:
        from_h = next((h for h in record.holdings if h.id == body.from_holding_id), None)
        if not from_h:
            raise LookupError("from_holding_id not found on this tokenization")
    if body.to_holding_id:
        to_h = next((h for h in record.holdings if h.id == body.to_holding_id), None)
        if not to_h:
            raise LookupError("to_holding_id not found on this tokenization")

    now = datetime.now(UTC)
    transfer = TokenTransfer(
        tokenization_id=record.id,
        from_holding_id=body.from_holding_id,
        to_holding_id=body.to_holding_id,
        amount=body.amount,
        transfer_type=body.transfer_type.value,
        executed_at=now,
        executed_by=user_id,
        tx_hash=body.tx_hash,
    )
    db.add(transfer)

    # Update current holdings (transfers are the source of truth, but we maintain
    # denormalised current balances for fast reads)
    if body.transfer_type == TransferType.TRANSFER and body.from_holding_id and body.to_holding_id:
        from_h = next(h for h in record.holdings if h.id == body.from_holding_id)
        to_h = next(h for h in record.holdings if h.id == body.to_holding_id)
        from_h.tokens = Decimal(str(from_h.tokens)) - body.amount
        to_h.tokens = Decimal(str(to_h.tokens)) + body.amount
        # Recalculate percentages
        total = Decimal(str(record.total_supply))
        if total > 0:
            from_h.percentage = (Decimal(str(from_h.tokens)) / total * 100).quantize(
                Decimal("0.01")
            )
            to_h.percentage = (Decimal(str(to_h.tokens)) / total * 100).quantize(Decimal("0.01"))
    elif body.transfer_type == TransferType.BURN and body.from_holding_id:
        from_h = next(h for h in record.holdings if h.id == body.from_holding_id)
        from_h.tokens = Decimal(str(from_h.tokens)) - body.amount

    await db.flush()
    await db.refresh(transfer)
    return TransferResponse.model_validate(transfer)


async def update_status(
    db: AsyncSession,
    org_id: uuid.UUID,
    record_id: uuid.UUID,
    body: StatusUpdateRequest,
) -> TokenizationResponse:
    """Update the status and record the timestamp of the transition."""
    record = await _load_record(db, org_id, record_id)
    record.status = body.status.value
    record.status_changed_at = datetime.now(UTC)
    await db.flush()
    await db.refresh(record)
    return _record_to_response(record)
