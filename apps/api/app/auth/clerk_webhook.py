"""Clerk webhook handler: sync users and organizations from Clerk to our DB.

Verifies signatures using svix (Clerk's webhook infra). Each handler is idempotent.
"""

import uuid

import structlog
from fastapi import HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from svix.webhooks import Webhook, WebhookVerificationError

from app.core.config import settings
from app.models.core import Organization, User
from app.models.enums import OrgType, UserRole

logger = structlog.get_logger()


async def verify_webhook_signature(request: Request) -> dict:
    """Verify the Clerk webhook using svix and return parsed payload."""
    body = await request.body()
    headers = {
        "svix-id": request.headers.get("svix-id", ""),
        "svix-timestamp": request.headers.get("svix-timestamp", ""),
        "svix-signature": request.headers.get("svix-signature", ""),
    }

    try:
        wh = Webhook(settings.CLERK_WEBHOOK_SECRET)
        payload = wh.verify(body, headers)
        return payload
    except WebhookVerificationError as e:
        logger.warning("webhook_verification_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook signature",
        ) from e
    except Exception as e:
        logger.error("webhook_verification_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook verification failed",
        ) from e


# ── Event handlers ────────────────────────────────────────────────────────


async def handle_user_created(data: dict, db: AsyncSession) -> None:
    """Handle user.created: create User + Organization in our DB."""
    clerk_user_id = data.get("id", "")
    email_addresses = data.get("email_addresses", [])
    email = email_addresses[0].get("email_address", "") if email_addresses else ""
    first_name = data.get("first_name", "")
    last_name = data.get("last_name", "")
    full_name = f"{first_name} {last_name}".strip() or email.split("@")[0]
    image_url = data.get("image_url")

    # Idempotency check
    result = await db.execute(
        select(User).where(User.external_auth_id == clerk_user_id)
    )
    if result.scalar_one_or_none():
        logger.info("webhook_user_already_exists", clerk_id=clerk_user_id)
        return

    # Determine organization from Clerk data
    org_memberships = data.get("organization_memberships", [])
    if org_memberships:
        clerk_org = org_memberships[0].get("organization", {})
        org = await _get_or_create_org(
            db,
            clerk_org_id=clerk_org.get("id", ""),
            name=clerk_org.get("name", ""),
            slug=clerk_org.get("slug", ""),
        )
    else:
        org = await _create_default_org(db, full_name, email)

    # Check if this is the first user in the org (gets admin role)
    existing_users = await db.execute(
        select(User.id).where(User.org_id == org.id).limit(1)
    )
    role = UserRole.ADMIN if existing_users.scalar_one_or_none() is None else UserRole.VIEWER

    user = User(
        org_id=org.id,
        email=email,
        full_name=full_name,
        role=role,
        avatar_url=image_url,
        external_auth_id=clerk_user_id,
        is_active=True,
    )
    db.add(user)
    await db.flush()
    logger.info("webhook_user_created", user_id=str(user.id), email=email, role=role.value)


async def handle_user_updated(data: dict, db: AsyncSession) -> None:
    """Handle user.updated: sync email, name, avatar from Clerk."""
    clerk_user_id = data.get("id", "")
    result = await db.execute(
        select(User).where(User.external_auth_id == clerk_user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        logger.warning("webhook_user_not_found", clerk_id=clerk_user_id)
        return

    email_addresses = data.get("email_addresses", [])
    if email_addresses:
        user.email = email_addresses[0].get("email_address", user.email)

    first_name = data.get("first_name", "")
    last_name = data.get("last_name", "")
    if first_name or last_name:
        user.full_name = f"{first_name} {last_name}".strip()

    if data.get("image_url"):
        user.avatar_url = data["image_url"]

    await db.flush()
    logger.info("webhook_user_updated", clerk_id=clerk_user_id)


async def handle_user_deleted(data: dict, db: AsyncSession) -> None:
    """Handle user.deleted: soft-delete the user."""
    clerk_user_id = data.get("id", "")
    result = await db.execute(
        select(User).where(User.external_auth_id == clerk_user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        return

    user.is_active = False
    user.is_deleted = True
    await db.flush()
    logger.info("webhook_user_deleted", clerk_id=clerk_user_id)


async def handle_organization_created(data: dict, db: AsyncSession) -> None:
    """Handle organization.created from Clerk."""
    await _get_or_create_org(
        db,
        clerk_org_id=data.get("id", ""),
        name=data.get("name", ""),
        slug=data.get("slug", ""),
    )


# ── Helpers ───────────────────────────────────────────────────────────────


async def _get_or_create_org(
    db: AsyncSession, clerk_org_id: str, name: str, slug: str
) -> Organization:
    """Find org by slug or create a new one."""
    result = await db.execute(select(Organization).where(Organization.slug == slug))
    org = result.scalar_one_or_none()
    if org:
        return org

    org = Organization(
        name=name,
        slug=slug or clerk_org_id,
        type=OrgType.ALLY,  # default; changeable via admin settings
        settings={"clerk_org_id": clerk_org_id},
    )
    db.add(org)
    await db.flush()
    logger.info("webhook_org_created", org_id=str(org.id), name=name)
    return org


async def _create_default_org(
    db: AsyncSession, user_name: str, email: str
) -> Organization:
    """Create a default personal org for a user without one."""
    slug = email.split("@")[0].lower().replace(".", "-").replace("+", "-")

    # Ensure slug uniqueness
    result = await db.execute(select(Organization).where(Organization.slug == slug))
    if result.scalar_one_or_none():
        slug = f"{slug}-{uuid.uuid4().hex[:6]}"

    org = Organization(
        name=f"{user_name}'s Organization",
        slug=slug,
        type=OrgType.ALLY,
    )
    db.add(org)
    await db.flush()
    return org


# ── Event dispatcher ─────────────────────────────────────────────────────

EVENT_HANDLERS: dict = {
    "user.created": handle_user_created,
    "user.updated": handle_user_updated,
    "user.deleted": handle_user_deleted,
    "organization.created": handle_organization_created,
}
