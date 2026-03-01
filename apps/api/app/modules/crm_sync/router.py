"""CRM Sync — FastAPI router (8 endpoints)."""

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.modules.crm_sync.schemas import (
    CRMConnectionResponse,
    FieldMappingUpdate,
    SalesforceContactResponse,
    SalesforceSyncRequest,
    SalesforceSyncResponse,
    SyncLogResponse,
    TestConnectionResponse,
)
from app.modules.crm_sync.service import CRMSyncService
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()
router = APIRouter(prefix="/crm", tags=["CRM Sync"])


@router.get("/connect/{provider}")
async def get_oauth_url(
    provider: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return the OAuth2 authorization URL for the given CRM provider."""
    svc = CRMSyncService(db, current_user.org_id)
    try:
        url = await svc.get_oauth_url(provider)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return {"url": url}


@router.get("/callback/{provider}")
async def oauth_callback(
    provider: str,
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Handle OAuth2 callback from CRM provider.

    The `state` query parameter contains the org_id (set during /connect/{provider}).
    No auth header available here — this is the OAuth redirect from HubSpot.
    On success, redirects to the frontend settings page with ?crm=connected.
    """
    try:
        org_id = uuid.UUID(state)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid state parameter",
        )

    svc = CRMSyncService(db, org_id)
    try:
        conn = await svc.handle_oauth_callback(provider, code)
        await db.commit()
        logger.info("crm_oauth_callback_success", provider=provider, org_id=str(org_id), connection_id=str(conn.id))
    except Exception as e:
        await db.rollback()
        logger.error("crm_oauth_callback_error", provider=provider, error=str(e))
        frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
        return RedirectResponse(url=f"{frontend_url}/settings?crm=error", status_code=302)

    frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
    return RedirectResponse(url=f"{frontend_url}/settings?crm=connected", status_code=302)


@router.get("/connections", response_model=list[CRMConnectionResponse])
async def list_connections(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[CRMConnectionResponse]:
    """List all active CRM connections for the current organisation."""
    svc = CRMSyncService(db, current_user.org_id)
    connections = await svc.list_connections()
    return [CRMConnectionResponse.model_validate(c) for c in connections]


@router.put("/connections/{connection_id}/mappings", response_model=CRMConnectionResponse)
async def update_field_mappings(
    connection_id: uuid.UUID,
    body: FieldMappingUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CRMConnectionResponse:
    """Update field mappings and sync settings for a CRM connection."""
    svc = CRMSyncService(db, current_user.org_id)
    try:
        conn = await svc.update_field_mappings(
            connection_id,
            body.field_mappings,
            body.sync_frequency,
            body.sync_direction,
        )
        await db.commit()
        await db.refresh(conn)
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return CRMConnectionResponse.model_validate(conn)


@router.post("/connections/{connection_id}/sync")
async def trigger_sync(
    connection_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Manually trigger a CRM sync for the given connection."""
    svc = CRMSyncService(db, current_user.org_id)
    try:
        result = await svc.trigger_sync(connection_id)
        await db.commit()
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        await db.rollback()
        logger.error("crm_sync_trigger_error", connection_id=str(connection_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Sync failed",
        )
    return result


@router.get("/connections/{connection_id}/logs", response_model=list[SyncLogResponse])
async def get_sync_logs(
    connection_id: uuid.UUID,
    limit: int = Query(default=50, ge=1, le=500),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SyncLogResponse]:
    """Return recent sync log entries for a CRM connection."""
    svc = CRMSyncService(db, current_user.org_id)
    try:
        logs = await svc.get_sync_logs(connection_id, limit)
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return [SyncLogResponse.model_validate(log) for log in logs]


@router.delete("/connections/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect(
    connection_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft-disconnect (deactivate) a CRM connection."""
    svc = CRMSyncService(db, current_user.org_id)
    try:
        await svc.disconnect(connection_id)
        await db.commit()
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/connections/{connection_id}/test", response_model=TestConnectionResponse)
async def test_connection(
    connection_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TestConnectionResponse:
    """Verify that a CRM connection's credentials are still valid."""
    svc = CRMSyncService(db, current_user.org_id)
    try:
        result = await svc.test_connection(connection_id)
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return TestConnectionResponse(**result)


@router.post(
    "/salesforce/sync",
    response_model=SalesforceSyncResponse,
    summary="Sync SCR projects to Salesforce Opportunities",
)
async def salesforce_sync(
    body: SalesforceSyncRequest,
    connection_id: uuid.UUID = Query(..., description="Active Salesforce CRM connection ID"),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SalesforceSyncResponse:
    """Push the requested SCR projects to Salesforce as Opportunities.

    Requires an active Salesforce CRM connection ID passed as a query parameter.
    """
    svc = CRMSyncService(db, current_user.org_id)
    try:
        result = await svc.sync_salesforce(connection_id, body.project_ids)
        await db.commit()
    except (LookupError, ValueError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await db.rollback()
        logger.error("salesforce_sync_error", connection_id=str(connection_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Salesforce sync failed",
        )
    return SalesforceSyncResponse(**result)


@router.get(
    "/salesforce/contacts",
    response_model=list[SalesforceContactResponse],
    summary="List contacts pulled from Salesforce",
)
async def salesforce_contacts(
    connection_id: uuid.UUID = Query(..., description="Active Salesforce CRM connection ID"),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SalesforceContactResponse]:
    """Fetch and return Salesforce contacts via SOQL (SELECT Id, Name, Email FROM Contact)."""
    svc = CRMSyncService(db, current_user.org_id)
    try:
        contacts = await svc.pull_salesforce_contacts(connection_id)
        await db.commit()
    except (LookupError, ValueError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await db.rollback()
        logger.error("salesforce_contacts_error", connection_id=str(connection_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch Salesforce contacts",
        )
    return [SalesforceContactResponse(**c) for c in contacts]
