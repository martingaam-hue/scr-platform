"""External data feeds admin endpoint."""
import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.services.auth import verify_gateway_key
from app.services.external_data import get_feed_service, FEEDS

logger = structlog.get_logger()
router = APIRouter()


class FeedStatusResponse(BaseModel):
    feeds: dict


@router.get("/feeds/status", response_model=FeedStatusResponse)
async def get_feed_status(
    _api_key: str = Depends(verify_gateway_key),
) -> FeedStatusResponse:
    """Return cache freshness status for all external data feeds."""
    svc = get_feed_service()
    return FeedStatusResponse(feeds=svc.get_cache_status())


@router.post("/feeds/{feed_name}/refresh")
async def refresh_feed(
    feed_name: str,
    _api_key: str = Depends(verify_gateway_key),
) -> dict:
    """Manually trigger a refresh for a specific feed."""
    if feed_name not in FEEDS:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Unknown feed: {feed_name}")
    svc = get_feed_service()
    data = await svc.refresh_feed(feed_name)
    return {"feed": feed_name, "refreshed": True, "records": len(data) if isinstance(data, dict) else 0}


@router.get("/feeds/{feed_name}")
async def get_feed_data(
    feed_name: str,
    _api_key: str = Depends(verify_gateway_key),
) -> dict:
    """Get cached data for a specific feed."""
    if feed_name not in FEEDS:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Unknown feed: {feed_name}")
    svc = get_feed_service()
    data = await svc.get_feed_data(feed_name)
    return {"feed": feed_name, "data": data}
