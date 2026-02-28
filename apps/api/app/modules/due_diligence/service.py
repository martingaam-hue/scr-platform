"""Due Diligence Checklist service — async business logic."""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

import structlog
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dataroom import Document
from app.models.due_diligence import (
    DDChecklistItem,
    DDChecklistTemplate,
    DDItemStatus,
    DDProjectChecklist,
)
from app.models.projects import Project
from app.modules.due_diligence.schemas import (
    DDChecklistItemFull,
    DDChecklistResponse,
    DDTemplateResponse,
)

logger = structlog.get_logger()

# Stage → deal_stage mapping for template selection
STAGE_TO_DD_STAGE: dict[str, str] = {
    "concept": "screening",
    "pre_development": "screening",
    "development": "preliminary_dd",
    "construction_ready": "full_dd",
    "under_construction": "full_dd",
    "operational": "full_dd",
}


# ── Template queries ──────────────────────────────────────────────────────────


async def list_templates(
    db: AsyncSession,
    asset_type: str | None = None,
) -> list[dict[str, Any]]:
    """List active DD checklist templates, optionally filtered by asset_type."""
    stmt = select(DDChecklistTemplate).where(
        DDChecklistTemplate.is_active.is_(True),
        DDChecklistTemplate.is_deleted.is_(False),
    )
    if asset_type:
        stmt = stmt.where(DDChecklistTemplate.asset_type == asset_type)
    stmt = stmt.order_by(DDChecklistTemplate.asset_type, DDChecklistTemplate.deal_stage)
    result = await db.execute(stmt)
    templates = result.scalars().all()

    out = []
    for tpl in templates:
        # Count items
        count_stmt = select(DDChecklistItem).where(
            DDChecklistItem.template_id == tpl.id,
            DDChecklistItem.is_deleted.is_(False),
        )
        items_result = await db.execute(count_stmt)
        item_count = len(items_result.scalars().all())

        tpl_dict = tpl.to_dict()
        tpl_dict["item_count"] = item_count
        out.append(tpl_dict)

    return out


async def get_template(
    db: AsyncSession,
    template_id: uuid.UUID,
) -> dict[str, Any] | None:
    """Get a single template with its items."""
    tpl = await db.get(DDChecklistTemplate, template_id)
    if not tpl or tpl.is_deleted:
        return None

    items_stmt = (
        select(DDChecklistItem)
        .where(
            DDChecklistItem.template_id == template_id,
            DDChecklistItem.is_deleted.is_(False),
        )
        .order_by(DDChecklistItem.sort_order)
    )
    items_result = await db.execute(items_stmt)
    items = items_result.scalars().all()

    result = tpl.to_dict()
    result["item_count"] = len(items)
    result["items"] = [item.to_dict() for item in items]
    return result


# ── Checklist generation ──────────────────────────────────────────────────────


