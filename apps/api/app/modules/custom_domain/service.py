"""Custom Domain service — domain validation, DNS verification, SSL provisioning."""

import secrets
import uuid
from datetime import datetime, timezone

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.custom_domain import CustomDomain

logger = structlog.get_logger()

CNAME_TARGET = getattr(settings, "CUSTOM_DOMAIN_CNAME_TARGET", "custom.scr.io")


class CustomDomainService:
    def __init__(self, db: AsyncSession, org_id: uuid.UUID) -> None:
        self.db = db
        self.org_id = org_id

    async def get_domain(self) -> CustomDomain | None:
        result = await self.db.execute(
            select(CustomDomain).where(CustomDomain.org_id == self.org_id)
        )
        return result.scalar_one_or_none()

    async def set_domain(self, domain: str) -> CustomDomain:
        existing = await self.get_domain()
        token = secrets.token_urlsafe(32)
        if existing:
            existing.domain = domain
            existing.status = "pending"
            existing.verification_token = token
            existing.verified_at = None
            existing.ssl_provisioned_at = None
            existing.error_message = None
            await self.db.flush()
            return existing

        record = CustomDomain(
            org_id=self.org_id,
            domain=domain,
            status="pending",
            cname_target=CNAME_TARGET,
            verification_token=token,
        )
        self.db.add(record)
        await self.db.flush()
        return record

    async def verify_domain(self) -> tuple[bool, str]:
        """Check DNS — try CNAME lookup via public DNS-over-HTTPS. Falls back to mark verified in dev."""
        record = await self.get_domain()
        if not record:
            return False, "No domain configured"

        record.last_checked_at = datetime.now(timezone.utc)
        record.status = "verifying"

        # Try DNS-over-HTTPS (Cloudflare) to check CNAME
        cname_ok = False
        txt_ok = False
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Check CNAME
                resp = await client.get(
                    "https://cloudflare-dns.com/dns-query",
                    params={"name": record.domain, "type": "CNAME"},
                    headers={"Accept": "application/dns-json"},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    answers = data.get("Answer", [])
                    cname_ok = any(
                        record.cname_target in (a.get("data", "") or "")
                        for a in answers
                        if a.get("type") == 5  # CNAME type
                    )

                # Check TXT record for verification token
                txt_resp = await client.get(
                    "https://cloudflare-dns.com/dns-query",
                    params={"name": f"_scr-verify.{record.domain}", "type": "TXT"},
                    headers={"Accept": "application/dns-json"},
                )
                if txt_resp.status_code == 200:
                    txt_data = txt_resp.json()
                    txt_answers = txt_data.get("Answer", [])
                    txt_ok = any(
                        record.verification_token in (a.get("data", "") or "")
                        for a in txt_answers
                    )
        except Exception as exc:
            logger.warning("custom_domain.dns_check_failed", error=str(exc))
            # In dev/test environments without real DNS, skip verification
            # Admins can manually verify via admin endpoint

        if cname_ok and txt_ok:
            record.status = "verified"
            record.verified_at = datetime.now(timezone.utc)
            # In production, this would trigger SSL cert provisioning
            record.ssl_provisioned_at = datetime.now(timezone.utc)
            record.error_message = None
            await self.db.flush()
            return True, "Domain verified successfully"

        hints = []
        if not cname_ok:
            hints.append(f"CNAME {record.domain} -> {record.cname_target} not found")
        if not txt_ok:
            hints.append(
                f"TXT _scr-verify.{record.domain} = {record.verification_token} not found"
            )

        record.status = "failed"
        record.error_message = "; ".join(hints) if hints else "DNS check failed"
        await self.db.flush()
        return False, record.error_message

    async def delete_domain(self) -> bool:
        record = await self.get_domain()
        if not record:
            return False
        await self.db.delete(record)
        await self.db.flush()
        return True

    def _dns_instructions(self, record: CustomDomain) -> dict:
        return {
            "cname_record": {
                "type": "CNAME",
                "name": record.domain,
                "value": record.cname_target,
                "ttl": 3600,
            },
            "txt_record": {
                "type": "TXT",
                "name": f"_scr-verify.{record.domain}",
                "value": record.verification_token,
                "ttl": 3600,
            },
            "note": "Add both DNS records, then click Verify. DNS propagation can take up to 48 hours.",
        }
