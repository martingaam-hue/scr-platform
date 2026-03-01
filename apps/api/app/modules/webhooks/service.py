"""Webhook delivery service."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid
from datetime import datetime, timedelta

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.webhooks import WebhookDelivery, WebhookSubscription
from app.modules.webhooks.schemas import CreateSubscriptionRequest, UpdateSubscriptionRequest

logger = structlog.get_logger()


class WebhookService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Subscription CRUD ─────────────────────────────────────────────────────

    async def create_subscription(
        self,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        data: CreateSubscriptionRequest,
    ) -> WebhookSubscription:
        sub = WebhookSubscription(
            org_id=org_id,
            created_by=user_id,
            url=data.url,
            secret=data.secret,
            events=data.events,
            description=data.description,
        )
        self.db.add(sub)
        await self.db.commit()
        await self.db.refresh(sub)
        return sub

    async def list_subscriptions(self, org_id: uuid.UUID) -> list[WebhookSubscription]:
        stmt = (
            select(WebhookSubscription)
            .where(WebhookSubscription.org_id == org_id)
            .order_by(WebhookSubscription.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_subscription(
        self, org_id: uuid.UUID, sub_id: uuid.UUID
    ) -> WebhookSubscription | None:
        stmt = select(WebhookSubscription).where(
            WebhookSubscription.id == sub_id,
            WebhookSubscription.org_id == org_id,
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def update_subscription(
        self,
        org_id: uuid.UUID,
        sub_id: uuid.UUID,
        data: UpdateSubscriptionRequest,
    ) -> WebhookSubscription | None:
        sub = await self.get_subscription(org_id, sub_id)
        if not sub:
            return None
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(sub, k, v)
        await self.db.commit()
        await self.db.refresh(sub)
        return sub

    async def delete_subscription(
        self, org_id: uuid.UUID, sub_id: uuid.UUID
    ) -> bool:
        sub = await self.get_subscription(org_id, sub_id)
        if not sub:
            return False
        await self.db.delete(sub)
        await self.db.commit()
        return True

    async def enable_subscription(
        self, org_id: uuid.UUID, sub_id: uuid.UUID
    ) -> WebhookSubscription | None:
        sub = await self.get_subscription(org_id, sub_id)
        if not sub:
            return None
        sub.is_active = True
        sub.failure_count = 0
        sub.disabled_reason = None
        await self.db.commit()
        await self.db.refresh(sub)
        return sub

    async def disable_subscription(
        self, org_id: uuid.UUID, sub_id: uuid.UUID
    ) -> WebhookSubscription | None:
        sub = await self.get_subscription(org_id, sub_id)
        if not sub:
            return None
        sub.is_active = False
        sub.disabled_reason = "Manually disabled"
        await self.db.commit()
        await self.db.refresh(sub)
        return sub

    # ── Event firing ──────────────────────────────────────────────────────────

    async def fire_event(
        self, org_id: uuid.UUID, event_type: str, payload: dict
    ) -> int:
        """Find all active subscriptions for this org+event, queue deliveries.

        Returns the number of deliveries queued.
        """
        stmt = select(WebhookSubscription).where(
            WebhookSubscription.org_id == org_id,
            WebhookSubscription.is_active.is_(True),
        )
        subs = (await self.db.execute(stmt)).scalars().all()

        deliveries_to_queue: list[WebhookDelivery] = []
        for sub in subs:
            if event_type in sub.events or "*" in sub.events:
                delivery = WebhookDelivery(
                    subscription_id=sub.id,
                    org_id=org_id,
                    event_type=event_type,
                    payload={
                        "event": event_type,
                        "data": payload,
                        "timestamp": int(time.time()),
                    },
                    status="pending",
                )
                self.db.add(delivery)
                deliveries_to_queue.append(delivery)

        if not deliveries_to_queue:
            return 0

        await self.db.flush()

        # Refresh to get server-generated IDs, then queue Celery tasks
        from app.modules.webhooks.tasks import deliver_webhook_task

        for delivery in deliveries_to_queue:
            await self.db.refresh(delivery)
            deliver_webhook_task.delay(str(delivery.id))

        await self.db.commit()
        return len(deliveries_to_queue)

    # ── Delivery ──────────────────────────────────────────────────────────────

    @staticmethod
    def _sign_payload(secret: str, body: bytes) -> str:
        return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    async def deliver(self, delivery_id: uuid.UUID) -> bool:
        """Attempt HTTP delivery with HMAC signature. Called from Celery."""
        stmt = select(WebhookDelivery).where(WebhookDelivery.id == delivery_id)
        delivery = (await self.db.execute(stmt)).scalar_one_or_none()
        if not delivery:
            return False

        stmt2 = select(WebhookSubscription).where(
            WebhookSubscription.id == delivery.subscription_id
        )
        sub = (await self.db.execute(stmt2)).scalar_one_or_none()
        if not sub:
            delivery.status = "failed"
            delivery.error_message = "Subscription not found"
            await self.db.commit()
            return False

        body = json.dumps(delivery.payload).encode()
        signature = self._sign_payload(sub.secret, body)

        delivery.attempts += 1
        delivery.status = "retrying"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    sub.url,
                    content=body,
                    headers={
                        "Content-Type": "application/json",
                        "X-SCR-Signature": signature,
                        "X-SCR-Event": delivery.event_type,
                        "X-SCR-Delivery": str(delivery.id),
                    },
                )
            delivery.response_status_code = resp.status_code
            delivery.response_body = resp.text[:1000]

            if resp.status_code < 300:
                delivery.status = "delivered"
                delivery.delivered_at = datetime.utcnow()
                # Reset failure count on success
                sub.failure_count = max(0, sub.failure_count - 1)
            else:
                raise Exception(f"HTTP {resp.status_code}")

        except Exception as exc:
            delivery.error_message = str(exc)[:500]
            sub.failure_count += 1

            # Exponential retry: 1m, 5m, 15m, 1h, 4h
            retry_delays = [60, 300, 900, 3600, 14400]
            if delivery.attempts <= len(retry_delays):
                delivery.next_retry_at = datetime.utcnow() + timedelta(
                    seconds=retry_delays[delivery.attempts - 1]
                )
                delivery.status = "retrying"
            else:
                delivery.status = "failed"

            # Auto-disable after 10 consecutive failures
            if sub.failure_count >= 10:
                sub.is_active = False
                sub.disabled_reason = (
                    "Auto-disabled: 10 consecutive delivery failures"
                )

            logger.warning(
                "webhook_delivery_failed",
                delivery_id=str(delivery_id),
                attempts=delivery.attempts,
                error=str(exc)[:200],
            )

        await self.db.commit()
        return delivery.status == "delivered"

    # ── Deliveries list ───────────────────────────────────────────────────────

    async def list_deliveries(
        self,
        org_id: uuid.UUID,
        subscription_id: uuid.UUID | None = None,
        limit: int = 50,
    ) -> list[WebhookDelivery]:
        stmt = select(WebhookDelivery).where(WebhookDelivery.org_id == org_id)
        if subscription_id:
            stmt = stmt.where(WebhookDelivery.subscription_id == subscription_id)
        stmt = stmt.order_by(WebhookDelivery.created_at.desc()).limit(limit)
        return list((await self.db.execute(stmt)).scalars().all())
