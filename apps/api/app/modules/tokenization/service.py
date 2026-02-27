"""Tokenization service — uses AITaskLog for metadata storage.

Token records are stored as AITaskLog entries with:
  agent_type = AIAgentType.REPORT
  entity_type = "tokenization"
  entity_id   = project_id
  output_data = {all token fields}
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai import AITaskLog
from app.models.enums import AIAgentType, AITaskStatus
from app.models.projects import Project
from app.modules.tokenization.schemas import (
    TokenHolding,
    TokenizationRequest,
    TokenizationResponse,
    TransferRequest,
)


def _default_cap_table(total_supply: int, lock_up_days: int) -> list[dict[str, Any]]:
    """Generate a default 60/20/20 cap table."""
    now = datetime.now(timezone.utc)
    locked_until = (now + timedelta(days=lock_up_days)).date().isoformat()
    return [
        {
            "holder_name": "Founders",
            "holder_type": "founder",
            "tokens": int(total_supply * 0.60),
            "percentage": 60.0,
            "locked_until": locked_until,
        },
        {
            "holder_name": "Treasury",
            "holder_type": "treasury",
            "tokens": int(total_supply * 0.20),
            "percentage": 20.0,
            "locked_until": None,
        },
        {
            "holder_name": "Investors",
            "holder_type": "investor",
            "tokens": int(total_supply * 0.20),
            "percentage": 20.0,
            "locked_until": None,
        },
    ]


def _log_to_response(log: AITaskLog) -> TokenizationResponse:
    """Convert an AITaskLog record to a TokenizationResponse."""
    data: dict[str, Any] = log.output_data or {}
    cap_table = [TokenHolding(**h) for h in data.get("cap_table", [])]
    return TokenizationResponse(
        id=log.id,
        project_id=uuid.UUID(str(data.get("project_id", log.entity_id))),
        token_name=data.get("token_name", ""),
        token_symbol=data.get("token_symbol", ""),
        total_supply=int(data.get("total_supply", 0)),
        token_price_usd=float(data.get("token_price_usd", 0.0)),
        market_cap_usd=float(data.get("token_price_usd", 0.0)) * int(data.get("total_supply", 0)),
        blockchain=data.get("blockchain", "Ethereum"),
        token_type=data.get("token_type", "security"),
        regulatory_framework=data.get("regulatory_framework", "Reg D"),
        minimum_investment_usd=float(data.get("minimum_investment_usd", 1000.0)),
        lock_up_period_days=int(data.get("lock_up_period_days", 365)),
        status=data.get("status", "draft"),
        cap_table=cap_table,
        transfer_history=data.get("transfer_history", []),
        created_at=log.created_at,
        updated_at=log.updated_at,
    )


async def create_tokenization(
    db: AsyncSession,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    body: TokenizationRequest,
) -> TokenizationResponse:
    """Create a tokenization record for a project."""
    # Verify project exists and belongs to org
    stmt = select(Project).where(
        Project.id == body.project_id,
        Project.org_id == org_id,
        Project.is_deleted.is_(False),
    )
    project: Project | None = (await db.execute(stmt)).scalar_one_or_none()
    if not project:
        raise LookupError("Project not found")

    output_data: dict[str, Any] = {
        "project_id": str(body.project_id),
        "token_name": body.token_name,
        "token_symbol": body.token_symbol,
        "total_supply": body.total_supply,
        "token_price_usd": body.token_price_usd,
        "blockchain": body.blockchain,
        "token_type": body.token_type,
        "regulatory_framework": body.regulatory_framework,
        "minimum_investment_usd": body.minimum_investment_usd,
        "lock_up_period_days": body.lock_up_period_days,
        "status": "draft",
        "cap_table": _default_cap_table(body.total_supply, body.lock_up_period_days),
        "transfer_history": [],
        "metadata": body.metadata or {},
    }

    log = AITaskLog(
        org_id=org_id,
        agent_type=AIAgentType.REPORT,
        entity_type="tokenization",
        entity_id=body.project_id,
        status=AITaskStatus.COMPLETED,
        output_data=output_data,
        triggered_by=user_id,
        model_used="deterministic",
    )
    db.add(log)
    await db.flush()
    await db.refresh(log)
    return _log_to_response(log)


async def get_tokenization(
    db: AsyncSession,
    org_id: uuid.UUID,
    project_id: uuid.UUID,
) -> TokenizationResponse | None:
    """Get the latest tokenization record for a project."""
    stmt = (
        select(AITaskLog)
        .where(
            AITaskLog.entity_type == "tokenization",
            AITaskLog.entity_id == project_id,
            AITaskLog.org_id == org_id,
        )
        .order_by(AITaskLog.created_at.desc())
        .limit(1)
    )
    log: AITaskLog | None = (await db.execute(stmt)).scalar_one_or_none()
    if not log:
        return None
    return _log_to_response(log)


async def list_tokenizations(
    db: AsyncSession,
    org_id: uuid.UUID,
) -> list[TokenizationResponse]:
    """List all tokenization records for an org."""
    stmt = (
        select(AITaskLog)
        .where(
            AITaskLog.entity_type == "tokenization",
            AITaskLog.org_id == org_id,
        )
        .order_by(AITaskLog.created_at.desc())
    )
    rows = (await db.execute(stmt)).scalars().all()
    # Deduplicate by project_id — keep latest per project
    seen: set[str] = set()
    results: list[TokenizationResponse] = []
    for log in rows:
        pid = str(log.entity_id)
        if pid not in seen:
            seen.add(pid)
            results.append(_log_to_response(log))
    return results


async def add_transfer(
    db: AsyncSession,
    org_id: uuid.UUID,
    project_id: uuid.UUID,
    body: TransferRequest,
) -> TokenizationResponse:
    """Append a transfer to the tokenization transfer_history."""
    stmt = (
        select(AITaskLog)
        .where(
            AITaskLog.entity_type == "tokenization",
            AITaskLog.entity_id == project_id,
            AITaskLog.org_id == org_id,
        )
        .order_by(AITaskLog.created_at.desc())
        .limit(1)
    )
    log: AITaskLog | None = (await db.execute(stmt)).scalar_one_or_none()
    if not log:
        raise LookupError("Tokenization record not found for this project")

    data: dict[str, Any] = dict(log.output_data or {})
    transfer_history: list[dict[str, Any]] = list(data.get("transfer_history", []))
    transfer_history.append({
        "id": str(uuid.uuid4()),
        "from_holder": body.from_holder,
        "to_holder": body.to_holder,
        "tokens": body.tokens,
        "price_per_token_usd": body.price_per_token_usd,
        "notes": body.notes,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    data["transfer_history"] = transfer_history
    log.output_data = data
    await db.flush()
    await db.refresh(log)
    return _log_to_response(log)
