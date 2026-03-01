"""Salesforce CRM integration — OAuth, SOQL queries, bidirectional sync."""

import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.crm import CRMConnection, CRMEntityMapping, CRMSyncLog

SALESFORCE_AUTH_URL = "https://login.salesforce.com/services/oauth2/authorize"
SALESFORCE_TOKEN_URL = "https://login.salesforce.com/services/oauth2/token"
SALESFORCE_API_VERSION = "v59.0"


class SalesforceService:
    def __init__(self, db: AsyncSession, connection: CRMConnection):
        self.db = db
        self.conn = connection

    # ── OAuth ──────────────────────────────────────────────────────────────────

    async def get_oauth_url(self, org_id: uuid.UUID) -> str:
        """Return Salesforce OAuth2 authorization URL."""
        client_id = getattr(settings, "SALESFORCE_CLIENT_ID", "")
        redirect_uri = getattr(settings, "SALESFORCE_REDIRECT_URI", "")
        params = urlencode(
            {
                "response_type": "code",
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "scope": "api refresh_token offline_access",
                "state": str(org_id),
            }
        )
        return f"{SALESFORCE_AUTH_URL}?{params}"

    async def exchange_code(self, code: str) -> dict:
        """Exchange OAuth2 authorization code for tokens.

        Returns a dict with keys: access_token, instance_url, refresh_token.
        """
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                SALESFORCE_TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "client_id": getattr(settings, "SALESFORCE_CLIENT_ID", ""),
                    "client_secret": getattr(settings, "SALESFORCE_CLIENT_SECRET", ""),
                    "redirect_uri": getattr(settings, "SALESFORCE_REDIRECT_URI", ""),
                    "code": code,
                },
            )
        resp.raise_for_status()
        return resp.json()

    async def refresh_access_token(self) -> str:
        """Use the stored refresh_token to obtain a new access_token.

        Updates conn.access_token and conn.token_expires_at in place and
        flushes the session.  Returns the new access_token.
        """
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                SALESFORCE_TOKEN_URL,
                data={
                    "grant_type": "refresh_token",
                    "client_id": getattr(settings, "SALESFORCE_CLIENT_ID", ""),
                    "client_secret": getattr(settings, "SALESFORCE_CLIENT_SECRET", ""),
                    "refresh_token": self.conn.refresh_token,
                },
            )
        resp.raise_for_status()
        tokens = resp.json()
        self.conn.access_token = tokens.get("access_token", self.conn.access_token)
        # Salesforce does not always return expires_in; default 2 h
        self.conn.token_expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=tokens.get("expires_in", 7200)
        )
        await self.db.flush()
        return self.conn.access_token

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _base_url(self) -> str:
        return (self.conn.instance_url or "").rstrip("/")

    async def _api_call(self, method: str, path: str, body: dict | None = None) -> dict:
        """Make an authenticated Salesforce REST API call.

        Automatically retries once with a refreshed token on 401.
        """
        headers = {
            "Authorization": f"Bearer {self.conn.access_token}",
            "Content-Type": "application/json",
        }
        url = f"{self._base_url()}{path}"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.request(method, url, json=body, headers=headers)
            if resp.status_code == 401:
                await self.refresh_access_token()
                headers["Authorization"] = f"Bearer {self.conn.access_token}"
                resp = await client.request(method, url, json=body, headers=headers)
            resp.raise_for_status()
            return resp.json() if resp.content else {}

    def _map_stage(self, project_stage: str) -> str:
        """Map SCR project stage to Salesforce Opportunity stage name."""
        mapping = {
            "DEVELOPMENT": "Prospecting",
            "CONSTRUCTION": "Value Proposition",
            "OPERATIONAL": "Closed Won",
            "CLOSED": "Closed Won",
        }
        return mapping.get(project_stage, "Prospecting")

    async def _get_crm_mapping(
        self, scr_entity_type: str, scr_entity_id: uuid.UUID
    ) -> CRMEntityMapping | None:
        result = await self.db.execute(
            select(CRMEntityMapping).where(
                CRMEntityMapping.connection_id == self.conn.id,
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
        crm_entity_id: str,
    ) -> None:
        mapping = CRMEntityMapping(
            connection_id=self.conn.id,
            scr_entity_type=scr_entity_type,
            scr_entity_id=scr_entity_id,
            crm_entity_type=crm_entity_type,
            crm_entity_id=crm_entity_id,
        )
        self.db.add(mapping)
        await self.db.flush()

    async def _log_sync(
        self,
        direction: str,
        entity_type: str,
        scr_id: uuid.UUID | None,
        crm_id: str | None,
        action: str,
        status: str,
        error: str | None = None,
    ) -> None:
        log = CRMSyncLog(
            connection_id=self.conn.id,
            direction=direction,
            entity_type=entity_type,
            scr_entity_id=scr_id,
            crm_entity_id=crm_id,
            action=action,
            status=status,
            error_message=error,
        )
        self.db.add(log)

    # ── Sync operations ────────────────────────────────────────────────────────

    async def sync_projects_to_deals(
        self, project_ids: list[uuid.UUID]
    ) -> dict:
        """Push SCR projects to Salesforce Opportunities.

        For each project, creates a new Opportunity or patches the existing
        one when an entity mapping already exists.

        Returns {"synced": N, "failed": M}.
        """
        from app.models.projects import Project  # local import avoids circular deps

        projects = (
            await self.db.execute(
                select(Project).where(
                    Project.id.in_(project_ids),
                    Project.org_id == self.conn.org_id,
                    Project.is_deleted.is_(False),
                )
            )
        ).scalars().all()

        field_mappings = self.conn.field_mappings or {}
        synced = 0
        failed = 0

        for project in projects:
            opp_data = {
                field_mappings.get("project_name", "Name"): project.name,
                field_mappings.get("stage", "StageName"): self._map_stage(
                    str(project.stage.value) if project.stage else ""
                ),
                # Salesforce requires a CloseDate; default 90 days out
                field_mappings.get("close_date", "CloseDate"): (
                    datetime.now(timezone.utc) + timedelta(days=90)
                ).strftime("%Y-%m-%d"),
            }
            if project.total_investment_required:
                opp_data[field_mappings.get("budget", "Amount")] = float(
                    project.total_investment_required
                )

            existing = await self._get_crm_mapping("project", project.id)
            try:
                if existing:
                    await self._api_call(
                        "PATCH",
                        f"/services/data/{SALESFORCE_API_VERSION}/sobjects/Opportunity/{existing.crm_entity_id}",
                        opp_data,
                    )
                    await self._log_sync(
                        "push", "opportunity", project.id,
                        existing.crm_entity_id, "update", "success",
                    )
                else:
                    resp = await self._api_call(
                        "POST",
                        f"/services/data/{SALESFORCE_API_VERSION}/sobjects/Opportunity/",
                        opp_data,
                    )
                    sf_id = resp.get("id", "")
                    await self._save_mapping("project", project.id, "opportunity", sf_id)
                    await self._log_sync(
                        "push", "opportunity", project.id, sf_id, "create", "success"
                    )
                synced += 1
            except Exception as exc:
                await self._log_sync(
                    "push", "opportunity", project.id, None, "create", "error", str(exc)
                )
                failed += 1

        return {"synced": synced, "failed": failed}

    async def pull_contacts(self) -> list[dict]:
        """Fetch contacts from Salesforce via SOQL query.

        Returns a list of contact dicts with keys: id, name, email.
        """
        soql = "SELECT+Id,Name,Email+FROM+Contact+LIMIT+200"
        try:
            resp = await self._api_call(
                "GET",
                f"/services/data/{SALESFORCE_API_VERSION}/query?q={soql}",
            )
            records = resp.get("records", [])
            contacts = [
                {
                    "id": r.get("Id"),
                    "name": r.get("Name"),
                    "email": r.get("Email"),
                }
                for r in records
            ]
            await self._log_sync(
                "pull", "contact", None, None, "list", "success"
            )
            return contacts
        except Exception as exc:
            await self._log_sync(
                "pull", "contact", None, None, "list", "error", str(exc)
            )
            return []

    async def test_connection(self) -> dict:
        """Verify connection by calling the Salesforce identity endpoint."""
        try:
            resp = await self._api_call(
                "GET",
                f"/services/data/{SALESFORCE_API_VERSION}/limits",
            )
            return {
                "success": True,
                "message": "Connected",
                "instance_url": self.conn.instance_url,
            }
        except Exception as exc:
            return {"success": False, "message": str(exc), "instance_url": None}