async def _find_best_template(
    db: AsyncSession,
    asset_type: str,
    dd_stage: str,
    country: str | None,
) -> DDChecklistTemplate | None:
    """Find best matching template: jurisdiction-specific > global."""
    # Determine jurisdiction group from country (simplified EU mapping)
    eu_countries = {
        "DE", "FR", "ES", "IT", "PL", "NL", "BE", "SE", "PT", "FI",
        "DK", "AT", "IE", "GR", "CZ", "RO", "HU", "SK", "BG", "HR",
        "LT", "LV", "EE", "SI", "LU", "MT", "CY",
        # Country names
        "Germany", "France", "Spain", "Italy", "Poland", "Netherlands",
        "Belgium", "Sweden", "Portugal", "Finland", "Denmark", "Austria",
        "Ireland", "Greece", "Czech Republic", "Romania", "Hungary",
    }
    jurisdiction_group: str | None = None
    if country and country in eu_countries:
        jurisdiction_group = "EU"

    # Try jurisdiction-specific first
    if jurisdiction_group:
        stmt = select(DDChecklistTemplate).where(
            DDChecklistTemplate.asset_type == asset_type,
            DDChecklistTemplate.deal_stage == dd_stage,
            DDChecklistTemplate.jurisdiction_group == jurisdiction_group,
            DDChecklistTemplate.is_active.is_(True),
            DDChecklistTemplate.is_deleted.is_(False),
        ).limit(1)
        result = await db.execute(stmt)
        tpl = result.scalar_one_or_none()
        if tpl:
            return tpl

    # Fall back to global (jurisdiction_group IS NULL)
    stmt = select(DDChecklistTemplate).where(
        DDChecklistTemplate.asset_type == asset_type,
        DDChecklistTemplate.deal_stage == dd_stage,
        DDChecklistTemplate.jurisdiction_group.is_(None),
        DDChecklistTemplate.is_active.is_(True),
        DDChecklistTemplate.is_deleted.is_(False),
    ).limit(1)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def generate_checklist(
    db: AsyncSession,
    project_id: uuid.UUID,
    org_id: uuid.UUID,
    investor_id: uuid.UUID | None = None,
) -> DDProjectChecklist:
    """Instantiate a DD checklist for a project from the best matching template."""
    # Load project
    project = await db.get(Project, project_id)
    if not project:
        raise LookupError(f"Project {project_id} not found")

    asset_type = project.project_type.value if project.project_type else "other"
    stage_value = project.stage.value if project.stage else "concept"
    dd_stage = STAGE_TO_DD_STAGE.get(stage_value, "screening")
    country = project.geography_country

    # Find best template
    template = await _find_best_template(db, asset_type, dd_stage, country)
    if not template:
        # Try broader fallback: just asset_type with any stage
        stmt = select(DDChecklistTemplate).where(
            DDChecklistTemplate.asset_type == asset_type,
            DDChecklistTemplate.is_active.is_(True),
            DDChecklistTemplate.is_deleted.is_(False),
        ).limit(1)
        result = await db.execute(stmt)
        template = result.scalar_one_or_none()

    if not template:
        raise LookupError(
            f"No DD template found for asset_type={asset_type}, stage={dd_stage}"
        )

    # Load template items
    items_stmt = select(DDChecklistItem).where(
        DDChecklistItem.template_id == template.id,
        DDChecklistItem.is_deleted.is_(False),
    ).order_by(DDChecklistItem.sort_order)
    items_result = await db.execute(items_stmt)
    items = items_result.scalars().all()

    # Create checklist
    checklist = DDProjectChecklist(
        project_id=project_id,
        org_id=org_id,
        template_id=template.id,
        investor_id=investor_id,
        status="in_progress",
        completion_percentage=0.0,
        total_items=len(items),
        completed_items=0,
        custom_items=[],
    )
    db.add(checklist)
    await db.flush()

    # Create item statuses
    for item in items:
        item_status = DDItemStatus(
            checklist_id=checklist.id,
            item_id=item.id,
            status="pending",
        )
        db.add(item_status)

    await db.flush()

    # Auto-match documents
    await auto_match_documents(db, checklist.id, project_id)

    await db.commit()
    await db.refresh(checklist)

    logger.info(
        "dd_checklist.generated",
        checklist_id=str(checklist.id),
        project_id=str(project_id),
        template_id=str(template.id),
        total_items=len(items),
    )
    return checklist


# ── Checklist retrieval ───────────────────────────────────────────────────────


async def get_checklist(
    db: AsyncSession,
    checklist_id: uuid.UUID,
    org_id: uuid.UUID,
) -> DDChecklistResponse | None:
    """Fetch checklist with all item statuses joined."""
    checklist = await db.get(DDProjectChecklist, checklist_id)
    if not checklist or checklist.is_deleted or checklist.org_id != org_id:
        return None

    # Load all item statuses
    statuses_stmt = select(DDItemStatus).where(
        DDItemStatus.checklist_id == checklist_id,
        DDItemStatus.is_deleted.is_(False),
    )
    statuses_result = await db.execute(statuses_stmt)
    statuses = statuses_result.scalars().all()
    status_map: dict[uuid.UUID, DDItemStatus] = {s.item_id: s for s in statuses}

    # Load template items
    items_stmt = (
        select(DDChecklistItem)
        .where(
            DDChecklistItem.template_id == checklist.template_id,
            DDChecklistItem.is_deleted.is_(False),
        )
        .order_by(DDChecklistItem.sort_order)
    )
    items_result = await db.execute(items_stmt)
    items = items_result.scalars().all()

    # Build items_by_category
    items_by_category: dict[str, list[DDChecklistItemFull]] = defaultdict(list)
    for item in items:
        item_status = status_map.get(item.id)
        full_item = DDChecklistItemFull(
            item_id=item.id,
            template_id=item.template_id,
            category=item.category,
            name=item.name,
            description=item.description,
            requirement_type=item.requirement_type,
            required_document_types=item.required_document_types,
            verification_criteria=item.verification_criteria,
            priority=item.priority,
            sort_order=item.sort_order,
            estimated_time_hours=item.estimated_time_hours,
            regulatory_reference=item.regulatory_reference,
            status_id=item_status.id if item_status else None,
            status=item_status.status if item_status else "pending",
            satisfied_by_document_id=(
                item_status.satisfied_by_document_id if item_status else None
            ),
            ai_review_result=item_status.ai_review_result if item_status else None,
            reviewer_notes=item_status.reviewer_notes if item_status else None,
            reviewed_at=item_status.reviewed_at if item_status else None,
        )
        items_by_category[item.category].append(full_item)

    return DDChecklistResponse(
        id=checklist.id,
        project_id=checklist.project_id,
        org_id=checklist.org_id,
        template_id=checklist.template_id,
        investor_id=checklist.investor_id,
        status=checklist.status,
        completion_percentage=checklist.completion_percentage,
        total_items=checklist.total_items,
        completed_items=checklist.completed_items,
        custom_items=checklist.custom_items or [],
        items_by_category=dict(items_by_category),
        created_at=checklist.created_at,
        updated_at=checklist.updated_at,
    )


