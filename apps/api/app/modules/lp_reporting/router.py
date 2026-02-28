"""LP Reporting API router."""

from __future__ import annotations

import math
import uuid
from datetime import datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_permission
from app.core.database import get_db
from app.modules.lp_reporting import service
from app.modules.lp_reporting.schemas import (
    ApproveReportResponse,
    CreateLPReportRequest,
    GeneratePDFResponse,
    LPReportListResponse,
    LPReportResponse,
    UpdateLPReportRequest,
)
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()

router = APIRouter(prefix="/lp-reports", tags=["lp-reporting"])


# ── Helpers ───────────────────────────────────────────────────────────────────


def _report_to_response(report, download_url: str | None = None) -> LPReportResponse:
    return LPReportResponse(
        id=report.id,
        org_id=report.org_id,
        portfolio_id=report.portfolio_id,
        report_period=report.report_period,
        period_start=report.period_start,
        period_end=report.period_end,
        status=report.status,
        approved_by=report.approved_by,
        approved_at=report.approved_at,
        gross_irr=report.gross_irr,
        net_irr=report.net_irr,
        tvpi=report.tvpi,
        dpi=report.dpi,
        rvpi=report.rvpi,
        moic=report.moic,
        total_committed=report.total_committed,
        total_invested=report.total_invested,
        total_returned=report.total_returned,
        total_nav=report.total_nav,
        narrative=report.narrative,
        investments_data=report.investments_data,
        pdf_s3_key=report.pdf_s3_key,
        generated_at=report.generated_at,
        download_url=download_url,
        created_at=report.created_at,
        updated_at=report.updated_at,
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post("", response_model=LPReportResponse, status_code=status.HTTP_201_CREATED)
async def create_report(
    body: CreateLPReportRequest,
    current_user: CurrentUser = Depends(require_permission("create", "report")),
    db: AsyncSession = Depends(get_db),
):
    """
    Create an LP report.

    This endpoint:
    1. Calculates all financial metrics deterministically (Python, never LLM).
    2. Calls the AI Gateway to generate narrative sections.
    3. Persists and returns the draft report.
    """
    try:
        report = await service.create_report(
            db,
            org_id=current_user.org_id,
            portfolio_id=body.portfolio_id,
            report_period=body.report_period,
            period_start=body.period_start,
            period_end=body.period_end,
            cash_flows=body.cash_flows,
            investments_data=body.investments_data,
            total_committed=body.total_committed,
            total_invested=body.total_invested,
            total_returned=body.total_returned,
            total_nav=body.total_nav,
        )
        await db.commit()
        await db.refresh(report)
    except Exception as exc:
        logger.error("lp_report.create_failed", error=str(exc))
        raise HTTPException(status_code=500, detail=f"Failed to create report: {exc}") from exc

    logger.info(
        "lp_report.created",
        report_id=str(report.id),
        org_id=str(current_user.org_id),
        period=report.report_period,
    )
    return _report_to_response(report)


@router.get("", response_model=LPReportListResponse)
async def list_reports(
    portfolio_id: uuid.UUID | None = None,
    report_status: str | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: CurrentUser = Depends(require_permission("view", "report")),
    db: AsyncSession = Depends(get_db),
):
    """List LP reports for the current organisation."""
    reports, total = await service.list_reports(
        db,
        org_id=current_user.org_id,
        portfolio_id=portfolio_id,
        status=report_status,
        page=page,
        page_size=page_size,
    )
    total_pages = math.ceil(total / page_size) if total > 0 else 0
    return LPReportListResponse(
        items=[_report_to_response(r) for r in reports],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{report_id}", response_model=LPReportResponse)
async def get_report(
    report_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "report")),
    db: AsyncSession = Depends(get_db),
):
    """Get a single LP report by ID."""
    report = await service.get_report(db, report_id, current_user.org_id)
    if not report:
        raise HTTPException(status_code=404, detail="LP report not found")

    download_url = None
    if report.pdf_s3_key:
        download_url = await service.get_download_url(db, report_id, current_user.org_id)

    return _report_to_response(report, download_url)


@router.put("/{report_id}", response_model=LPReportResponse)
async def update_report(
    report_id: uuid.UUID,
    body: UpdateLPReportRequest,
    current_user: CurrentUser = Depends(require_permission("create", "report")),
    db: AsyncSession = Depends(get_db),
):
    """Update narrative sections or metadata of a draft LP report."""
    narrative_dict = body.narrative.model_dump() if body.narrative else None
    investments = (
        [inv.model_dump() if hasattr(inv, "model_dump") else inv for inv in body.investments_data]
        if body.investments_data is not None
        else None
    )

    try:
        report = await service.update_report(
            db,
            report_id=report_id,
            org_id=current_user.org_id,
            narrative=narrative_dict,
            investments_data=investments,
            report_period=body.report_period,
            period_start=body.period_start,
            period_end=body.period_end,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not report:
        raise HTTPException(status_code=404, detail="LP report not found")

    await db.commit()
    await db.refresh(report)
    return _report_to_response(report)


@router.post("/{report_id}/approve", response_model=ApproveReportResponse)
async def approve_report(
    report_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("create", "report")),
    db: AsyncSession = Depends(get_db),
):
    """Approve an LP report (transitions to 'approved' status). Manager+ only."""
    try:
        report = await service.approve_report(
            db,
            report_id=report_id,
            org_id=current_user.org_id,
            approver_id=current_user.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not report:
        raise HTTPException(status_code=404, detail="LP report not found")

    await db.commit()
    await db.refresh(report)

    logger.info(
        "lp_report.approved",
        report_id=str(report_id),
        approver_id=str(current_user.user_id),
    )

    return ApproveReportResponse(
        id=report.id,
        status=report.status,
        approved_by=report.approved_by,
        approved_at=report.approved_at or datetime.utcnow(),
    )


@router.post("/{report_id}/generate-pdf", response_model=GeneratePDFResponse)
async def generate_pdf(
    report_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("create", "report")),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate the HTML report document and upload to S3.

    Returns a pre-signed URL. The frontend can open this URL and use
    browser print to export as PDF.
    """
    try:
        s3_key, download_url = await service.generate_html_report(
            db, report_id, current_user.org_id
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("lp_report.generate_pdf_failed", report_id=str(report_id), error=str(exc))
        raise HTTPException(
            status_code=500, detail=f"Failed to generate report document: {exc}"
        ) from exc

    await db.commit()

    # Fetch updated report for generated_at timestamp
    report = await service.get_report(db, report_id, current_user.org_id)

    logger.info("lp_report.pdf_generated", report_id=str(report_id))

    return GeneratePDFResponse(
        id=report_id,
        pdf_s3_key=s3_key,
        download_url=download_url,
        generated_at=report.generated_at if report else datetime.utcnow(),
    )


@router.get("/{report_id}/download")
async def download_report(
    report_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "report")),
    db: AsyncSession = Depends(get_db),
):
    """Redirect to the pre-signed S3 URL for the generated report document."""
    download_url = await service.get_download_url(db, report_id, current_user.org_id)
    if not download_url:
        raise HTTPException(
            status_code=404,
            detail="Report document not yet generated. Call /generate-pdf first.",
        )
    return RedirectResponse(url=download_url)
