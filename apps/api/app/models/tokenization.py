"""Tokenization models — proper data model for token lifecycle management.

TokenizationRecord  - the tokenization itself (one per project/symbol)
TokenHolding        - current cap table entries (mutable, soft-deletable)
TokenTransfer       - immutable audit log of all mints/burns/transfers
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel, TimestampedModel


class TokenizationStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    RETIRED = "retired"


class TransferType(str, enum.Enum):
    MINT = "mint"
    TRANSFER = "transfer"
    BURN = "burn"


class TokenizationRecord(BaseModel):
    """One tokenization per (org, project, symbol) — unique constraint enforced."""

    __tablename__ = "tokenization_records"
    __table_args__ = (
        UniqueConstraint(
            "org_id", "project_id", "token_symbol", name="uq_tokenization_org_project_symbol"
        ),
        Index("ix_tokenization_records_org_id", "org_id"),
        Index("ix_tokenization_records_project_id", "project_id"),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_name: Mapped[str] = mapped_column(String(255), nullable=False)
    token_symbol: Mapped[str] = mapped_column(String(10), nullable=False)
    total_supply: Mapped[sa.Numeric] = mapped_column(Numeric(19, 4), nullable=False)
    token_price_usd: Mapped[sa.Numeric] = mapped_column(Numeric(19, 4), nullable=False)
    blockchain: Mapped[str] = mapped_column(String(100), nullable=False, server_default="Ethereum")
    token_type: Mapped[str] = mapped_column(String(50), nullable=False, server_default="security")
    regulatory_framework: Mapped[str] = mapped_column(
        String(100), nullable=False, server_default="Reg D"
    )
    minimum_investment_usd: Mapped[sa.Numeric] = mapped_column(
        Numeric(19, 4), nullable=False, server_default="1000"
    )
    lock_up_period_days: Mapped[int] = mapped_column(nullable=False, server_default="365")
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=TokenizationStatus.DRAFT.value
    )
    status_changed_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    record_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)

    # Relationships
    holdings: Mapped[list[TokenHolding]] = relationship(
        "TokenHolding",
        back_populates="tokenization",
        primaryjoin="and_(TokenHolding.tokenization_id == TokenizationRecord.id, TokenHolding.is_deleted == False)",
        lazy="selectin",
    )
    transfers: Mapped[list[TokenTransfer]] = relationship(
        "TokenTransfer",
        back_populates="tokenization",
        order_by="TokenTransfer.executed_at",
        lazy="selectin",
    )


class TokenHolding(BaseModel):
    """Current cap-table entry for a tokenization.  Mutable; soft-deletable."""

    __tablename__ = "token_holdings"
    __table_args__ = (Index("ix_token_holdings_tokenization_id", "tokenization_id"),)

    tokenization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tokenization_records.id", ondelete="CASCADE"),
        nullable=False,
    )
    holder_name: Mapped[str] = mapped_column(String(255), nullable=False)
    holder_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # GP, LP, Institutional, Developer, Sponsor
    tokens: Mapped[sa.Numeric] = mapped_column(Numeric(19, 4), nullable=False)
    percentage: Mapped[sa.Numeric] = mapped_column(Numeric(5, 2), nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)

    # Relationships
    tokenization: Mapped[TokenizationRecord] = relationship(
        "TokenizationRecord", back_populates="holdings"
    )
    outgoing_transfers: Mapped[list[TokenTransfer]] = relationship(
        "TokenTransfer",
        foreign_keys="[TokenTransfer.from_holding_id]",
        back_populates="from_holding",
    )
    incoming_transfers: Mapped[list[TokenTransfer]] = relationship(
        "TokenTransfer",
        foreign_keys="[TokenTransfer.to_holding_id]",
        back_populates="to_holding",
    )


class TokenTransfer(TimestampedModel):
    """Append-only audit log entry for every mint / transfer / burn.

    No updated_at, no is_deleted — immutable by design.
    """

    __tablename__ = "token_transfers"
    __table_args__ = (
        Index("ix_token_transfers_tokenization_id", "tokenization_id"),
        Index("ix_token_transfers_executed_at", "executed_at"),
    )

    tokenization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tokenization_records.id", ondelete="CASCADE"),
        nullable=False,
    )
    from_holding_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("token_holdings.id", ondelete="SET NULL"),
        nullable=True,
    )
    to_holding_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("token_holdings.id", ondelete="SET NULL"),
        nullable=True,
    )
    amount: Mapped[sa.Numeric] = mapped_column(Numeric(19, 4), nullable=False)
    transfer_type: Mapped[str] = mapped_column(String(20), nullable=False)
    executed_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )
    executed_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    tx_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    tokenization: Mapped[TokenizationRecord] = relationship(
        "TokenizationRecord", back_populates="transfers"
    )
    from_holding: Mapped[TokenHolding | None] = relationship(
        "TokenHolding",
        foreign_keys=[from_holding_id],
        back_populates="outgoing_transfers",
    )
    to_holding: Mapped[TokenHolding | None] = relationship(
        "TokenHolding",
        foreign_keys=[to_holding_id],
        back_populates="incoming_transfers",
    )
