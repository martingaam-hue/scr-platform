"""Smart Screener API router."""

import uuid

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.modules.smart_screener import service
from app.modules.smart_screener.schemas import (
    ParsedFilters,
    SavedSearchResponse,
    SaveSearchRequest,
    ScreenerQuery,
    ScreenerResponse,
)
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()
router = APIRouter(prefix="/screener", tags=["smart-screener"])


@router.post("/search", response_model=ScreenerResponse)
async def smart_search(
    request: ScreenerQuery,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ScreenerResponse:
    """Parse natural language query into filters and execute deal search."""
    parsed = await service.parse_query(request.query)

    if request.existing_filters:
        parsed = service.merge_filters(parsed, request.existing_filters)

    results = await service.execute_search(db, parsed, current_user.org_id)
    suggestions = service.generate_suggestions(parsed, len(results))

    logger.info(
        "screener_search",
        query=request.query,
        result_count=len(results),
        org_id=str(current_user.org_id),
    )

    return ScreenerResponse(
        query=request.query,
        parsed_filters=parsed,
        results=results,
        total_results=len(results),
        suggestions=suggestions,
    )


@router.get("/saved", response_model=list[SavedSearchResponse])
async def get_saved_searches(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SavedSearchResponse]:
    """Get current user's saved searches."""
    searches = await service.list_saved_searches(db, current_user.user_id)
    return [SavedSearchResponse.model_validate(s) for s in searches]


@router.post("/save", response_model=SavedSearchResponse, status_code=201)
async def save_search(
    body: SaveSearchRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SavedSearchResponse:
    """Save a search for quick access and optional notifications."""
    saved = await service.save_search(
        db,
        user_id=current_user.user_id,
        org_id=current_user.org_id,
        name=body.name,
        query=body.query,
        filters=body.filters,
        notify_new_matches=body.notify_new_matches,
    )
    await db.commit()
    return SavedSearchResponse.model_validate(saved)
