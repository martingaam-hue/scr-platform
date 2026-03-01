"""Webhook System API router."""

from __future__ import annotations

import time
import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_permission
from app.core.database import get_db
from app.modules.webhooks.schemas import (
    VALID_EVENTS,
    CreateSubscriptionRequest,
    TestWebhookRequest,
    UpdateSubscriptionRequest,
    WebhookDeliveryResponse,
    WebhookSubscriptionResponse,
)
from app.modules.webhooks.service import WebhookService
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


# ── Events catalog ────────────────────────────────────────────────────────────


@router.get("/events", response_model=list[str])
async def list_valid_events(
    current_user: CurrentUser = Depends(require_permission("view", "project")),
) -> list[str]:
    """Return the list of supported webhook event types."""
    return VALID_EVENTS


# ── Org-level delivery log ────────────────────────────────────────────────────


@router.get("/deliveries", response_model=list[WebhookDeliveryResponse])
async def list_all_deliveries(
    limit: int = Query(100, ge=1, le=500),
    current_user: CurrentUser = Depends(require_permission("admin", "project")),
    db: AsyncSession = Depends(get_db),
) -> list[WebhookDeliveryResponse]:
    """List recent webhook deliveries across all subscriptions for the org."""
    svc = WebhookService(db)
    deliveries = await svc.list_deliveries(current_user.org_id, limit=limit)
    return [WebhookDeliveryResponse.model_validate(d) for d in deliveries]


# ── Subscription CRUD ─────────────────────────────────────────────────────────


@router.post(
    "",
    response_model=WebhookSubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_subscription(
    body: CreateSubscriptionRequest,
    current_user: CurrentUser = Depends(require_permission("admin", "project")),
    db: AsyncSession = Depends(get_db),
) -> WebhookSubscriptionResponse:
    """Register a new webhook endpoint."""
    svc = WebhookService(db)
    sub = await svc.create_subscription(
        current_user.org_id, current_user.user_id, body
    )
    return WebhookSubscriptionResponse.model_validate(sub)


@router.get("", response_model=list[WebhookSubscriptionResponse])
async def list_subscriptions(
    current_user: CurrentUser = Depends(require_permission("admin", "project")),
    db: AsyncSession = Depends(get_db),
) -> list[WebhookSubscriptionResponse]:
    """List all webhook subscriptions for the organisation."""
    svc = WebhookService(db)
    subs = await svc.list_subscriptions(current_user.org_id)
    return [WebhookSubscriptionResponse.model_validate(s) for s in subs]


@router.get("/{subscription_id}", response_model=WebhookSubscriptionResponse)
async def get_subscription(
    subscription_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("admin", "project")),
    db: AsyncSession = Depends(get_db),
) -> WebhookSubscriptionResponse:
    """Get a single webhook subscription."""
    svc = WebhookService(db)
    sub = await svc.get_subscription(current_user.org_id, subscription_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Webhook subscription not found")
    return WebhookSubscriptionResponse.model_validate(sub)


@router.put("/{subscription_id}", response_model=WebhookSubscriptionResponse)
async def update_subscription(
    subscription_id: uuid.UUID,
    body: UpdateSubscriptionRequest,
    current_user: CurrentUser = Depends(require_permission("admin", "project")),
    db: AsyncSession = Depends(get_db),
) -> WebhookSubscriptionResponse:
    """Update a webhook subscription."""
    svc = WebhookService(db)
    sub = await svc.update_subscription(current_user.org_id, subscription_id, body)
    if not sub:
        raise HTTPException(status_code=404, detail="Webhook subscription not found")
    return WebhookSubscriptionResponse.model_validate(sub)


@router.delete(
    "/{subscription_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def delete_subscription(
    subscription_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("admin", "project")),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a webhook subscription and all its deliveries."""
    svc = WebhookService(db)
    deleted = await svc.delete_subscription(current_user.org_id, subscription_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Webhook subscription not found")


# ── Enable / Disable ──────────────────────────────────────────────────────────


@router.post("/{subscription_id}/enable", response_model=WebhookSubscriptionResponse)
async def enable_subscription(
    subscription_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("admin", "project")),
    db: AsyncSession = Depends(get_db),
) -> WebhookSubscriptionResponse:
    """Re-enable a webhook subscription (resets failure count)."""
    svc = WebhookService(db)
    sub = await svc.enable_subscription(current_user.org_id, subscription_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Webhook subscription not found")
    return WebhookSubscriptionResponse.model_validate(sub)


@router.post("/{subscription_id}/disable", response_model=WebhookSubscriptionResponse)
async def disable_subscription(
    subscription_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("admin", "project")),
    db: AsyncSession = Depends(get_db),
) -> WebhookSubscriptionResponse:
    """Manually disable a webhook subscription."""
    svc = WebhookService(db)
    sub = await svc.disable_subscription(current_user.org_id, subscription_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Webhook subscription not found")
    return WebhookSubscriptionResponse.model_validate(sub)


# ── Test & Deliveries ─────────────────────────────────────────────────────────


@router.post("/{subscription_id}/test", response_model=WebhookDeliveryResponse)
async def test_subscription(
    subscription_id: uuid.UUID,
    body: TestWebhookRequest,
    current_user: CurrentUser = Depends(require_permission("admin", "project")),
    db: AsyncSession = Depends(get_db),
) -> WebhookDeliveryResponse:
    """Send a test event to the webhook endpoint."""
    from app.models.webhooks import WebhookDelivery

    svc = WebhookService(db)
    sub = await svc.get_subscription(current_user.org_id, subscription_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Webhook subscription not found")

    delivery = WebhookDelivery(
        subscription_id=sub.id,
        org_id=current_user.org_id,
        event_type=body.event_type,
        payload={
            "event": body.event_type,
            "data": {"test": True},
            "timestamp": int(time.time()),
        },
        status="pending",
    )
    db.add(delivery)
    await db.flush()
    await db.refresh(delivery)

    from app.modules.webhooks.tasks import deliver_webhook_task

    deliver_webhook_task.delay(str(delivery.id))

    await db.commit()
    return WebhookDeliveryResponse.model_validate(delivery)


@router.get(
    "/{subscription_id}/deliveries",
    response_model=list[WebhookDeliveryResponse],
)
async def list_subscription_deliveries(
    subscription_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=200),
    current_user: CurrentUser = Depends(require_permission("admin", "project")),
    db: AsyncSession = Depends(get_db),
) -> list[WebhookDeliveryResponse]:
    """List delivery attempts for a specific webhook subscription."""
    svc = WebhookService(db)
    # Verify subscription belongs to org
    sub = await svc.get_subscription(current_user.org_id, subscription_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Webhook subscription not found")

    deliveries = await svc.list_deliveries(
        current_user.org_id, subscription_id=subscription_id, limit=limit
    )
    return [WebhookDeliveryResponse.model_validate(d) for d in deliveries]
