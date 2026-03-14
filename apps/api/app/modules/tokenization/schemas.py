"""Tokenization schemas — on-chain token lifecycle management."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, field_validator, model_validator

from app.models.tokenization import TokenizationStatus, TransferType

# ── Request schemas ─────────────────────────────────────────────────────────────


class HoldingRequest(BaseModel):
    holder_name: str
    holder_type: str  # GP, LP, Institutional, Developer, Sponsor
    tokens: Decimal
    percentage: Decimal
    locked_until: datetime | None = None

    @field_validator("tokens")
    @classmethod
    def tokens_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("tokens must be positive")
        return v

    @field_validator("percentage")
    @classmethod
    def percentage_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("percentage must be positive")
        return v


class TokenizationRequest(BaseModel):
    project_id: uuid.UUID
    token_name: str
    token_symbol: str
    total_supply: Decimal
    token_price_usd: Decimal
    blockchain: str = "Ethereum"
    token_type: str = "security"
    regulatory_framework: str = "Reg D"
    minimum_investment_usd: Decimal = Decimal("1000")
    lock_up_period_days: int = 365
    holdings: list[HoldingRequest] | None = None
    metadata: dict[str, Any] | None = None

    @field_validator("total_supply")
    @classmethod
    def total_supply_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("total_supply must be positive")
        return v

    @field_validator("token_symbol")
    @classmethod
    def symbol_max_length(cls, v: str) -> str:
        if len(v) > 10:
            raise ValueError("token_symbol must be 10 characters or fewer")
        return v.upper()

    @model_validator(mode="after")
    def holdings_sum_to_100(self) -> TokenizationRequest:
        if self.holdings is not None:
            total = sum(h.percentage for h in self.holdings)
            if abs(total - Decimal("100")) > Decimal("0.01"):
                raise ValueError(f"holding percentages must sum to 100 (got {total})")
        return self


class TransferRequest(BaseModel):
    from_holding_id: uuid.UUID | None = None
    to_holding_id: uuid.UUID | None = None
    amount: Decimal
    transfer_type: TransferType
    tx_hash: str | None = None

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("amount must be positive")
        return v

    @model_validator(mode="after")
    def validate_transfer_sides(self) -> TransferRequest:
        if self.transfer_type == TransferType.MINT and self.to_holding_id is None:
            raise ValueError("mint transfer requires to_holding_id")
        if self.transfer_type == TransferType.BURN and self.from_holding_id is None:
            raise ValueError("burn transfer requires from_holding_id")
        if self.transfer_type == TransferType.TRANSFER and (
            self.from_holding_id is None or self.to_holding_id is None
        ):
            raise ValueError("transfer requires both from_holding_id and to_holding_id")
        return self


class StatusUpdateRequest(BaseModel):
    status: TokenizationStatus


# ── Response schemas ────────────────────────────────────────────────────────────


class HoldingResponse(BaseModel):
    id: uuid.UUID
    tokenization_id: uuid.UUID
    holder_name: str
    holder_type: str
    tokens: Decimal
    percentage: Decimal
    locked_until: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TransferResponse(BaseModel):
    id: uuid.UUID
    tokenization_id: uuid.UUID
    from_holding_id: uuid.UUID | None
    to_holding_id: uuid.UUID | None
    amount: Decimal
    transfer_type: str
    executed_at: datetime
    executed_by: uuid.UUID
    tx_hash: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenizationResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    project_id: uuid.UUID
    token_name: str
    token_symbol: str
    total_supply: Decimal
    token_price_usd: Decimal
    market_cap_usd: Decimal  # computed: total_supply * token_price_usd
    blockchain: str
    token_type: str
    regulatory_framework: str
    minimum_investment_usd: Decimal
    lock_up_period_days: int
    status: str
    status_changed_at: datetime
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime
    holdings: list[HoldingResponse]

    model_config = {"from_attributes": True}