async def list_checklists(
    db: AsyncSession,
    org_id: uuid.UUID,
    project_id: uuid.UUID | None = None,
) -> list[dict[str, Any]]:
    """List checklists for an org, optionally filtered by project."""
    stmt = select(DDProjectChecklist).where(
        DDProjectChecklist.org_id == org_id,
        DDProjectChecklist.is_deleted.is_(False),
    )
    if project_id:
        stmt = stmt.where(DDProjectChecklist.project_id == project_id)
    stmt = stmt.order_by(DDProjectChecklist.created_at.desc())
    result = await db.execute(stmt)
    checklists = result.scalars().all()
    return [c.to_dict() for c in checklists]


# ── Item status updates ───────────────────────────────────────────────────────


async def update_item_status(
    db: AsyncSession,
    checklist_id: uuid.UUID,
    item_id: uuid.UUID,
    org_id: uuid.UUID,
    status: str,
    notes: str | None = None,
    document_id: uuid.UUID | None = None,
) -> DDItemStatus | None:
    """Update the status of a checklist item."""
    # Verify checklist belongs to org
    checklist = await db.get(DDProjectChecklist, checklist_id)
    if not checklist or checklist.is_deleted or checklist.org_id != org_id:
        return None

    # Find item status
    stmt = select(DDItemStatus).where(
        DDItemStatus.checklist_id == checklist_id,
        DDItemStatus.item_id == item_id,
        DDItemStatus.is_deleted.is_(False),
    )
    result = await db.execute(stmt)
    item_status = result.scalar_one_or_none()

    if not item_status:
        return None

    item_status.status = status
    if notes is not None:
        item_status.reviewer_notes = notes
    if document_id is not None:
        item_status.satisfied_by_document_id = document_id
    if status in ("satisfied", "partially_met", "not_met", "waived"):
        item_status.reviewed_at = datetime.now(timezone.utc)

    await db.flush()
    await _update_completion_percentage(db, checklist_id)
    await db.commit()
    await db.refresh(item_status)
    return item_status


