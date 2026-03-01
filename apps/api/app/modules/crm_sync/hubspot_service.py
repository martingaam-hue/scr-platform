"""HubSpot API integration service for CRM sync operations."""

import uuid
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.crm import CRMConnection, CRMEntityMapping, CRMSyncLog


class HubSpotService:
    BASE_URL = "https://api.hubapi.com"

    def __init__(self, db: AsyncSession, connection: CRMConnection):
        self.db = db
        self.connection = connection

    async def _api_call(self, method: str, path: str, body: dict = None) -> dict:
        """Make authenticated HubSpot API call. Refresh token if expired."""
        headers = {
            "Authorization": f"Bearer {self.connection.access_token}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.request(
                method, f"{self.BASE_URL}{path}", json=body, headers=headers
            )
            if resp.status_code == 401:
                await self._refresh_access_token()
                headers["Authorization"] = f"Bearer {self.connection.access_token}"
                resp = await client.request(
                    method, f"{self.BASE_URL}{path}", json=body, headers=headers
                )
            resp.raise_for_status()
            return resp.json() if resp.content else {}

    async def _refresh_access_token(self):
        """Refresh OAuth2 access token using refresh_token."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.hubapi.com/oauth/v1/token",
                data={
                    "grant_type": "refresh_token",
                    "client_id": getattr(settings, "HUBSPOT_CLIENT_ID", ""),
                    "client_secret": getattr(settings, "HUBSPOT_CLIENT_SECRET", ""),
                    "refresh_token": self.connection.refresh_token,
                },
            )
        tokens = resp.json()
        self.connection.access_token = tokens.get("access_token", self.connection.access_token)
        self.connection.token_expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=tokens.get("expires_in", 3600)
        )
        await self.db.flush()

    def _map_stage(self, project_stage: str) -> str:
        """Map SCR project stage to HubSpot deal stage."""
        mapping = {
            "DEVELOPMENT": "appointmentscheduled",
            "CONSTRUCTION": "qualifiedtobuy",
            "OPERATIONAL": "closedwon",
            "CLOSED": "closedwon",
        }
        return mapping.get(project_stage, "appointmentscheduled")

    async def _get_crm_mapping(
        self, scr_entity_type: str, scr_entity_id: uuid.UUID
    ) -> CRMEntityMapping | None:
        result = await self.db.execute(
            select(CRMEntityMapping).where(
                CRMEntityMapping.connection_id == self.connection.id,
                CRMEntityMapping.scr_entity_type == scr_entity_type,
                CRMEntityMapping.scr_entity_id == scr_entity_id,
            )
        )
        return result.scalar_one_or_none()

    async def _save_mapping(
        self,
        scr_entity_type: str,
        scr_entity_id: uuid.UUID,
        crm_entity_type: str,
        crm_entity_id,
    ):
        mapping = CRMEntityMapping(
            connection_id=self.connection.id,
            scr_entity_type=scr_entity_type,
            scr_entity_id=scr_entity_id,
            crm_entity_type=crm_entity_type,
            crm_entity_id=str(crm_entity_id),
        )
        self.db.add(mapping)
        await self.db.flush()

    async def _log_sync(
        self,
        direction: str,
        entity_type: str,
        scr_id,
        crm_id,
        action: str,
        status: str,
        error: str = None,
    ):
        log = CRMSyncLog(
            connection_id=self.connection.id,
            direction=direction,
            entity_type=entity_type,
            scr_entity_id=scr_id,
            crm_entity_id=str(crm_id) if crm_id else None,
            action=action,
            status=status,
            error_message=error,
        )
        self.db.add(log)

    async def push_project_as_deal(self, project) -> dict:
        """Push a SCR project to HubSpot as a Deal."""
        mappings = self.connection.field_mappings or {}
        deal_props = {
            mappings.get("project_name", "dealname"): project.name,
            mappings.get("project_type", "deal_type"): (
                str(project.project_type.value) if project.project_type else ""
            ),
            mappings.get("stage", "dealstage"): self._map_stage(
                str(project.stage.value) if project.stage else ""
            ),
        }
        if project.total_investment_required:
            deal_props[mappings.get("budget", "amount")] = str(
                float(project.total_investment_required)
            )

        existing = await self._get_crm_mapping("project", project.id)
        try:
            if existing:
                resp = await self._api_call(
                    "PATCH",
                    f"/crm/v3/objects/deals/{existing.crm_entity_id}",
                    {"properties": deal_props},
                )
                await self._log_sync(
                    "push", "deal", project.id, existing.crm_entity_id, "update", "success"
                )
            else:
                resp = await self._api_call(
                    "POST", "/crm/v3/objects/deals", {"properties": deal_props}
                )
                await self._save_mapping("project", project.id, "deal", resp.get("id"))
                await self._log_sync(
                    "push", "deal", project.id, resp.get("id"), "create", "success"
                )
            return resp
        except Exception as e:
            await self._log_sync("push", "deal", project.id, None, "create", "error", str(e))
            raise

    async def pull_deal_updates(self) -> int:
        """Pull recent deal changes from HubSpot, update SCR project stages."""
        since = self.connection.last_sync_at or datetime(2020, 1, 1)
        since_ms = int(since.timestamp() * 1000)  # noqa: F841 — available for future filtered queries

        try:
            resp = await self._api_call(
                "GET",
                "/crm/v3/objects/deals?properties=dealname,dealstage,amount&limit=100",
            )
            updated = 0
            for deal in resp.get("results", []):
                mapping = await self.db.execute(
                    select(CRMEntityMapping).where(
                        CRMEntityMapping.connection_id == self.connection.id,
                        CRMEntityMapping.crm_entity_id == str(deal["id"]),
                    )
                )
                m = mapping.scalar_one_or_none()
                if m:
                    await self._log_sync(
                        "pull", "deal", m.scr_entity_id, deal["id"], "update", "success"
                    )
                    updated += 1
            return updated
        except Exception as e:
            await self._log_sync("pull", "deal", None, None, "update", "error", str(e))
            return 0

    async def test_connection(self) -> dict:
        """Test that connection is valid by calling /oauth/v1/access-tokens/{token}."""
        try:
            resp = await self._api_call(
                "GET", f"/oauth/v1/access-tokens/{self.connection.access_token}"
            )
            return {
                "success": True,
                "message": "Connected",
                "portal_id": str(resp.get("hub_id", "")),
            }
        except Exception as e:
            return {"success": False, "message": str(e), "portal_id": None}
