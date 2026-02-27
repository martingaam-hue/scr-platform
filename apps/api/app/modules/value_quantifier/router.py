"""Value Quantifier API router — deterministic financial KPIs."""

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_permission
from app.core.database import get_db
from app.modules.value_quantifier import service
from app.modules.value_quantifier.schemas import (
    ValueQuantifierRequest,
    ValueQuantifierResponse,
)
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()

router = APIRouter(prefix="/value-quantifier", tags=["value-quantifier"])


@router.post("/calculate", response_model=ValueQuantifierResponse)
async def calculate_value(
    body: ValueQuantifierRequest,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
) -> ValueQuantifierResponse:
    """Calculate deterministic financial KPIs for a project.

    All calculations are pure Python — no LLM calls. Override defaults
    via the request body to run sensitivity scenarios.
    """
    try:
        return await service.calculate_value(db, current_user.org_id, body)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error("value_quantifier.calculate.error", error=str(exc))
        raise HTTPException(status_code=500, detail="Calculation failed")


@router.get("/{project_id}", response_model=ValueQuantifierResponse)
async def get_value_quantifier(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
) -> ValueQuantifierResponse:
    """Get value quantification for a project using default assumptions."""
    req = ValueQuantifierRequest(project_id=project_id)
    try:
        return await service.calculate_value(db, current_user.org_id, req)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error("value_quantifier.get.error", project_id=str(project_id), error=str(exc))
        raise HTTPException(status_code=500, detail="Calculation failed")
