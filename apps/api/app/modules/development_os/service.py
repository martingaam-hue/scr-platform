"""Development OS service — project construction lifecycle management."""

import uuid
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import MilestoneStatus, ProjectStage
from app.models.projects import Project, ProjectMilestone
from app.modules.development_os.schemas import (
    ConstructionPhase,
    DevelopmentOSResponse,
    MilestoneCreate,
    MilestoneResponse,
    MilestoneUpdate,
    ProcurementItem,
)

# ── Phase keyword mapping ────────────────────────────────────────────────────

PHASE_PATTERNS: dict[str, list[str]] = {
    "Pre-Development": ["feasibility", "permitting", "environmental", "land", "site", "survey", "assessment", "study"],
    "Development": ["design", "engineering", "financing", "procurement", "planning", "approval", "regulatory"],
    "Construction": ["civil", "electrical", "mechanical", "commissioning", "installation", "build", "construction"],
    "Operations": ["operations", "maintenance", "monitoring", "reporting", "inspection", "performance"],
}

# Synthetic procurement items keyed by project_type prefix
PROCUREMENT_TEMPLATES: dict[str, list[dict[str, Any]]] = {
    "solar": [
        {"name": "PV Modules", "category": "Equipment", "vendor": "LONGi Solar", "cost": 850_000},
        {"name": "Inverters", "category": "Equipment", "vendor": "SMA Solar", "cost": 120_000},
        {"name": "Mounting Structures", "category": "Civil", "vendor": None, "cost": 95_000},
        {"name": "Cables & Wiring", "category": "Electrical", "vendor": None, "cost": 45_000},
        {"name": "SCADA System", "category": "Controls", "vendor": "Schneider Electric", "cost": 35_000},
    ],
    "wind": [
        {"name": "Wind Turbines", "category": "Equipment", "vendor": "Vestas", "cost": 4_200_000},
        {"name": "Foundations", "category": "Civil", "vendor": None, "cost": 650_000},
        {"name": "Grid Connection Cable", "category": "Electrical", "vendor": None, "cost": 280_000},
        {"name": "SCADA & Controls", "category": "Controls", "vendor": "ABB", "cost": 75_000},
        {"name": "Cranes & Logistics", "category": "Logistics", "vendor": None, "cost": 180_000},
    ],
    "default": [
        {"name": "Primary Equipment", "category": "Equipment", "vendor": None, "cost": 1_200_000},
        {"name": "Civil Works", "category": "Civil", "vendor": None, "cost": 350_000},
        {"name": "Electrical Systems", "category": "Electrical", "vendor": None, "cost": 180_000},
        {"name": "Controls & Instrumentation", "category": "Controls", "vendor": None, "cost": 90_000},
        {"name": "Professional Services", "category": "Services", "vendor": None, "cost": 120_000},
    ],
}

PROCUREMENT_STATUSES = ["contracted", "rfq_sent", "negotiating", "pending", "contracted"]


def _classify_milestone(title: str) -> str:
    """Return the phase name that best matches a milestone title."""
    title_lower = title.lower()
    for phase_name, keywords in PHASE_PATTERNS.items():
        if any(kw in title_lower for kw in keywords):
            return phase_name
    return "Development"  # fallback


