"""Global search router."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_permission
from app.core.database import get_db
from app.modules.search import service
from app.modules.search.schemas import ReindexResponse, SearchResponse
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=SearchResponse)
async def search(
    q: str = Query(..., min_length=1, max_length=300, description="Search query"),
    limit: int = Query(10, ge=1, le=50),
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    """Full-text search across projects, marketplace listings, and documents."""
    return await service.search(q, current_user.org_id, limit=limit)


@router.post("/reindex", response_model=ReindexResponse, status_code=202)
async def reindex(
    current_user: CurrentUser = Depends(require_permission("manage_settings", "settings")),
    db: AsyncSession = Depends(get_db),
) -> ReindexResponse:
    """Rebuild the ElasticSearch indices from the database. Admin-only."""
    logger.info("search.reindex_requested", user_id=str(current_user.user_id))
    return await service.reindex_all(db)
