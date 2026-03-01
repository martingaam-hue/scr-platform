"""CRM Sync service — business logic for managing CRM connections and sync operations."""

import uuid
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.crm import CRMConnection, CRMSyncLog


class CRMSyncService:
    def __init__(self, db: AsyncSession, org_id: uuid.UUID):
        self.db = db
        self.org_id = org_id

    async def get_oauth_url(self, provider: str) -> str:
        """Return OAuth2 authorization URL."""
        if provider == "hubspot":
            client_id = getattr(settings, "HUBSPOT_CLIENT_ID", "")
            redirect_uri = getattr(
                settings,
                "HUBSPOT_REDIRECT_URI",
                f"{settings.API_URL}/crm/callback/hubspot",
            )
            return (
                f"https://app.hubspot.com/oauth/authorize"
                f"?client_id={client_id}&redirect_uri={redirect_uri}"
                f"&scope=crm.objects.deals.read+crm.objects.deals.write"
                f"&state={str(self.org_id)}"
            )
        elif provider == "salesforce":
            from app.modules.crm_sync.salesforce_service import SalesforceService

            # SalesforceService.get_oauth_url is a standalone helper; we build a
            # temporary stub connection so we can reuse the class method.
            stub_conn = type("_Stub", (), {"instance_url": None, "org_id": self.org_id})()
            svc = SalesforceService(self.db, stub_conn)  # type: ignore[arg-type]
            return await svc.get_oauth_url(self.org_id)
        raise ValueError(f"Unsupported provider: {provider}")

    async def handle_oauth_callback(self, provider: str, code: str) -> CRMConnection:
        """Exchange OAuth2 code for tokens and create CRMConnection."""
        if provider == "hubspot":
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "https://api.hubapi.com/oauth/v1/token",
                    data={
                        "grant_type": "authorization_code",
                        "client_id": getattr(settings, "HUBSPOT_CLIENT_ID", ""),
                        "client_secret": getattr(settings, "HUBSPOT_CLIENT_SECRET", ""),
                        "redirect_uri": getattr(settings, "HUBSPOT_REDIRECT_URI", ""),
                        "code": code,
                    },
                )
            tokens = resp.json()
            conn = CRMConnection(
                org_id=self.org_id,
                provider=provider,
                access_token=tokens.get("access_token", ""),
                refresh_token=tokens.get("refresh_token"),
                token_expires_at=datetime.now(timezone.utc)
                + timedelta(seconds=tokens.get("expires_in", 3600)),
                portal_id=str(tokens.get("hub_id", "")),
            )
            self.db.add(conn)
            await self.db.flush()
            await self.db.refresh(conn)
            return conn
        elif provider == "salesforce":
            from app.modules.crm_sync.salesforce_service import SalesforceService

            # Stub connection used only to call exchange_code (no DB access needed)
            stub_conn = type("_Stub", (), {
                "instance_url": None,
                "org_id": self.org_id,
                "access_token": "",
                "refresh_token": None,
            })()
            svc = SalesforceService(self.db, stub_conn)  # type: ignore[arg-type]
            tokens = await svc.exchange_code(code)
            conn = CRMConnection(
                org_id=self.org_id,
                provider=provider,
                access_token=tokens.get("access_token", ""),
                refresh_token=tokens.get("refresh_token"),
                token_expires_at=datetime.now(timezone.utc)
                + timedelta(seconds=tokens.get("expires_in", 7200)),
                instance_url=tokens.get("instance_url"),
            )
            self.db.add(conn)
            await self.db.flush()
            await self.db.refresh(conn)
            return conn
        raise ValueError(f"Unsupported provider: {provider}")

    async def list_connections(self) -> list[CRMConnection]:
        result = await self.db.execute(
            select(CRMConnection).where(
                CRMConnection.org_id == self.org_id,
                CRMConnection.is_active.is_(True),
            )
        )
        return list(result.scalars().all())

    async def update_field_mappings(
        self,
        connection_id: uuid.UUID,
        field_mappings: dict,
        sync_frequency: str = None,
        sync_direction: str = None,
    ) -> CRMConnection:
        conn = await self._get_conn(connection_id)
        conn.field_mappings = field_mappings
        if sync_frequency:
            conn.sync_frequency = sync_frequency
        if sync_direction:
            conn.sync_direction = sync_direction
        await self.db.flush()
        return conn

    async def trigger_sync(self, connection_id: uuid.UUID) -> dict:
        """Manually trigger sync for a connection."""
        conn = await self._get_conn(connection_id)
        from app.models.projects import Project
        from app.modules.crm_sync.hubspot_service import HubSpotService

        svc = HubSpotService(self.db, conn)
        projects = (
            await self.db.execute(
                select(Project)
                .where(
                    Project.org_id == self.org_id,
                    Project.is_deleted.is_(False),
                )
                .limit(50)
            )
        ).scalars().all()

        pushed = 0
        for p in projects:
            try:
                await svc.push_project_as_deal(p)
                pushed += 1
            except Exception:
                pass

        pulled = await svc.pull_deal_updates()
        conn.last_sync_at = datetime.now(timezone.utc)
        await self.db.flush()
        return {"pushed": pushed, "pulled": pulled}

    async def get_sync_logs(self, connection_id: uuid.UUID, limit: int = 50) -> list[CRMSyncLog]:
        result = await self.db.execute(
            select(CRMSyncLog)
            .join(CRMConnection, CRMConnection.id == CRMSyncLog.connection_id)
            .where(
                CRMConnection.org_id == self.org_id,
                CRMSyncLog.connection_id == connection_id,
            )
            .order_by(CRMSyncLog.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def disconnect(self, connection_id: uuid.UUID) -> None:
        conn = await self._get_conn(connection_id)
        conn.is_active = False
        await self.db.flush()

    async def test_connection(self, connection_id: uuid.UUID) -> dict:
        conn = await self._get_conn(connection_id)
        from app.modules.crm_sync.hubspot_service import HubSpotService

        svc = HubSpotService(self.db, conn)
        return await svc.test_connection()

    async def sync_salesforce(
        self,
        connection_id: uuid.UUID,
        project_ids: list[uuid.UUID],
    ) -> dict:
        """Trigger Salesforce deal sync for the specified projects.

        Returns {"synced": N, "failed": M}.
        """
        conn = await self._get_conn(connection_id)
        if conn.provider != "salesforce":
            raise ValueError("Connection is not a Salesforce connection")
        from app.modules.crm_sync.salesforce_service import SalesforceService

        svc = SalesforceService(self.db, conn)
        result = await svc.sync_projects_to_deals(project_ids)
        conn.last_sync_at = datetime.now(timezone.utc)
        await self.db.flush()
        return result

    async def pull_salesforce_contacts(self, connection_id: uuid.UUID) -> list[dict]:
        """Pull contacts from the Salesforce connection."""
        conn = await self._get_conn(connection_id)
        if conn.provider != "salesforce":
            raise ValueError("Connection is not a Salesforce connection")
        from app.modules.crm_sync.salesforce_service import SalesforceService

        svc = SalesforceService(self.db, conn)
        return await svc.pull_contacts()

    async def _get_conn(self, connection_id: uuid.UUID) -> CRMConnection:
        result = await self.db.execute(
            select(CRMConnection).where(
                CRMConnection.id == connection_id,
                CRMConnection.org_id == self.org_id,
            )
        )
        conn = result.scalar_one_or_none()
        if not conn:
            raise LookupError(f"CRM connection {connection_id} not found")
        return conn