async def add_custom_item(
    db: AsyncSession,
    checklist_id: uuid.UUID,
    org_id: uuid.UUID,
    name: str,
    category: str,
    description: str | None = None,
    priority: str = "recommended",
) -> DDProjectChecklist | None:
    """Add a custom item to the checklist's custom_items JSONB array."""
    checklist = await db.get(DDProjectChecklist, checklist_id)
    if not checklist or checklist.is_deleted or checklist.org_id != org_id:
        return None

    custom_item = {
        "id": str(uuid.uuid4()),
        "name": name,
        "category": category,
        "description": description,
        "priority": priority,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    current_items = list(checklist.custom_items or [])
    current_items.append(custom_item)
    checklist.custom_items = current_items
    checklist.total_items = checklist.total_items + 1

    await db.commit()
    await db.refresh(checklist)
    return checklist


# ── AI review ─────────────────────────────────────────────────────────────────


async def trigger_ai_review(
    db: AsyncSession,
    checklist_id: uuid.UUID,
    item_id: uuid.UUID,
    document_id: uuid.UUID,
    org_id: uuid.UUID,
) -> dict[str, Any] | None:
    """Enqueue Celery task for AI review of a document against a DD item."""
    # Verify checklist belongs to org
    checklist = await db.get(DDProjectChecklist, checklist_id)
    if not checklist or checklist.is_deleted or checklist.org_id != org_id:
        return None

    # Find item status record
    stmt = select(DDItemStatus).where(
        DDItemStatus.checklist_id == checklist_id,
        DDItemStatus.item_id == item_id,
        DDItemStatus.is_deleted.is_(False),
    )
    result = await db.execute(stmt)
    item_status = result.scalar_one_or_none()
    if not item_status:
        return None

    # Get item criteria
    item = await db.get(DDChecklistItem, item_id)
    criteria = item.verification_criteria or item.description or item.name if item else ""

    # Update status to in_review
    item_status.status = "in_review"
    item_status.satisfied_by_document_id = document_id
    await db.commit()

    # Enqueue task (lazy import to avoid circular)
    from app.modules.due_diligence.tasks import review_dd_item_task

    review_dd_item_task.delay(
        str(item_status.id),
        str(document_id),
        criteria,
    )

    return {"status": "queued", "item_status_id": str(item_status.id)}


# ── Document auto-matching ────────────────────────────────────────────────────


# Map document classification → DD required_document_types values
CLASSIFICATION_MAP: dict[str, str] = {
    "financial_statement": "financial_statement",
    "legal_agreement": "legal_agreement",
    "technical_study": "technical_study",
    "environmental_report": "environmental_report",
    "permit": "permit",
    "insurance": "insurance",
    "valuation": "valuation",
    "business_plan": "business_plan",
    "presentation": "presentation",
    "correspondence": "correspondence",
    "other": "other",
}


async def auto_match_documents(
    db: AsyncSession,
    checklist_id: uuid.UUID,
    project_id: uuid.UUID,
) -> int:
    """Auto-match project documents to pending checklist items by classification.

    Returns the number of items matched.
    """
    # Load project documents
    docs_stmt = select(Document).where(
        Document.project_id == project_id,
        Document.is_deleted.is_(False),
        Document.classification.isnot(None),
    )
    docs_result = await db.execute(docs_stmt)
    documents = docs_result.scalars().all()

    if not documents:
        return 0

    # Build classification → doc map (latest doc per classification)
    class_to_doc: dict[str, Document] = {}
    for doc in documents:
        cls_value = doc.classification.value if doc.classification else None
        if cls_value and cls_value not in class_to_doc:
            class_to_doc[cls_value] = doc

    # Load pending item statuses
    statuses_stmt = (
        select(DDItemStatus)
        .where(
            DDItemStatus.checklist_id == checklist_id,
            DDItemStatus.status == "pending",
            DDItemStatus.is_deleted.is_(False),
        )
    )
    statuses_result = await db.execute(statuses_stmt)
    statuses = statuses_result.scalars().all()

    matched = 0
    for item_status in statuses:
        # Load the item to get required_document_types
        item = await db.get(DDChecklistItem, item_status.item_id)
        if not item or not item.required_document_types:
            continue

        for req_type in item.required_document_types:
            doc = class_to_doc.get(req_type)
            if doc:
                item_status.status = "in_review"
                item_status.satisfied_by_document_id = doc.id
                matched += 1
                break

    await db.flush()
    return matched


# ── Completion percentage ─────────────────────────────────────────────────────


async def _update_completion_percentage(
    db: AsyncSession,
    checklist_id: uuid.UUID,
) -> None:
    """Recalculate and update checklist completion percentage."""
    checklist = await db.get(DDProjectChecklist, checklist_id)
    if not checklist:
        return

    stmt = select(DDItemStatus).where(
        DDItemStatus.checklist_id == checklist_id,
        DDItemStatus.is_deleted.is_(False),
    )
    result = await db.execute(stmt)
    all_statuses = result.scalars().all()

    if not all_statuses:
        return

    done_statuses = {"satisfied", "partially_met", "waived"}
    completed = sum(1 for s in all_statuses if s.status in done_statuses)
    total = len(all_statuses)

    percentage = (completed / total * 100) if total > 0 else 0.0
    checklist.completion_percentage = round(percentage, 1)
    checklist.completed_items = completed
    checklist.total_items = total

    if percentage >= 100:
        checklist.status = "completed"
    elif percentage > 0:
        checklist.status = "in_progress"

    await db.flush()
