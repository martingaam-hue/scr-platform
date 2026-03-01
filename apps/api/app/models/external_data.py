"""ExternalDataPoint model — public market data snapshots (FRED, World Bank, ECB)."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Index, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import ModelMixin


class ExternalDataPoint(Base, ModelMixin):
    """Snapshot of a public market / economic data series for one date."""

    __tablename__ = "external_data_points"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    # e.g. "fred", "worldbank", "ecb"
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    # e.g. "DGS10", "FEDFUNDS", "NY.GDP.MKTP.KD.ZG"
    series_id: Mapped[str] = mapped_column(String(100), nullable=False)
    # Human-readable name
    series_name: Mapped[str] = mapped_column(String(255), nullable=False)
    data_date: Mapped[date] = mapped_column(Date(), nullable=False)
    value: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    # "percent", "index", "usd", "billions_usd", etc.
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "source", "series_id", "data_date",
            name="uq_external_data_point",
        ),
        Index("ix_external_data_source_series", "source", "series_id"),
        Index("ix_external_data_date", "data_date"),
    )

    def __repr__(self) -> str:
        return f"<ExternalDataPoint({self.source}/{self.series_id}={self.value} @ {self.data_date})>"
