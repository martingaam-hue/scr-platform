"""Portfolio API router: CRUD, holdings, metrics, cash flows, allocation."""

import uuid
from decimal import Decimal

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_permission
from app.core.database import get_db, get_readonly_session
from app.models.enums import HoldingStatus
from app.modules.portfolio import service
from app.modules.portfolio.schemas import (
    AllocationBreakdown,
    AllocationResponse,
    CashFlowEntry,
    CashFlowResponse,
    HoldingCreateRequest,
    HoldingListResponse,
    HoldingResponse,
    HoldingTotals,
    HoldingUpdateRequest,
    PortfolioCreateRequest,
    PortfolioDetailResponse,
    PortfolioListResponse,
    PortfolioMetricsResponse,
    PortfolioResponse,
    PortfolioUpdateRequest,
)
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


# ── Helpers ─────────────────────────────────────────────────────────────────


def _portfolio_to_response(portfolio) -> PortfolioResponse:
    return PortfolioResponse(
        id=portfolio.id,
        name=portfolio.name,
        description=portfolio.description,
        strategy=portfolio.strategy,
        fund_type=portfolio.fund_type,
        vintage_year=portfolio.vintage_year,
        target_aum=portfolio.target_aum,
        current_aum=portfolio.current_aum,
        currency=portfolio.currency,
        sfdr_classification=portfolio.sfdr_classification,
        status=portfolio.status,
        created_at=portfolio.created_at,
        updated_at=portfolio.updated_at,
    )


def _holding_to_response(h) -> HoldingResponse:
    moic = None
    if h.investment_amount and h.investment_amount > 0:
        moic = h.current_value / h.investment_amount
    return HoldingResponse(
        id=h.id,
        portfolio_id=h.portfolio_id,
        project_id=h.project_id,
        asset_name=h.asset_name,
        asset_type=h.asset_type,
        investment_date=h.investment_date,
        investment_amount=h.investment_amount,
        current_value=h.current_value,
        ownership_pct=h.ownership_pct,
        currency=h.currency,
        status=h.status,
        exit_date=h.exit_date,
        exit_amount=h.exit_amount,
        notes=h.notes,
        moic=moic,
        created_at=h.created_at,
        updated_at=h.updated_at,
    )


# ── Portfolio CRUD ──────────────────────────────────────────────────────────


