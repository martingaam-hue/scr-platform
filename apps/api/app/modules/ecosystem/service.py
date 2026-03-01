"""Ecosystem service — stakeholder relationship mapping via AITaskLog storage."""

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai import AITaskLog
from app.models.enums import AIAgentType, AITaskStatus
from app.models.projects import Project
from app.modules.ecosystem.schemas import (
    EcosystemMapResponse,
    RelationshipCreate,
    StakeholderCreate,
    StakeholderEdge,
    StakeholderNode,
)


def _default_ecosystem(org_id: uuid.UUID, entity_id: uuid.UUID) -> dict[str, Any]:
    """Return a default ecosystem with a central org node and 3 synthetic stakeholders."""
    org_node_id = f"org-{str(org_id)[:8]}"
    return {
        "nodes": [
            {
                "id": org_node_id,
                "name": "Your Organisation",
                "type": "ally",
                "sub_type": "project_developer",
                "relationship_strength": 5,
                "engagement_status": "active",
                "tags": ["internal"],
                "metadata": None,
            },
            {
                "id": "stakeholder-1",
                "name": "Lead Investor",
                "type": "investor",
                "sub_type": "institutional",
                "relationship_strength": 4,
                "engagement_status": "active",
                "tags": ["strategic", "anchor"],
                "metadata": None,
            },
            {
                "id": "stakeholder-2",
                "name": "Technical Advisor",
                "type": "advisor",
                "sub_type": "technical",
                "relationship_strength": 3,
                "engagement_status": "active",
                "tags": ["advisory"],
                "metadata": None,
            },
            {
                "id": "stakeholder-3",
                "name": "Regulatory Authority",
                "type": "regulator",
                "sub_type": None,
                "relationship_strength": 2,
                "engagement_status": "passive",
                "tags": ["compliance"],
                "metadata": None,
            },
        ],
        "edges": [
            {
                "source": org_node_id,
                "target": "stakeholder-1",
                "relationship_type": "investment",
                "weight": 8,
                "description": "Primary capital provider",
            },
            {
                "source": org_node_id,
                "target": "stakeholder-2",
                "relationship_type": "advisory",
                "weight": 6,
                "description": "Technical due diligence support",
            },
            {
                "source": org_node_id,
                "target": "stakeholder-3",
                "relationship_type": "regulatory",
                "weight": 4,
                "description": "Permitting and compliance",
            },
        ],
    }


async def _build_initial_ecosystem(
    db: AsyncSession,
    org_id: uuid.UUID,
    entity_id: uuid.UUID,
) -> dict[str, Any]:
    """Build initial ecosystem from real DB connections; fall back to synthetic if empty."""
    from app.models.advisory import BoardAdvisorApplication, BoardAdvisorProfile
    from app.models.deal_flow import DealStageTransition
    from app.models.enums import BoardAdvisorApplicationStatus

    org_node_id = f"org-{str(org_id)[:8]}"
    nodes: list[dict[str, Any]] = [
        {
            "id": org_node_id,
            "name": "Your Organisation",
            "type": "ally",
            "sub_type": "project_developer",
            "relationship_strength": 5,
            "engagement_status": "active",
            "tags": ["internal"],
            "metadata": None,
        }
    ]
    edges: list[dict[str, Any]] = []

    # Accepted board advisors for this project
    advisor_result = await db.execute(
        select(BoardAdvisorApplication)
        .where(
            BoardAdvisorApplication.project_id == entity_id,
            BoardAdvisorApplication.status == BoardAdvisorApplicationStatus.ACCEPTED,
        )
        .limit(10)
    )
    for app in advisor_result.scalars().all():
        node_id = f"advisor-{str(app.id)[:8]}"
        nodes.append({
            "id": node_id,
            "name": f"Board Advisor ({app.role_offered or 'Advisor'})",
            "type": "advisor",
            "sub_type": "board",
            "relationship_strength": 4,
            "engagement_status": "active",
            "tags": ["board_advisor"],
            "metadata": {"application_id": str(app.id)},
        })
        edges.append({
            "source": org_node_id,
            "target": node_id,
            "relationship_type": "advisory",
            "weight": 7,
            "description": f"Board advisory: {app.role_offered or 'Advisor'}",
        })

    # Unique investors from deal stage transitions
    trans_result = await db.execute(
        select(DealStageTransition.investor_id)
        .where(
            DealStageTransition.project_id == entity_id,
            DealStageTransition.investor_id.is_not(None),
        )
        .distinct()
        .limit(5)
    )
    for i, (investor_id,) in enumerate(trans_result.all(), 1):
        node_id = f"investor-{str(investor_id)[:8]}"
        nodes.append({
            "id": node_id,
            "name": f"Investor {i}",
            "type": "investor",
            "sub_type": "institutional",
            "relationship_strength": 3,
            "engagement_status": "active",
            "tags": ["deal_pipeline"],
            "metadata": {"investor_id": str(investor_id)},
        })
        edges.append({
            "source": org_node_id,
            "target": node_id,
            "relationship_type": "investment",
            "weight": 6,
            "description": "Active deal pipeline investor",
        })

    # If we got no real connections at all, fall back to synthetic
    if len(nodes) == 1:
        return _default_ecosystem(org_id, entity_id)

    return {"nodes": nodes, "edges": edges}


