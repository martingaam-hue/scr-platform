"""Tax Credit Orchestrator API router."""

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_permission
from app.core.database import get_db
from app.modules.tax_credits import service
from app.modules.tax_credits.schemas import (
    IdentificationResponse,
    OptimizationRequest,
    OptimizationResult,
    TaxCreditInventoryResponse,
    TaxCreditSummaryResponse,
    TransferDocRequest,
    TransferDocResponse,
)
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()

router = APIRouter(prefix="/tax-credits", tags=["tax-credits"])


@router.get(
    "/inventory/{portfolio_id}",
    response_model=TaxCreditInventoryResponse,
)
async def get_inventory(
    portfolio_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "portfolio")),
    db: AsyncSession = Depends(get_db),
):
    """Portfolio-wide tax credit inventory with totals by credit type."""
    try:
        return await service.get_inventory(db, portfolio_id, current_user.org_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post(
    "/identify/{project_id}",
    response_model=IdentificationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def identify_credits(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("run_analysis", "analysis")),
    db: AsyncSession = Depends(get_db),
):
    """AI-powered identification of applicable tax credits for a project."""
    try:
        result = await service.identify_credits(db, project_id, current_user.org_id)
        await db.commit()
        return result
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/model", response_model=OptimizationResult)
async def run_optimization(
    body: OptimizationRequest,
    current_user: CurrentUser = Depends(require_permission("view", "portfolio")),
    db: AsyncSession = Depends(get_db),
):
    """Deterministic optimization: claim vs transfer, timing recommendations."""
    try:
        return await service.model_optimization(db, body, current_user.org_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post(
    "/transfer-docs",
    response_model=TransferDocResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_transfer_docs(
    body: TransferDocRequest,
    current_user: CurrentUser = Depends(require_permission("create", "report")),
    db: AsyncSession = Depends(get_db),
):
    """Queue generation of transfer election documentation."""
    try:
        report = await service.generate_transfer_docs(db, body, current_user.org_id)
        await db.commit()
        await db.refresh(report)

        from app.modules.tax_credits.tasks import generate_transfer_doc_task
        generate_transfer_doc_task.delay(str(report.id))

        return TransferDocResponse(
            report_id=report.id,
            status=report.status.value,
            message="Transfer documentation queued for generation.",
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/summary/{entity_id}", response_model=TaxCreditSummaryResponse)
async def get_summary(
    entity_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "portfolio")),
    db: AsyncSession = Depends(get_db),
):
    """Tax credit summary for a project or portfolio entity."""
    try:
        return await service.get_summary(db, entity_id, current_user.org_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