@router.get(
    "",
    summary="List portfolios",
    response_model=PortfolioListResponse,
    dependencies=[Depends(require_permission("view", "portfolio"))],
)
async def list_portfolios(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all portfolios for the current org."""
    portfolios = await service.list_portfolios(db, current_user.org_id)
    return PortfolioListResponse(
        items=[_portfolio_to_response(p) for p in portfolios],
        total=len(portfolios),
    )


@router.post(
    "",
    summary="Create portfolio",
    response_model=PortfolioResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("create", "portfolio"))],
)
async def create_portfolio(
    body: PortfolioCreateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new portfolio."""
    portfolio = await service.create_portfolio(
        db,
        current_user,
        name=body.name,
        description=body.description,
        strategy=body.strategy,
        fund_type=body.fund_type,
        vintage_year=body.vintage_year,
        target_aum=body.target_aum,
        current_aum=body.current_aum,
        currency=body.currency,
        sfdr_classification=body.sfdr_classification,
    )
    return _portfolio_to_response(portfolio)


@router.get(
    "/{portfolio_id}",
    summary="Get portfolio",
    response_model=PortfolioDetailResponse,
    dependencies=[Depends(require_permission("view", "portfolio"))],
)
async def get_portfolio(
    portfolio_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get portfolio details with latest metrics."""
    try:
        portfolio = await service.get_portfolio(db, portfolio_id, current_user.org_id)
        holdings = await service.list_holdings(db, portfolio_id, current_user.org_id)
        metrics = await service.get_latest_metrics(db, portfolio_id)

        metrics_resp = None
        if metrics:
            metrics_resp = PortfolioMetricsResponse(
                irr_gross=metrics.irr_gross,
                irr_net=metrics.irr_net,
                moic=metrics.moic,
                tvpi=metrics.tvpi,
                dpi=metrics.dpi,
                rvpi=metrics.rvpi,
                total_invested=metrics.total_invested,
                total_distributions=metrics.total_distributions,
                total_value=metrics.total_value,
                carbon_reduction_tons=metrics.carbon_reduction_tons,
                as_of_date=metrics.as_of_date,
            )

        base = _portfolio_to_response(portfolio)
        return PortfolioDetailResponse(
            **base.model_dump(),
            latest_metrics=metrics_resp,
            holding_count=len(holdings),
        )
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put(
    "/{portfolio_id}",
    summary="Update portfolio",
    response_model=PortfolioResponse,
    dependencies=[Depends(require_permission("edit", "portfolio"))],
)
async def update_portfolio(
    portfolio_id: uuid.UUID,
    body: PortfolioUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a portfolio."""
    try:
        portfolio = await service.update_portfolio(
            db, portfolio_id, current_user.org_id,
            **body.model_dump(exclude_unset=True),
        )
        return _portfolio_to_response(portfolio)
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ── Metrics ─────────────────────────────────────────────────────────────────


@router.get(
    "/{portfolio_id}/metrics",
    summary="Get portfolio metrics",
    response_model=PortfolioMetricsResponse,
    dependencies=[Depends(require_permission("view", "portfolio"))],
)
async def get_portfolio_metrics(
    portfolio_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_readonly_session),
):
    """Compute portfolio metrics (IRR, MOIC, TVPI, DPI, RVPI) using deterministic Python."""
    try:
        metrics = await service.compute_metrics(db, portfolio_id, current_user.org_id)
        return PortfolioMetricsResponse(**metrics)
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ── Holdings ────────────────────────────────────────────────────────────────


@router.get(
    "/{portfolio_id}/holdings",
    summary="List portfolio holdings",
    response_model=HoldingListResponse,
    dependencies=[Depends(require_permission("view", "portfolio"))],
)
async def list_holdings(
    portfolio_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_readonly_session),
    holding_status: HoldingStatus | None = Query(None, alias="status"),
):
    """List holdings in a portfolio."""
    try:
        holdings = await service.list_holdings(
            db, portfolio_id, current_user.org_id, status=holding_status
        )
        items = [_holding_to_response(h) for h in holdings]
        total_invested = sum(h.investment_amount for h in holdings)
        total_current = sum(h.current_value for h in holdings)
        weighted_moic = (
            total_current / total_invested if total_invested else None
        )
        return HoldingListResponse(
            items=items,
            total=len(items),
            totals=HoldingTotals(
                total_invested=total_invested,
                total_current_value=total_current,
                weighted_moic=weighted_moic,
            ),
        )
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/{portfolio_id}/holdings",
    summary="Add holding to portfolio",
    response_model=HoldingResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("edit", "portfolio"))],
)
async def add_holding(
    portfolio_id: uuid.UUID,
    body: HoldingCreateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a holding to a portfolio."""
    try:
        holding = await service.add_holding(
            db,
            current_user,
            portfolio_id,
            asset_name=body.asset_name,
            asset_type=body.asset_type,
            investment_date=body.investment_date,
            investment_amount=body.investment_amount,
            current_value=body.current_value,
            ownership_pct=body.ownership_pct,
            currency=body.currency,
            project_id=body.project_id,
            notes=body.notes,
        )
        return _holding_to_response(holding)
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put(
    "/{portfolio_id}/holdings/{holding_id}",
    summary="Update holding",
    response_model=HoldingResponse,
    dependencies=[Depends(require_permission("edit", "portfolio"))],
)
async def update_holding(
    portfolio_id: uuid.UUID,
    holding_id: uuid.UUID,
    body: HoldingUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a holding."""
    try:
        holding = await service.update_holding(
            db, holding_id, portfolio_id, current_user.org_id,
            **body.model_dump(exclude_unset=True),
        )
        return _holding_to_response(holding)
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ── Cash Flows ──────────────────────────────────────────────────────────────


@router.get(
    "/{portfolio_id}/cash-flows",
    summary="Get portfolio cash flows",
    response_model=CashFlowResponse,
    dependencies=[Depends(require_permission("view", "portfolio"))],
)
async def get_cash_flows(
    portfolio_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get cash flow time series for a portfolio."""
    try:
        flows = await service.get_cash_flows(db, portfolio_id, current_user.org_id)
        return CashFlowResponse(
            items=[CashFlowEntry(**f) for f in flows]
        )
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ── Allocation ──────────────────────────────────────────────────────────────


@router.get(
    "/{portfolio_id}/allocation",
    summary="Get portfolio allocation breakdown",
    response_model=AllocationResponse,
    dependencies=[Depends(require_permission("view", "portfolio"))],
)
async def get_allocation(
    portfolio_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get portfolio allocation breakdowns by sector, geography, stage, asset type."""
    try:
        alloc = await service.get_allocation(db, portfolio_id, current_user.org_id)
        return AllocationResponse(
            by_sector=[AllocationBreakdown(**a) for a in alloc["by_sector"]],
            by_geography=[AllocationBreakdown(**a) for a in alloc["by_geography"]],
            by_stage=[AllocationBreakdown(**a) for a in alloc["by_stage"]],
            by_asset_type=[AllocationBreakdown(**a) for a in alloc["by_asset_type"]],
        )
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