def _compute_summary(nodes: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute summary stats from node list."""
    by_type: dict[str, int] = {}
    strengths: list[int] = []
    for node in nodes:
        t = node.get("type", "unknown")
        by_type[t] = by_type.get(t, 0) + 1
        s = node.get("relationship_strength", 0)
        if isinstance(s, int):
            strengths.append(s)
    avg_strength = round(sum(strengths) / len(strengths), 1) if strengths else 0.0
    return {
        "total_stakeholders": len(nodes),
        "by_type": by_type,
        "avg_strength": avg_strength,
    }


def _log_to_response(
    log: AITaskLog,
    org_id: uuid.UUID,
    project_id: uuid.UUID | None,
) -> EcosystemMapResponse:
    data: dict[str, Any] = log.output_data or {}
    nodes_raw: list[dict[str, Any]] = data.get("nodes", [])
    edges_raw: list[dict[str, Any]] = data.get("edges", [])
    nodes = [StakeholderNode(**n) for n in nodes_raw]
    edges = [StakeholderEdge(**e) for e in edges_raw]
    summary = _compute_summary(nodes_raw)
    return EcosystemMapResponse(
        project_id=project_id,
        org_id=org_id,
        nodes=nodes,
        edges=edges,
        summary=summary,
        last_updated=log.updated_at,
    )


async def _get_or_create_ecosystem_log(
    db: AsyncSession,
    org_id: uuid.UUID,
    entity_id: uuid.UUID,
) -> AITaskLog:
    """Load the latest ecosystem log for the entity, or create a default one."""
    stmt = (
        select(AITaskLog)
        .where(
            AITaskLog.entity_type == "ecosystem",
            AITaskLog.entity_id == entity_id,
            AITaskLog.org_id == org_id,
        )
        .order_by(AITaskLog.created_at.desc())
        .limit(1)
    )
    log: AITaskLog | None = (await db.execute(stmt)).scalar_one_or_none()
    if log:
        return log

    # Build initial ecosystem from real connections (falls back to synthetic)
    default_data = await _build_initial_ecosystem(db, org_id, entity_id)
    log = AITaskLog(
        org_id=org_id,
        agent_type=AIAgentType.REPORT,
        entity_type="ecosystem",
        entity_id=entity_id,
        status=AITaskStatus.COMPLETED,
        output_data=default_data,
        model_used="deterministic",
    )
    db.add(log)
    await db.flush()
    await db.refresh(log)
    return log


async def get_ecosystem_map(
    db: AsyncSession,
    org_id: uuid.UUID,
    project_id: uuid.UUID | None = None,
) -> EcosystemMapResponse:
    """Get (or auto-create) the ecosystem map for an org or project."""
    entity_id = project_id if project_id is not None else org_id

    if project_id is not None:
        # Verify project belongs to org
        p_stmt = select(Project).where(
            Project.id == project_id,
            Project.org_id == org_id,
            Project.is_deleted.is_(False),
        )
        project: Project | None = (await db.execute(p_stmt)).scalar_one_or_none()
        if not project:
            raise LookupError("Project not found")

    log = await _get_or_create_ecosystem_log(db, org_id, entity_id)
    # Commit the auto-created default if it was new
    return _log_to_response(log, org_id, project_id)


async def add_stakeholder(
    db: AsyncSession,
    org_id: uuid.UUID,
    project_id: uuid.UUID,
    body: StakeholderCreate,
) -> EcosystemMapResponse:
    """Add a stakeholder node to the ecosystem map."""
    entity_id = project_id
    log = await _get_or_create_ecosystem_log(db, org_id, entity_id)
    data: dict[str, Any] = dict(log.output_data or {})
    nodes: list[dict[str, Any]] = list(data.get("nodes", []))

    new_node: dict[str, Any] = {
        "id": f"stakeholder-{uuid.uuid4().hex[:8]}",
        "name": body.name,
        "type": body.type,
        "sub_type": body.sub_type,
        "relationship_strength": body.relationship_strength,
        "engagement_status": body.engagement_status,
        "tags": body.tags,
        "metadata": body.metadata,
    }
    nodes.append(new_node)
    data["nodes"] = nodes
    log.output_data = data
    await db.flush()
    await db.refresh(log)
    return _log_to_response(log, org_id, project_id)


async def add_relationship(
    db: AsyncSession,
    org_id: uuid.UUID,
    project_id: uuid.UUID,
    body: RelationshipCreate,
) -> EcosystemMapResponse:
    """Add a relationship edge between two stakeholders."""
    entity_id = project_id
    log = await _get_or_create_ecosystem_log(db, org_id, entity_id)
    data: dict[str, Any] = dict(log.output_data or {})
    edges: list[dict[str, Any]] = list(data.get("edges", []))

    new_edge: dict[str, Any] = {
        "source": body.source_id,
        "target": body.target_id,
        "relationship_type": body.relationship_type,
        "weight": body.weight,
        "description": body.description,
    }
    edges.append(new_edge)
    data["edges"] = edges
    log.output_data = data
    await db.flush()
    await db.refresh(log)
    return _log_to_response(log, org_id, project_id)
