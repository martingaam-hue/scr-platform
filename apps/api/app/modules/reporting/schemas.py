"""Reporting Pydantic schemas: request/response models for templates, reports, schedules."""

import enum
import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import ReportCategory, ReportFrequency, ReportStatus


# ── Enums (request-only) ────────────────────────────────────────────────────


class OutputFormat(str, enum.Enum):
    PDF = "pdf"
    XLSX = "xlsx"
    PPTX = "pptx"


# ── Request schemas ─────────────────────────────────────────────────────────


class GenerateReportRequest(BaseModel):
    template_id: uuid.UUID
    parameters: dict = Field(default_factory=dict)
    output_format: OutputFormat = OutputFormat.PDF
    title: str | None = None


class CreateScheduleRequest(BaseModel):
    template_id: uuid.UUID
    name: str = Field(min_length=1, max_length=500)
    frequency: ReportFrequency
    parameters: dict = Field(default_factory=dict)
    recipients: list[str] = Field(default_factory=list)
    output_format: OutputFormat = OutputFormat.PDF


class UpdateScheduleRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=500)
    frequency: ReportFrequency | None = None
    parameters: dict | None = None
    recipients: list[str] | None = None
    output_format: OutputFormat | None = None
    is_active: bool | None = None


# ── Response schemas ────────────────────────────────────────────────────────


class ReportTemplateResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID | None
    name: str
    category: ReportCategory
    description: str
    template_config: dict
    sections: dict | None
    is_system: bool
    version: int
    created_at: datetime
    updated_at: datetime


class ReportTemplateListResponse(BaseModel):
    items: list[ReportTemplateResponse]
    total: int


class GeneratedReportResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    template_id: uuid.UUID | None
    title: str
    status: ReportStatus
    parameters: dict | None
    result_data: dict | None
    s3_key: str | None
    error_message: str | None
    generated_by: uuid.UUID
    completed_at: datetime | None
    download_url: str | None = None
    template_name: str | None = None
    created_at: datetime
    updated_at: datetime


class GeneratedReportListResponse(BaseModel):
    items: list[GeneratedReportResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class GenerateReportAcceptedResponse(BaseModel):
    report_id: uuid.UUID
    status: ReportStatus
    message: str


class ScheduledReportResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    template_id: uuid.UUID
    name: str
    frequency: ReportFrequency
    parameters: dict | None
    recipients: dict | None
    is_active: bool
    last_run_at: datetime | None
    next_run_at: datetime | None
    template_name: str | None = None
    created_at: datetime
    updated_at: datetime


class ScheduledReportListResponse(BaseModel):
    items: list[ScheduledReportResponse]
    total: int
