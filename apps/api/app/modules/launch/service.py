"""Service layer for E04 Launch Preparation module."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.launch import FeatureFlag, FeatureFlagOverride, UsageEvent, WaitlistEntry
from app.modules.launch.schemas import FeatureFlagResponse

logger = structlog.get_logger()

# ── Default flags seeded at startup ───────────────────────────────────────────

DEFAULT_FLAGS: list[tuple[str, str, bool]] = [
    ("deal_rooms", "Collaborative deal rooms", True),
    ("ai_redaction", "AI-powered document redaction", True),
    ("webhooks", "Outbound webhook subscriptions", True),
    ("pdf_annotations", "PDF viewer with annotations", True),
    ("expert_insights", "Expert notes with AI enrichment", True),
    ("market_data", "Public market data indicators", True),
    ("score_backtesting", "Signal score backtesting framework", True),
]


async def seed_default_flags(db: AsyncSession) -> None:
    """Insert default feature flags if they do not already exist.

    Called from the FastAPI lifespan startup hook.
    """
    for name, description, enabled in DEFAULT_FLAGS:
        existing = await db.execute(
            select(FeatureFlag).where(FeatureFlag.name == name)
        )
        if existing.scalar_one_or_none() is None:
            flag = FeatureFlag(
                name=name,
                description=description,
                enabled_globally=enabled,
                rollout_pct=100,
            )
            db.add(flag)
            logger.info("feature_flag_seeded", flag=name)

    await db.commit()


# ── Service class ─────────────────────────────────────────────────────────────


class LaunchService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Feature flags ──────────────────────────────────────────────────────────

    async def is_feature_enabled(self, flag_name: str, org_id: uuid.UUID) -> bool:
        """Return True if the feature is enabled for the given org.

        Per-org overrides take priority over the global setting.
        """
        # Check org-level override first
        override_stmt = select(FeatureFlagOverride).where(
            FeatureFlagOverride.flag_name == flag_name,
            FeatureFlagOverride.org_id == org_id,
        )
        override = (await self.db.execute(override_stmt)).scalar_one_or_none()
        if override is not None:
            return override.enabled

        # Fall back to global setting
        flag_stmt = select(FeatureFlag).where(FeatureFlag.name == flag_name)
        flag = (await self.db.execute(flag_stmt)).scalar_one_or_none()
        if flag is None:
            return False  # Unknown flags default to disabled
        return flag.enabled_globally

    async def set_org_override(
        self, flag_name: str, org_id: uuid.UUID, enabled: bool
    ) -> FeatureFlagOverride:
        """Create or update a per-org override for a feature flag."""
        stmt = select(FeatureFlagOverride).where(
            FeatureFlagOverride.flag_name == flag_name,
            FeatureFlagOverride.org_id == org_id,
        )
        override = (await self.db.execute(stmt)).scalar_one_or_none()

        if override is None:
            override = FeatureFlagOverride(
                flag_name=flag_name,
                org_id=org_id,
                enabled=enabled,
            )
            self.db.add(override)
        else:
            override.enabled = enabled

        await self.db.commit()
        await self.db.refresh(override)
        return override

    async def list_flags(self, org_id: uuid.UUID) -> list[FeatureFlagResponse]:
        """List all feature flags with the current org's override value if set."""
        flags_stmt = select(FeatureFlag).order_by(FeatureFlag.name)
        flags = list((await self.db.execute(flags_stmt)).scalars().all())

        overrides_stmt = select(FeatureFlagOverride).where(
            FeatureFlagOverride.org_id == org_id
        )
        overrides = {
            o.flag_name: o.enabled
            for o in (await self.db.execute(overrides_stmt)).scalars().all()
        }

        return [
            FeatureFlagResponse(
                name=f.name,
                description=f.description,
                enabled_globally=f.enabled_globally,
                rollout_pct=f.rollout_pct,
                org_override=overrides.get(f.name),
            )
            for f in flags
        ]

    # ── Usage events ───────────────────────────────────────────────────────────

    async def record_usage(
        self,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        event_type: str,
        entity_type: str | None = None,
        entity_id: uuid.UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> UsageEvent:
        """Append a usage event for the given org/user."""
        event = UsageEvent(
            org_id=org_id,
            user_id=user_id,
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            event_metadata=metadata or {},
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)
        return event

    async def get_usage_summary(
        self, org_id: uuid.UUID, days: int = 30
    ) -> dict[str, Any]:
        """Return usage event counts grouped by event_type for the last N days."""
        since = datetime.utcnow() - timedelta(days=days)

        stmt = (
            select(UsageEvent.event_type, func.count(UsageEvent.id).label("count"))
            .where(
                UsageEvent.org_id == org_id,
                UsageEvent.created_at >= since,
            )
            .group_by(UsageEvent.event_type)
            .order_by(func.count(UsageEvent.id).desc())
        )
        rows = (await self.db.execute(stmt)).all()

        return {
            "org_id": str(org_id),
            "days": days,
            "since": since.isoformat(),
            "totals": {row.event_type: row.count for row in rows},
            "total_events": sum(row.count for row in rows),
        }

    # ── Waitlist ───────────────────────────────────────────────────────────────

    async def create_waitlist_entry(
        self,
        email: str,
        name: str | None = None,
        company: str | None = None,
        use_case: str | None = None,
    ) -> WaitlistEntry:
        """Add a new entry to the waitlist. Raises if the email already exists."""
        # Check for duplicate
        stmt = select(WaitlistEntry).where(WaitlistEntry.email == email.lower())
        existing = (await self.db.execute(stmt)).scalar_one_or_none()
        if existing:
            return existing  # Idempotent — return the existing entry

        entry = WaitlistEntry(
            email=email.lower(),
            name=name,
            company=company,
            use_case=use_case,
            status="pending",
        )
        self.db.add(entry)
        await self.db.commit()
        await self.db.refresh(entry)
        logger.info("waitlist_entry_created", email=email)
        return entry

    async def approve_waitlist_entry(self, entry_id: uuid.UUID) -> WaitlistEntry | None:
        """Approve a waitlist entry by ID."""
        stmt = select(WaitlistEntry).where(WaitlistEntry.id == entry_id)
        entry = (await self.db.execute(stmt)).scalar_one_or_none()
        if not entry:
            return None
        entry.status = "approved"
        entry.approved_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(entry)
        return entry

    async def list_waitlist(
        self, status_filter: str | None = None
    ) -> list[WaitlistEntry]:
        """List waitlist entries, optionally filtered by status."""
        stmt = select(WaitlistEntry).order_by(WaitlistEntry.created_at.desc())
        if status_filter:
            stmt = stmt.where(WaitlistEntry.status == status_filter)
        return list((await self.db.execute(stmt)).scalars().all())
