"""Tokenization API router."""

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_permission
from app.core.database import get_db
from app.modules.tokenization import service
from app.modules.tokenization.schemas import (
    TokenizationRequest,
    TokenizationResponse,
    TransferRequest,
)
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()

router = APIRouter(prefix="/tokenization", tags=["tokenization"])


@router.get("", response_model=list[TokenizationResponse])
async def list_tokenizations(
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
) -> list[TokenizationResponse]:
    """List all tokenized projects for the organisation."""
    return await service.list_tokenizations(db, current_user.org_id)


@router.post("", response_model=TokenizationResponse, status_code=status.HTTP_201_CREATED)
async def create_tokenization(
    body: TokenizationRequest,
    current_user: CurrentUser = Depends(require_permission("create", "project")),
    db: AsyncSession = Depends(get_db),
) -> TokenizationResponse:
    """Create a tokenization record for a project."""
    try:
        result = await service.create_tokenization(
            db, current_user.org_id, current_user.user_id, body
        )
        await db.commit()
        return result
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error("tokenization.create.error", error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to create tokenization")


@router.get("/{project_id}", response_model=TokenizationResponse)
async def get_tokenization(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
) -> TokenizationResponse:
    """Get the latest tokenization record for a project."""
    result = await service.get_tokenization(db, current_user.org_id, project_id)
    if not result:
        raise HTTPException(status_code=404, detail="Tokenization not found")
    return result


@router.post("/{project_id}/transfer", response_model=TokenizationResponse)
async def add_transfer(
    project_id: uuid.UUID,
    body: TransferRequest,
    current_user: CurrentUser = Depends(require_permission("edit", "project")),
    db: AsyncSession = Depends(get_db),
) -> TokenizationResponse:
    """Record a token transfer for a project."""
    try:
        result = await service.add_transfer(db, current_user.org_id, project_id, body)
        await db.commit()
        return result
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error("tokenization.transfer.error", project_id=str(project_id), error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to record transfer")
