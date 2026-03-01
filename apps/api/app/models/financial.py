"""Financial models: Valuation, TaxCredit, CarbonCredit, BusinessPlan."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Date, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import (
    BusinessPlanStatus,
    CarbonVerificationStatus,
    TaxCreditQualification,
    ValuationMethod,
    ValuationStatus,
)


class Valuation(BaseModel):
    __tablename__ = "valuations"
    __table_args__ = (
        Index("ix_valuations_project_id", "project_id"),
        Index("ix_valuations_org_id", "org_id"),
        Index("ix_valuations_status", "status"),
        Index("ix_valuations_project_id_version", "project_id", "version"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    method: Mapped[ValuationMethod] = mapped_column(nullable=False)
    enterprise_value: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    equity_value: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    assumptions: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    model_inputs: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    status: Mapped[ValuationStatus] = mapped_column(
        nullable=False, default=ValuationStatus.DRAFT
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    valued_at: Mapped[date] = mapped_column(Date, nullable=False)
    prepared_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
    )
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )

    def __repr__(self) -> str:
        return f"<Valuation(id={self.id}, method={self.method.value}, ev={self.enterprise_value})>"


class TaxCredit(BaseModel):
    __tablename__ = "tax_credits"
    __table_args__ = (
        Index("ix_tax_credits_project_id", "project_id"),
        Index("ix_tax_credits_org_id", "org_id"),
        Index("ix_tax_credits_qualification", "qualification"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    credit_type: Mapped[str] = mapped_column(String(100), nullable=False)
    estimated_value: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    claimed_value: Mapped[Decimal | None] = mapped_column(Numeric(19, 4))
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    qualification: Mapped[TaxCreditQualification] = mapped_column(
        nullable=False, default=TaxCreditQualification.POTENTIAL
    )
    qualification_details: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    effective_date: Mapped[date | None] = mapped_column(Date)
    expiry_date: Mapped[date | None] = mapped_column(Date)

    def __repr__(self) -> str:
        return f"<TaxCredit(id={self.id}, type={self.credit_type!r}, qualification={self.qualification.value})>"


class CarbonCredit(BaseModel):
    __tablename__ = "carbon_credits"
    __table_args__ = (
        Index("ix_carbon_credits_project_id", "project_id"),
        Index("ix_carbon_credits_org_id", "org_id"),
        Index("ix_carbon_credits_verification_status", "verification_status"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    registry: Mapped[str] = mapped_column(String(100), nullable=False)
    methodology: Mapped[str] = mapped_column(String(255), nullable=False)
    vintage_year: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_tons: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    price_per_ton: Mapped[Decimal | None] = mapped_column(Numeric(19, 4))
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    serial_number: Mapped[str | None] = mapped_column(String(255))
    verification_status: Mapped[CarbonVerificationStatus] = mapped_column(
        nullable=False, default=CarbonVerificationStatus.ESTIMATED
    )
    verification_body: Mapped[str | None] = mapped_column(String(255))
    issuance_date: Mapped[date | None] = mapped_column(Date)
    retirement_date: Mapped[date | None] = mapped_column(Date)

    def __repr__(self) -> str:
        return f"<CarbonCredit(id={self.id}, registry={self.registry!r}, tons={self.quantity_tons})>"


class BusinessPlan(BaseModel):
    __tablename__ = "business_plans"
    __table_args__ = (
        Index("ix_business_plans_project_id", "project_id"),
        Index("ix_business_plans_org_id", "org_id"),
        Index("ix_business_plans_status", "status"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    executive_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    financial_projections: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    market_analysis: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    risk_analysis: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    use_of_funds: Mapped[str | None] = mapped_column(Text, nullable=True)
    team_section: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_section: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[BusinessPlanStatus] = mapped_column(
        nullable=False, default=BusinessPlanStatus.DRAFT
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    def __repr__(self) -> str:
        return f"<BusinessPlan(id={self.id}, title={self.title!r}, status={self.status.value})>"
