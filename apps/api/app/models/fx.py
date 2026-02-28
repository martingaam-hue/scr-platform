"""FX Rates model — daily currency exchange rates fetched from ECB."""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Date, Float, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TimestampedModel


class FXRate(TimestampedModel):
    """Daily FX rate from ECB. Base currency is always EUR."""

    __tablename__ = "fx_rates"

    base_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    quote_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    rate: Mapped[float] = mapped_column(Float, nullable=False)
    rate_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    source: Mapped[str] = mapped_column(
        String(20), default="ecb", server_default="ecb", nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "base_currency", "quote_currency", "rate_date", name="uq_fx_pair_date"
        ),
        Index("ix_fx_pair_date_lookup", "base_currency", "quote_currency", "rate_date"),
    )

    def __repr__(self) -> str:
        return (
            f"<FXRate({self.base_currency}/{self.quote_currency}={self.rate} "
            f"@ {self.rate_date})>"
        )
