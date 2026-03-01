"""Custom Domain — 5 endpoints (E03)."""

import uuid
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.modules.custom_domain.schemas import (
    CustomDomainResponse,
    SetDomainRequest,
    VerifyDomainResponse,
)
from app.modules.custom_domain.service import CustomDomainService
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()
router = APIRouter(prefix="/custom-domain", tags=["Custom Domain"])


def _to_response(record, svc: CustomDomainService) -> CustomDomainResponse:
    return CustomDomainResponse(
        id=record.id,
        org_id=record.org_id,
        domain=record.domain,
        status=record.status,
        cname_target=record.cname_target,
        verification_token=record.verification_token,
        verified_at=record.verified_at,
        ssl_provisioned_at=record.ssl_provisioned_at,
        last_checked_at=record.last_checked_at,
        error_message=record.error_message,
        created_at=record.created_at,
        dns_instructions=svc._dns_instructions(record),
    )


@router.get("", response_model=CustomDomainResponse | None)
async def get_domain_status(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CustomDomainResponse | None:
    """Get the current custom domain configuration for this org."""
    svc = CustomDomainService(db, current_user.org_id)
    record = await svc.get_domain()
    if not record:
        return None
    return _to_response(record, svc)


@router.put("", response_model=CustomDomainResponse, status_code=status.HTTP_200_OK)
async def set_domain(
    body: SetDomainRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CustomDomainResponse:
    """Set or update the custom domain for this org. Resets verification status."""
    svc = CustomDomainService(db, current_user.org_id)
    try:
        record = await svc.set_domain(body.domain)
        await db.commit()
        await db.refresh(record)
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    logger.info("custom_domain.set", org_id=str(current_user.org_id), domain=body.domain)
    return _to_response(record, svc)


@router.post("/verify", response_model=VerifyDomainResponse)
async def verify_domain(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VerifyDomainResponse:
    """Trigger DNS verification for the configured domain."""
    svc = CustomDomainService(db, current_user.org_id)
    record = await svc.get_domain()
    if not record:
        raise HTTPException(status_code=404, detail="No domain configured")
    success, message = await svc.verify_domain()
    await db.commit()
    # Refresh record to get updated status after commit
    await db.refresh(record)
    return VerifyDomainResponse(
        success=success,
        status=record.status,
        message=message,
        verified_at=record.verified_at,
    )


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_domain(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Remove the custom domain configuration and revert to scr.io."""
    svc = CustomDomainService(db, current_user.org_id)
    deleted = await svc.delete_domain()
    if not deleted:
        raise HTTPException(status_code=404, detail="No domain configured")
    await db.commit()
    logger.info("custom_domain.deleted", org_id=str(current_user.org_id))


@router.post("/admin/force-verify/{org_id}", response_model=CustomDomainResponse)
async def admin_force_verify(
    org_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CustomDomainResponse:
    """Admin: manually mark a domain as verified (for testing/support)."""
    from app.models.core import Organization
    from app.models.enums import OrgType

    result = await db.get(Organization, current_user.org_id)
    if not result or result.type != OrgType.ADMIN:
        raise HTTPException(status_code=403, detail="Admin only")

    svc = CustomDomainService(db, org_id)
    record = await svc.get_domain()
    if not record:
        raise HTTPException(status_code=404, detail="Domain not found for org")
    record.status = "verified"
    record.verified_at = datetime.now(timezone.utc)
    record.ssl_provisioned_at = datetime.now(timezone.utc)
    record.error_message = None
    await db.commit()
    await db.refresh(record)
    return _to_response(record, svc)
