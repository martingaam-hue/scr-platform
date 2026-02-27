"""Business logic for the onboarding flow."""

import uuid
from decimal import Decimal, InvalidOperation

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core import Organization, User
from app.models.dataroom import DocumentFolder
from app.models.enums import (
    FundType,
    OrgType,
    PortfolioStatus,
    PortfolioStrategy,
    ProjectStage,
    ProjectStatus,
    ProjectType,
    RiskTolerance,
    SFDRClassification,
)
from app.models.investors import InvestorMandate, Portfolio
from app.modules.onboarding.schemas import OnboardingCompleteRequest
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()


def _safe_decimal(value: str | None, default: Decimal = Decimal("0")) -> Decimal:
    if not value:
        return default
    try:
        return Decimal(value)
    except (InvalidOperation, ValueError):
        return default


async def complete_onboarding(
    db: AsyncSession,
    current_user: CurrentUser,
    data: OnboardingCompleteRequest,
) -> dict:
    """
    Run the full onboarding flow:
    1. Update organisation type, name, settings
    2. Merge user preferences with onboarding_completed flag
    3. Create default entities based on org type
    """
    created: dict = {}

    # ── 1. Update organisation ───────────────────────────────────────────
    stmt = select(Organization).where(Organization.id == current_user.org_id)
    result = await db.execute(stmt)
    org = result.scalar_one()

    org.type = OrgType(data.org_type)
    org.name = data.org_name
    org.settings = {
        **org.settings,
        "industry": data.org_industry,
        "geography": data.org_geography,
        "size": data.org_size,
        "aum": data.org_aum,
    }

    # ── 2. Merge user preferences ────────────────────────────────────────
    stmt = select(User).where(User.id == current_user.user_id)
    result = await db.execute(stmt)
    user = result.scalar_one()

    user.preferences = {
        **user.preferences,
        **data.preferences,
        "onboarding_completed": True,
    }

    # ── 3. Create default entities ───────────────────────────────────────
    if data.org_type == "investor":
        created = await _setup_investor(db, current_user, org, data)
    else:
        created = await _setup_ally(db, current_user, org, data)

    await db.flush()

    redirect = "/dashboard/portfolio" if data.org_type == "investor" else "/dashboard/projects"

    logger.info(
        "onboarding_completed",
        user_id=str(current_user.user_id),
        org_id=str(current_user.org_id),
        org_type=data.org_type,
    )

    return {
        "success": True,
        "org_type": data.org_type,
        "created_entities": created,
        "redirect_to": redirect,
    }


# ── Investor setup ───────────────────────────────────────────────────────


async def _setup_investor(
    db: AsyncSession,
    current_user: CurrentUser,
    org: Organization,
    data: OnboardingCompleteRequest,
) -> dict:
    created: dict = {}

    # Default portfolio
    portfolio = Portfolio(
        org_id=current_user.org_id,
        name=f"{org.name} Portfolio",
        description="Default portfolio created during onboarding.",
        strategy=PortfolioStrategy.BALANCED,
        fund_type=FundType.OPEN_END,
        target_aum=_safe_decimal(data.org_aum),
        current_aum=Decimal("0"),
        currency="USD",
        sfdr_classification=SFDRClassification.NOT_APPLICABLE,
        status=PortfolioStatus.FUNDRAISING,
    )
    db.add(portfolio)
    await db.flush()
    created["portfolio_id"] = str(portfolio.id)

    # Investor mandate from preferences
    prefs = data.preferences
    mandate = InvestorMandate(
        org_id=current_user.org_id,
        name=f"{org.name} Mandate",
        sectors=prefs.get("sectors"),
        geographies=prefs.get("geographies"),
        stages=prefs.get("stages"),
        ticket_size_min=_safe_decimal(str(prefs.get("ticket_size_min", "0"))),
        ticket_size_max=_safe_decimal(str(prefs.get("ticket_size_max", "0"))),
        target_irr_min=None,
        risk_tolerance=RiskTolerance(prefs.get("risk_tolerance", "moderate")),
        is_active=True,
    )
    db.add(mandate)
    await db.flush()
    created["mandate_id"] = str(mandate.id)

    # Default folders (org-level, no project)
    folder_names = ["Due Diligence", "Legal Documents", "Financial Reports"]
    folder_ids = []
    for name in folder_names:
        folder = DocumentFolder(
            org_id=current_user.org_id,
            project_id=None,
            parent_folder_id=None,
            name=name,
        )
        db.add(folder)
        await db.flush()
        folder_ids.append(str(folder.id))
    created["folder_ids"] = folder_ids

    return created


# ── Ally setup ───────────────────────────────────────────────────────────


async def _setup_ally(
    db: AsyncSession,
    current_user: CurrentUser,
    org: Organization,
    data: OnboardingCompleteRequest,
) -> dict:
    created: dict = {}

    if data.first_action:
        # Create first project via the projects service
        from app.modules.projects.service import create_project

        fa = data.first_action
        project = await create_project(
            db,
            current_user,
            name=fa.get("name", f"{org.name} Project"),
            project_type=ProjectType(fa.get("project_type", "solar")),
            description=fa.get("description", ""),
            geography_country=fa.get("geography_country", ""),
            total_investment_required=_safe_decimal(
                str(fa.get("total_investment_required", "0"))
            ),
            currency=fa.get("currency", "USD"),
        )
        created["project_id"] = str(project.id)

        # Project-level folders
        folder_names = ["Technical Documents", "Financial Models", "Legal & Permits"]
        folder_ids = []
        for name in folder_names:
            folder = DocumentFolder(
                org_id=current_user.org_id,
                project_id=project.id,
                parent_folder_id=None,
                name=name,
            )
            db.add(folder)
            await db.flush()
            folder_ids.append(str(folder.id))
        created["folder_ids"] = folder_ids
    else:
        # Org-level folders
        folder_names = ["Project Templates", "Compliance", "Reports"]
        folder_ids = []
        for name in folder_names:
            folder = DocumentFolder(
                org_id=current_user.org_id,
                project_id=None,
                parent_folder_id=None,
                name=name,
            )
            db.add(folder)
            await db.flush()
            folder_ids.append(str(folder.id))
        created["folder_ids"] = folder_ids

    return created
