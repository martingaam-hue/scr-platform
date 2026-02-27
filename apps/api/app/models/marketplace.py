"""Marketplace models: Listing, RFQ, Transaction."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Date, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import (
    ListingStatus,
    ListingType,
    ListingVisibility,
    RFQStatus,
    TransactionStatus,
)


class Listing(BaseModel):
    __tablename__ = "listings"
    __table_args__ = (
        Index("ix_listings_org_id", "org_id"),
        Index("ix_listings_project_id", "project_id"),
        Index("ix_listings_status", "status"),
        Index("ix_listings_listing_type", "listing_type"),
        Index("ix_listings_visibility", "visibility"),
        Index("ix_listings_org_id_status", "org_id", "status"),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="SET NULL"),
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    listing_type: Mapped[ListingType] = mapped_column(nullable=False)
    status: Mapped[ListingStatus] = mapped_column(
        nullable=False, default=ListingStatus.DRAFT
    )
    visibility: Mapped[ListingVisibility] = mapped_column(
        nullable=False, default=ListingVisibility.QUALIFIED_ONLY
    )
    asking_price: Mapped[Decimal | None] = mapped_column(Numeric(19, 4))
    minimum_investment: Mapped[Decimal | None] = mapped_column(Numeric(19, 4))
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    details: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    expires_at: Mapped[date | None] = mapped_column(Date)

    # Relationships
    rfqs: Mapped[list["RFQ"]] = relationship(back_populates="listing")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="listing")

    def __repr__(self) -> str:
        return f"<Listing(id={self.id}, title={self.title!r}, status={self.status.value})>"


class RFQ(BaseModel):
    __tablename__ = "rfqs"
    __table_args__ = (
        Index("ix_rfqs_listing_id", "listing_id"),
        Index("ix_rfqs_buyer_org_id", "buyer_org_id"),
        Index("ix_rfqs_status", "status"),
        Index("ix_rfqs_buyer_status", "buyer_org_id", "status"),
    )

    listing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("listings.id", ondelete="CASCADE"),
        nullable=False,
    )
    buyer_org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    proposed_price: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    proposed_terms: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    status: Mapped[RFQStatus] = mapped_column(
        nullable=False, default=RFQStatus.SUBMITTED
    )
    message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    counter_price: Mapped[Decimal | None] = mapped_column(Numeric(19, 4))
    counter_terms: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    submitted_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
    )

    # Relationships
    listing: Mapped["Listing"] = relationship(back_populates="rfqs")

    def __repr__(self) -> str:
        return f"<RFQ(id={self.id}, status={self.status.value})>"


class Transaction(BaseModel):
    __tablename__ = "transactions"
    __table_args__ = (
        Index("ix_transactions_listing_id", "listing_id"),
        Index("ix_transactions_buyer_org_id", "buyer_org_id"),
        Index("ix_transactions_seller_org_id", "seller_org_id"),
        Index("ix_transactions_status", "status"),
    )

    listing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("listings.id", ondelete="SET NULL"),
        nullable=False,
    )
    buyer_org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    seller_org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    rfq_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rfqs.id", ondelete="SET NULL"),
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    status: Mapped[TransactionStatus] = mapped_column(
        nullable=False, default=TransactionStatus.PENDING
    )
    terms: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    settlement_details: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    completed_at: Mapped[datetime | None] = mapped_column()

    # Relationships
    listing: Mapped["Listing"] = relationship(back_populates="transactions")

    def __repr__(self) -> str:
        return f"<Transaction(id={self.id}, amount={self.amount}, status={self.status.value})>"
