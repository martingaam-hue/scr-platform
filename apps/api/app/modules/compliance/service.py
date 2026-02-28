"""Compliance deadline service — CRUD + auto-generation + recurrence."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.compliance import ComplianceDeadline

logger = structlog.get_logger()

# ── Jurisdiction-specific deadline templates ──────────────────────────────────

_TEMPLATES: dict[str, list[dict[str, Any]]] = {
    "EU_solar": [
        {"category": "environmental", "title": "Environmental Impact Assessment Renewal", "recurrence": "annually",
         "priority": "critical", "regulatory_body": "Local Environmental Authority",
         "description": "Annual EIA report submission to maintain operational permit."},
        {"category": "permit", "title": "Grid Connection License Renewal", "recurrence": "annually",
         "priority": "critical", "regulatory_body": "National Grid Operator",
         "description": "Renew grid connection agreement and technical compliance certificate."},
        {"category": "sfdr", "title": "SFDR Quarterly Sustainability Report", "recurrence": "quarterly",
         "priority": "high", "regulatory_body": "National Competent Authority",
         "description": "Article 8/9 sustainability indicators quarterly disclosure."},
        {"category": "reporting", "title": "EU Taxonomy Alignment Report", "recurrence": "annually",
         "priority": "high", "regulatory_body": "European Securities and Markets Authority",
         "description": "Annual Do No Significant Harm (DNSH) and minimum social safeguards assessment."},
        {"category": "insurance", "title": "Annual Insurance Renewal", "recurrence": "annually",
         "priority": "high", "regulatory_body": "Insurance Provider",
         "description": "Renew operational, liability, and property insurance policies."},
        {"category": "tax", "title": "Annual Corporate Tax Filing", "recurrence": "annually",
         "priority": "high", "regulatory_body": "National Tax Authority",
         "description": "Corporate income tax return and renewable energy incentive claims."},
    ],
    "EU_wind": [
        {"category": "environmental", "title": "Noise Impact Assessment", "recurrence": "annually",
         "priority": "critical", "regulatory_body": "Environmental Protection Agency",
         "description": "Annual noise level monitoring and regulatory reporting."},
        {"category": "permit", "title": "Aviation Authority Notification", "recurrence": "annually",
         "priority": "high", "regulatory_body": "Civil Aviation Authority",
         "description": "Annual update of obstacle lighting status and turbine inventory."},
        {"category": "sfdr", "title": "SFDR Quarterly Report", "recurrence": "quarterly",
         "priority": "high", "regulatory_body": "National Competent Authority",
         "description": "SFDR Article 8/9 quarterly sustainability disclosure."},
        {"category": "insurance", "title": "Annual Insurance Renewal", "recurrence": "annually",
         "priority": "high", "regulatory_body": "Insurance Provider",
         "description": "Renew all-risk, liability, and business interruption insurance."},
    ],
    "EU_general": [
        {"category": "reporting", "title": "AIFMD Annual Report", "recurrence": "annually",
         "priority": "critical", "regulatory_body": "National Competent Authority",
         "description": "Alternative Investment Fund Manager Directive annual regulatory report."},
        {"category": "sfdr", "title": "SFDR Quarterly Disclosure", "recurrence": "quarterly",
         "priority": "high", "regulatory_body": "National Competent Authority",
         "description": "Principal adverse impacts and sustainability risk quarterly report."},
        {"category": "insurance", "title": "Annual Insurance Renewal", "recurrence": "annually",
         "priority": "high", "regulatory_body": "Insurance Provider",
         "description": "Annual professional indemnity and D&O insurance renewal."},
        {"category": "tax", "title": "Annual Tax Filing", "recurrence": "annually",
         "priority": "high", "regulatory_body": "Tax Authority",
         "description": "Annual corporate and partnership tax return filing."},
    ],
}


def _next_occurrence(from_date: date, recurrence: str | None) -> date | None:
    """Calculate next due date from a recurrence pattern."""
    if not recurrence or recurrence == "one_time":
        return None
    today = date.today()
    # Find next future date from today
    d = from_date
    while d <= today:
        if recurrence == "monthly":
            month = d.month + 1 if d.month < 12 else 1
            year = d.year if d.month < 12 else d.year + 1
            d = d.replace(year=year, month=month)
        elif recurrence == "quarterly":
            months = d.month + 3
            year = d.year + (months - 1) // 12
            month = ((months - 1) % 12) + 1
            d = d.replace(year=year, month=month)
        elif recurrence == "annually":
            d = d.replace(year=d.year + 1)
        else:
            return None
    return d


async def list_deadlines(
    db: AsyncSession,
    org_id: uuid.UUID,
    status: str | None = None,
    category: str | None = None,
    project_id: uuid.UUID | None = None,
) -> list[ComplianceDeadline]:
    stmt = select(ComplianceDeadline).where(
        ComplianceDeadline.org_id == org_id,
        ComplianceDeadline.is_deleted == False,
    )
    if status:
        stmt = stmt.where(ComplianceDeadline.status == status)
    if category:
        stmt = stmt.where(ComplianceDeadline.category == category)
    if project_id:
        stmt = stmt.where(ComplianceDeadline.project_id == project_id)
    stmt = stmt.order_by(ComplianceDeadline.due_date)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_deadline(db: AsyncSession, deadline_id: uuid.UUID, org_id: uuid.UUID) -> ComplianceDeadline | None:
    result = await db.execute(
        select(ComplianceDeadline).where(
            ComplianceDeadline.id == deadline_id,
            ComplianceDeadline.org_id == org_id,
            ComplianceDeadline.is_deleted == False,
        )
    )
    return result.scalar_one_or_none()


async def create_deadline(db: AsyncSession, org_id: uuid.UUID, body: Any) -> ComplianceDeadline:
    deadline = ComplianceDeadline(
        org_id=org_id,
        **{k: v for k, v in body.model_dump().items() if v is not None},
    )
    db.add(deadline)
    await db.commit()
    await db.refresh(deadline)
    return deadline


async def update_deadline(
    db: AsyncSession, deadline: ComplianceDeadline, body: Any
) -> ComplianceDeadline:
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(deadline, field, value)
    await db.commit()
    await db.refresh(deadline)
    return deadline


async def complete_deadline(db: AsyncSession, deadline: ComplianceDeadline) -> ComplianceDeadline:
    """Mark deadline complete; if recurring, create next occurrence."""
    deadline.status = "completed"
    deadline.completed_at = datetime.utcnow()
    await db.flush()

    # Spawn next occurrence for recurring deadlines
    if deadline.recurrence and deadline.recurrence != "one_time":
        next_due = _next_occurrence(deadline.due_date, deadline.recurrence)
        if next_due:
            next_deadline = ComplianceDeadline(
                org_id=deadline.org_id,
                project_id=deadline.project_id,
                portfolio_id=deadline.portfolio_id,
                category=deadline.category,
                title=deadline.title,
                description=deadline.description,
                jurisdiction=deadline.jurisdiction,
                regulatory_body=deadline.regulatory_body,
                due_date=next_due,
                recurrence=deadline.recurrence,
                priority=deadline.priority,
                assigned_to=deadline.assigned_to,
                status="upcoming",
            )
            db.add(next_deadline)

    await db.commit()
    await db.refresh(deadline)
    return deadline


async def delete_deadline(db: AsyncSession, deadline: ComplianceDeadline) -> None:
    deadline.is_deleted = True
    await db.commit()


async def auto_generate_deadlines(
    db: AsyncSession,
    org_id: uuid.UUID,
    project_id: uuid.UUID,
    jurisdiction: str,
    project_type: str,
) -> list[ComplianceDeadline]:
    """Generate standard jurisdiction/type deadlines for a project."""
    key = f"{jurisdiction}_{project_type}"
    templates = _TEMPLATES.get(key) or _TEMPLATES.get(f"{jurisdiction}_general") or []
    today = date.today()
    created: list[ComplianceDeadline] = []
    for tmpl in templates:
        # Calculate first due date: ~1 year from now for annual, 3 months for quarterly
        recurrence = tmpl.get("recurrence", "annually")
        if recurrence == "quarterly":
            due = today + timedelta(days=90)
        elif recurrence == "monthly":
            due = today + timedelta(days=30)
        else:
            due = today + timedelta(days=365)
        deadline = ComplianceDeadline(
            org_id=org_id,
            project_id=project_id,
            due_date=due,
            status="upcoming",
            **{k: v for k, v in tmpl.items()},
        )
        db.add(deadline)
        created.append(deadline)
    await db.commit()
    for d in created:
        await db.refresh(d)
    return created


async def flag_overdue(db: AsyncSession) -> int:
    """Mark all past-due 'upcoming'/'in_progress' deadlines as overdue."""
    today = date.today()
    result = await db.execute(
        update(ComplianceDeadline)
        .where(
            ComplianceDeadline.due_date < today,
            ComplianceDeadline.status.in_(["upcoming", "in_progress"]),
            ComplianceDeadline.is_deleted == False,
        )
        .values(status="overdue")
        .returning(ComplianceDeadline.id)
    )
    count = len(result.fetchall())
    await db.commit()
    logger.info("compliance.overdue_flagged", count=count)
    return count


async def get_reminder_candidates(db: AsyncSession, days: int) -> list[ComplianceDeadline]:
    """Get deadlines due in exactly `days` days that haven't had their reminder sent."""
    target = date.today() + timedelta(days=days)
    flag_col = {
        30: ComplianceDeadline.reminder_30d_sent,
        14: ComplianceDeadline.reminder_14d_sent,
        7: ComplianceDeadline.reminder_7d_sent,
        1: ComplianceDeadline.reminder_1d_sent,
    }.get(days)
    if flag_col is None:
        return []
    result = await db.execute(
        select(ComplianceDeadline).where(
            ComplianceDeadline.due_date == target,
            ComplianceDeadline.status.in_(["upcoming", "in_progress"]),
            flag_col == False,
            ComplianceDeadline.is_deleted == False,
        )
    )
    return list(result.scalars().all())


async def mark_reminder_sent(db: AsyncSession, deadline: ComplianceDeadline, days: int) -> None:
    col_map = {30: "reminder_30d_sent", 14: "reminder_14d_sent", 7: "reminder_7d_sent", 1: "reminder_1d_sent"}
    col = col_map.get(days)
    if col:
        setattr(deadline, col, True)
    await db.commit()