def _milestone_to_response(m: ProjectMilestone) -> MilestoneResponse:
    return MilestoneResponse(
        id=m.id,
        project_id=m.project_id,
        title=m.name,
        description=m.description or None,
        due_date=m.target_date,
        completed_date=m.completed_date,
        status=m.status.value,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


def _phase_status(milestones: list[MilestoneResponse]) -> str:
    if not milestones:
        return "not_started"
    statuses = {m.status for m in milestones}
    if "completed" in statuses and len(statuses) == 1:
        return "completed"
    if {"in_progress", "completed"} & statuses:
        return "in_progress"
    return "not_started"


def _build_procurement(project_type: str) -> list[ProcurementItem]:
    key = "default"
    for k in PROCUREMENT_TEMPLATES:
        if k != "default" and project_type.startswith(k):
            key = k
            break
    templates = PROCUREMENT_TEMPLATES[key]
    items: list[ProcurementItem] = []
    for i, t in enumerate(templates):
        items.append(ProcurementItem(
            id=f"proc-{i+1}",
            name=t["name"],
            vendor=t.get("vendor"),
            category=t["category"],
            estimated_cost_usd=float(t.get("cost", 0)),
            status=PROCUREMENT_STATUSES[i % len(PROCUREMENT_STATUSES)],
            delivery_date=None,
            notes=None,
        ))
    return items


def _str_to_milestone_status(s: str) -> MilestoneStatus:
    mapping = {
        "not_started": MilestoneStatus.NOT_STARTED,
        "in_progress": MilestoneStatus.IN_PROGRESS,
        "completed": MilestoneStatus.COMPLETED,
        "delayed": MilestoneStatus.DELAYED,
        "blocked": MilestoneStatus.BLOCKED,
        # Legacy aliases
        "planned": MilestoneStatus.NOT_STARTED,
    }
    return mapping.get(s.lower(), MilestoneStatus.NOT_STARTED)


# ── Public service functions ─────────────────────────────────────────────────

async def get_development_overview(
    db: AsyncSession,
    org_id: uuid.UUID,
    project_id: uuid.UUID,
) -> DevelopmentOSResponse:
    """Return a full Development OS overview for a project."""
    # Load project
    stmt = select(Project).where(
        Project.id == project_id,
        Project.org_id == org_id,
        Project.is_deleted.is_(False),
    )
    project: Project | None = (await db.execute(stmt)).scalar_one_or_none()
    if not project:
        raise LookupError("Project not found")

    # Load milestones
    ms_stmt = (
        select(ProjectMilestone)
        .where(ProjectMilestone.project_id == project_id)
        .order_by(ProjectMilestone.target_date.asc())
    )
    milestones = list((await db.execute(ms_stmt)).scalars().all())
    ms_responses = [_milestone_to_response(m) for m in milestones]

    # Group milestones into phases
    phase_map: dict[str, list[MilestoneResponse]] = {k: [] for k in PHASE_PATTERNS}
    for mr in ms_responses:
        phase_name = _classify_milestone(mr.title)
        phase_map.setdefault(phase_name, []).append(mr)

    phases: list[ConstructionPhase] = []
    for phase_name in PHASE_PATTERNS:
        phase_ms = phase_map.get(phase_name, [])
        total = len(phase_ms)
        completed = sum(1 for m in phase_ms if m.status == "completed")
        comp_pct = round((completed / total * 100) if total > 0 else 0.0, 1)

        # Derive start/end dates from milestones
        dates = [m.due_date for m in phase_ms if m.due_date is not None]
        start_date = min(dates) if dates else None
        end_date = max(dates) if dates else None

        phases.append(ConstructionPhase(
            phase_name=phase_name,
            start_date=start_date,
            end_date=end_date,
            completion_pct=comp_pct,
            milestones=phase_ms,
            status=_phase_status(phase_ms),
        ))

    # Overall completion
    total_ms = len(ms_responses)
    completed_ms = sum(1 for m in ms_responses if m.status == "completed")
    overall_pct = round((completed_ms / total_ms * 100) if total_ms > 0 else 0.0, 1)

    # Next pending milestone (closest future due_date)
    today = date.today()
    pending = [
        m for m in ms_responses
        if m.status not in ("completed",) and m.due_date is not None
    ]
    next_milestone: MilestoneResponse | None = None
    days_to_next: int | None = None
    if pending:
        next_milestone = min(pending, key=lambda m: m.due_date)  # type: ignore[arg-type]
        delta = (next_milestone.due_date - today).days  # type: ignore[operator]
        days_to_next = delta

    # Synthetic procurement list
    project_type = project.project_type.value if project.project_type else "default"
    procurement = _build_procurement(project_type)

    return DevelopmentOSResponse(
        project_id=project.id,
        project_name=project.name,
        project_stage=project.stage.value,
        overall_completion_pct=overall_pct,
        phases=phases,
        procurement=procurement,
        next_milestone=next_milestone,
        days_to_next_milestone=days_to_next,
        last_updated=datetime.now(timezone.utc),
    )


async def list_milestones(
    db: AsyncSession,
    org_id: uuid.UUID,
    project_id: uuid.UUID,
) -> list[MilestoneResponse]:
    """List all milestones for a project."""
    # Verify project ownership
    p_stmt = select(Project).where(
        Project.id == project_id,
        Project.org_id == org_id,
        Project.is_deleted.is_(False),
    )
    project: Project | None = (await db.execute(p_stmt)).scalar_one_or_none()
    if not project:
        raise LookupError("Project not found")

    stmt = (
        select(ProjectMilestone)
        .where(ProjectMilestone.project_id == project_id)
        .order_by(ProjectMilestone.order_index.asc(), ProjectMilestone.target_date.asc())
    )
    rows = (await db.execute(stmt)).scalars().all()
    return [_milestone_to_response(m) for m in rows]


async def create_milestone(
    db: AsyncSession,
    org_id: uuid.UUID,
    project_id: uuid.UUID,
    body: MilestoneCreate,
) -> MilestoneResponse:
    """Create a new project milestone."""
    p_stmt = select(Project).where(
        Project.id == project_id,
        Project.org_id == org_id,
        Project.is_deleted.is_(False),
    )
    project: Project | None = (await db.execute(p_stmt)).scalar_one_or_none()
    if not project:
        raise LookupError("Project not found")

    milestone = ProjectMilestone(
        project_id=project_id,
        name=body.title,
        description=body.description or "",
        target_date=body.due_date or date.today(),
        status=_str_to_milestone_status(body.status),
    )
    db.add(milestone)
    await db.flush()
    await db.refresh(milestone)
    return _milestone_to_response(milestone)


async def update_milestone(
    db: AsyncSession,
    org_id: uuid.UUID,
    milestone_id: uuid.UUID,
    body: MilestoneUpdate,
) -> MilestoneResponse:
    """Update an existing milestone."""
    # Join to project to verify org ownership
    stmt = (
        select(ProjectMilestone)
        .join(Project, Project.id == ProjectMilestone.project_id)
        .where(
            ProjectMilestone.id == milestone_id,
            Project.org_id == org_id,
            Project.is_deleted.is_(False),
        )
    )
    milestone: ProjectMilestone | None = (await db.execute(stmt)).scalar_one_or_none()
    if not milestone:
        raise LookupError("Milestone not found")

    if body.title is not None:
        milestone.name = body.title
    if body.description is not None:
        milestone.description = body.description
    if body.due_date is not None:
        milestone.target_date = body.due_date
    if body.completed_date is not None:
        milestone.completed_date = body.completed_date
    if body.status is not None:
        milestone.status = _str_to_milestone_status(body.status)
        if body.status == "completed" and not milestone.completed_date:
            milestone.completed_date = date.today()

    await db.flush()
    await db.refresh(milestone)
    return _milestone_to_response(milestone)


async def delete_milestone(
    db: AsyncSession,
    org_id: uuid.UUID,
    milestone_id: uuid.UUID,
) -> None:
    """Delete a milestone."""
    stmt = (
        select(ProjectMilestone)
        .join(Project, Project.id == ProjectMilestone.project_id)
        .where(
            ProjectMilestone.id == milestone_id,
            Project.org_id == org_id,
            Project.is_deleted.is_(False),
        )
    )
    milestone: ProjectMilestone | None = (await db.execute(stmt)).scalar_one_or_none()
    if not milestone:
        raise LookupError("Milestone not found")
    await db.delete(milestone)
    await db.flush()
