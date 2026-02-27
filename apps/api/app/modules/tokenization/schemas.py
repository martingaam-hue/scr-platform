"""Tokenization schemas — on-chain token lifecycle management."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class TokenizationRequest(BaseModel):
    project_id: uuid.UUID
    token_name: str
    token_symbol: str
    total_supply: int
    token_price_usd: float
    blockchain: str = "Ethereum"       # Ethereum, Polygon, Solana
    token_type: str = "security"       # security, utility, equity
    regulatory_framework: str = "Reg D"  # Reg D, Reg A+, Reg CF, ERC-3643
    minimum_investment_usd: float = 1000.0
    lock_up_period_days: int = 365
    metadata: dict[str, Any] | None = None


class TokenHolding(BaseModel):
    holder_name: str
    holder_type: str        # founder, investor, advisor, treasury
    tokens: int
    percentage: float
    locked_until: str | None


class TokenizationResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    token_name: str
    token_symbol: str
    total_supply: int
    token_price_usd: float
    market_cap_usd: float   # computed
    blockchain: str
    token_type: str
    regulatory_framework: str
    minimum_investment_usd: float
    lock_up_period_days: int
    status: str             # draft, pending_review, active, paused
    cap_table: list[TokenHolding]
    transfer_history: list[dict[str, Any]]
    created_at: datetime
    updated_at: datetime


class TransferRequest(BaseModel):
    from_holder: str
    to_holder: str
    tokens: int
    price_per_token_usd: float | None = None
    notes: str | None = None
