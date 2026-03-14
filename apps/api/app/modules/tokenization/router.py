"""Tokenization API router."""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_permission
from app.core.database import get_db
from app.modules.tokenization import service
from app.modules.tokenization.schemas import (
    StatusUpdateRequest,
    TokenizationRequest,
    TokenizationResponse,
    TransferRequest,
    TransferResponse,
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
    """Create a tokenization record with initial cap table.

    Holdings must sum to exactly 100 %.  If omitted, a default 60/20/20
    (Founders/Treasury/Investors) allocation is generated.
    """
    try:
        result = await service.create_tokenization(
            db, current_user.org_id, current_user.user_id, body
        )
        await db.commit()
        return result
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("tokenization.create.error", error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to create tokenization") from exc


@router.get("/{record_id}", response_model=TokenizationResponse)
async def get_tokenization(
    record_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
) -> TokenizationResponse:
    """Get a tokenization record by its ID."""
    result = await service.get_tokenization(db, current_user.org_id, record_id)
    if not result:
        raise HTTPException(status_code=404, detail="Tokenization not found")
    return result


@router.post("/{record_id}/transfer", response_model=TransferResponse)
async def add_transfer(
    record_id: uuid.UUID,
    body: TransferRequest,
    current_user: CurrentUser = Depends(require_permission("edit", "project")),
    db: AsyncSession = Depends(get_db),
) -> TransferResponse:
    """Record a token transfer, burn, or mint (append-only audit log)."""
    try:
        result = await service.add_transfer(
            db, current_user.org_id, record_id, body, current_user.user_id
        )
        await db.commit()
        return result
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("tokenization.transfer.error", record_id=str(record_id), error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to record transfer") from exc


@router.patch("/{record_id}/status", response_model=TokenizationResponse)
async def update_status(
    record_id: uuid.UUID,
    body: StatusUpdateRequest,
    current_user: CurrentUser = Depends(require_permission("edit", "project")),
    db: AsyncSession = Depends(get_db),
) -> TokenizationResponse:
    """Update the tokenization status (draft → active → paused / retired).

    The status_changed_at timestamp is updated on every transition so the
    full state-change history is traceable via the database audit log.
    """
    try:
        result = await service.update_status(db, current_user.org_id, record_id, body)
        await db.commit()
        return result
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("tokenization.status.error", record_id=str(record_id), error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to update status") from exc
