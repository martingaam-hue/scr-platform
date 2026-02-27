"""Project models: Project, ProjectMilestone, ProjectBudgetItem, SignalScore."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Date, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel, TimestampedModel
from app.models.enums import (
    BudgetItemStatus,
    MilestoneStatus,
    ProjectStage,
    ProjectStatus,
    ProjectType,
)


class Project(BaseModel):
    __tablename__ = "projects"
    __table_args__ = (
        Index("ix_projects_org_id", "org_id"),
        Index("ix_projects_org_id_status", "org_id", "status"),
        Index("ix_projects_status", "status"),
        Index("ix_projects_project_type", "project_type"),
        Index("ix_projects_slug", "slug"),
        Index("ix_projects_geography_country", "geography_country"),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    slug: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    project_type: Mapped[ProjectType] = mapped_column(nullable=False)
    status: Mapped[ProjectStatus] = mapped_column(
        nullable=False, default=ProjectStatus.DRAFT
    )
    stage: Mapped[ProjectStage] = mapped_column(
        nullable=False, default=ProjectStage.CONCEPT
    )
    geography_country: Mapped[str] = mapped_column(String(100), nullable=False)
    geography_region: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    geography_coordinates: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    technology_details: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    capacity_mw: Mapped[Decimal | None] = mapped_column(Numeric(19, 4))
    total_investment_required: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    target_close_date: Mapped[date | None] = mapped_column(Date)
    cover_image_url: Mapped[str | None] = mapped_column(String(512))
    is_published: Mapped[bool] = mapped_column(
        default=False, server_default="false", nullable=False
    )
    published_at: Mapped[datetime | None] = mapped_column()

    # Relationships
    organization: Mapped["Organization"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="projects", foreign_keys=[org_id]
    )
    milestones: Mapped[list["ProjectMilestone"]] = relationship(back_populates="project")
    budget_items: Mapped[list["ProjectBudgetItem"]] = relationship(back_populates="project")
    signal_scores: Mapped[list["SignalScore"]] = relationship(back_populates="project")

    def __repr__(self) -> str:
        return f"<Project(id={self.id}, name={self.name!r}, status={self.status.value})>"


class ProjectMilestone(BaseModel):
    __tablename__ = "project_milestones"
    __table_args__ = (
        Index("ix_project_milestones_project_id", "project_id"),
        Index("ix_project_milestones_status", "status"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    target_date: Mapped[date] = mapped_column(Date, nullable=False)
    completed_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[MilestoneStatus] = mapped_column(
        nullable=False, default=MilestoneStatus.NOT_STARTED
    )
    completion_pct: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    project: Mapped["Project"] = relationship(back_populates="milestones")


class ProjectBudgetItem(BaseModel):
    __tablename__ = "project_budget_items"
    __table_args__ = (
        Index("ix_project_budget_items_project_id", "project_id"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    category: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    estimated_amount: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    actual_amount: Mapped[Decimal | None] = mapped_column(Numeric(19, 4))
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    status: Mapped[BudgetItemStatus] = mapped_column(
        nullable=False, default=BudgetItemStatus.PLANNED
    )

    # Relationships
    project: Mapped["Project"] = relationship(back_populates="budget_items")


class SignalScore(TimestampedModel):
    __tablename__ = "signal_scores"
    __table_args__ = (
        Index("ix_signal_scores_project_id", "project_id"),
        Index("ix_signal_scores_project_id_version", "project_id", "version"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    overall_score: Mapped[int] = mapped_column(Integer, nullable=False)
    technical_score: Mapped[int] = mapped_column(Integer, nullable=False)
    financial_score: Mapped[int] = mapped_column(Integer, nullable=False)
    esg_score: Mapped[int] = mapped_column(Integer, nullable=False)
    regulatory_score: Mapped[int] = mapped_column(Integer, nullable=False)
    team_score: Mapped[int] = mapped_column(Integer, nullable=False)
    scoring_details: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    gaps: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    strengths: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    model_used: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    calculated_at: Mapped[datetime] = mapped_column(nullable=False)

    # Relationships
    project: Mapped["Project"] = relationship(back_populates="signal_scores")
