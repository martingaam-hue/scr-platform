"""Legal Document Manager API schemas."""

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


# ── Templates ─────────────────────────────────────────────────────────────────


class QuestionnaireField(BaseModel):
    id: str
    type: str  # text|textarea|select|number|date|boolean
    label: str
    required: bool = False
    options: list[str] | None = None
    placeholder: str | None = None


class QuestionnaireSection(BaseModel):
    id: str
    title: str
    fields: list[QuestionnaireField]


class Questionnaire(BaseModel):
    sections: list[QuestionnaireSection]


class TemplateListItem(BaseModel):
    id: str                # slug-based system template id
    name: str
    doc_type: str
    description: str
    estimated_pages: int


class TemplateDetail(BaseModel):
    id: str
    name: str
    doc_type: str
    description: str
    estimated_pages: int
    questionnaire: Questionnaire


# ── Documents ─────────────────────────────────────────────────────────────────


class LegalDocumentCreate(BaseModel):
    template_id: str  # system template id slug
    title: str
    project_id: uuid.UUID | None = None


class LegalDocumentUpdate(BaseModel):
    questionnaire_answers: dict[str, Any]


class LegalDocumentResponse(BaseModel):
    id: uuid.UUID
    title: str
    doc_type: str
    status: str
    template_id: str | None
    project_id: uuid.UUID | None
    content: str
    s3_key: str | None
    version: int
    signed_date: date | None
    expiry_date: date | None
    questionnaire_answers: dict[str, Any] | None
    generation_status: str | None  # pending|generating|completed|failed
    download_url: str | None
    created_at: datetime
    updated_at: datetime


class LegalDocumentListResponse(BaseModel):
    items: list[LegalDocumentResponse]
    total: int


class GenerateDocumentRequest(BaseModel):
    format: str = Field(default="docx", pattern="^(docx|html)$")


class GenerateDocumentResponse(BaseModel):
    document_id: uuid.UUID
    status: str
    message: str


class SendDocumentRequest(BaseModel):
    recipient_emails: list[str]
    message: str | None = None


# ── Review ────────────────────────────────────────────────────────────────────


class ClauseAnalysis(BaseModel):
    clause_type: str
    text_excerpt: str
    risk_level: str  # low|medium|high|critical
    issue: str | None
    recommendation: str | None


class ReviewRequest(BaseModel):
    document_id: uuid.UUID | None = None
    document_text: str | None = None
    mode: str = Field(default="risk_focused")
    jurisdiction: str = Field(default="England & Wales")


class ReviewResponse(BaseModel):
    review_id: uuid.UUID
    status: str
    message: str


class ReviewResultResponse(BaseModel):
    review_id: uuid.UUID
    document_id: uuid.UUID | None
    mode: str
    jurisdiction: str
    status: str
    overall_risk_score: int | None
    summary: str | None
    clause_analyses: list[ClauseAnalysis]
    missing_clauses: list[str]
    jurisdiction_issues: list[str]
    recommendations: list[str]
    model_used: str | None
    created_at: datetime


class CompareRequest(BaseModel):
    document_id_a: uuid.UUID
    document_id_b: uuid.UUID
