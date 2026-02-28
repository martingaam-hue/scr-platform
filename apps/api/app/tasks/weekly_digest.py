"""Weekly digest Celery task — runs every Sunday at 20:00 UTC."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta

import structlog
from celery import shared_task

logger = structlog.get_logger()


@shared_task(name="tasks.send_weekly_digests", bind=True, max_retries=3)
def send_weekly_digests(self) -> dict:
    """Send weekly AI activity digest emails to opted-in users."""
    return asyncio.get_event_loop().run_until_complete(_async_send_digests())


async def _async_send_digests() -> dict:
    from sqlalchemy import select

    from app.core.database import async_session_factory
    from app.models.core import Organization, User
    from app.modules.digest import service as digest_service

    since = datetime.utcnow() - timedelta(days=7)
    sent = 0
    failed = 0

    async with async_session_factory() as db:
        # Get all active users with digest enabled
        stmt = (
            select(User, Organization.name.label("org_name"))
            .join(Organization, User.org_id == Organization.id)
            .where(
                User.is_active.is_(True),
                User.preferences["email_digest_enabled"].as_boolean().is_(True),
            )
        )
        result = await db.execute(stmt)
        rows = result.all()

        for row in rows:
            user = row[0]
            org_name = row[1]
            try:
                activity = await digest_service.gather_digest_data(
                    db, user.org_id, user.id, since
                )
                summary = await digest_service.generate_digest_summary(activity, org_name)
                await _send_digest_email(user.email, user.full_name, org_name, activity, summary)
                sent += 1
            except Exception as e:
                logger.warning("digest_send_failed", user_id=str(user.id), error=str(e))
                failed += 1

    logger.info("weekly_digest_complete", sent=sent, failed=failed)
    return {"sent": sent, "failed": failed}


async def _send_digest_email(
    email: str,
    full_name: str,
    org_name: str,
    activity: dict,
    summary: str,
) -> None:
    """Send digest email via SES or SMTP."""
    from app.core.config import settings

    if not getattr(settings, "EMAIL_FROM", None):
        logger.debug("email_not_configured_skipping", email=email)
        return

    import boto3
    from jinja2 import Environment, FileSystemLoader
    import os

    templates_dir = os.path.join(os.path.dirname(__file__), "..", "templates", "email")
    env = Environment(loader=FileSystemLoader(templates_dir), autoescape=True)
    template = env.get_template("weekly_digest.html")
    html_body = template.render(
        full_name=full_name,
        org_name=org_name,
        summary=summary,
        activity=activity,
        period_start=activity.get("period_start", ""),
        platform_url=getattr(settings, "FRONTEND_URL", "https://app.scrplatform.com"),
    )

    ses = boto3.client(
        "ses",
        region_name=getattr(settings, "AWS_SES_REGION", settings.AWS_S3_REGION),
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )
    ses.send_email(
        Source=settings.EMAIL_FROM,
        Destination={"ToAddresses": [email]},
        Message={
            "Subject": {"Data": f"Your SCR Platform Weekly Digest — {org_name}"},
            "Body": {"Html": {"Data": html_body}},
        },
    )
    logger.info("digest_email_sent", email=email)
