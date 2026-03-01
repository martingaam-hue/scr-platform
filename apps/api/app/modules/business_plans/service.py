"""Business Plans — async DB service."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.financial import BusinessPlan
from app.modules.business_plans.schemas import BusinessPlanCreate, BusinessPlanUpdate


class BusinessPlanService:
    def __init__(self, db: AsyncSession, org_id: uuid.UUID) -> None:
        self.db = db
        self.org_id = org_id

    async def create(
        self, user_id: uuid.UUID, data: BusinessPlanCreate
    ) -> BusinessPlan:
        plan = BusinessPlan(
            org_id=self.org_id,
            project_id=data.project_id,
            created_by=user_id,
            title=data.title,
            executive_summary=data.executive_summary,
            financial_projections=data.financial_projections,
            market_analysis=data.market_analysis,
            risk_analysis=data.risk_analysis,
            use_of_funds=data.use_of_funds,
            team_section=data.team_section,
            risk_section=data.risk_section,
            status=data.status,
        )
        self.db.add(plan)
        await self.db.commit()
        await self.db.refresh(plan)
        return plan

    async def list(
        self, project_id: uuid.UUID | None = None
    ) -> list[BusinessPlan]:
        stmt = select(BusinessPlan).where(
            BusinessPlan.org_id == self.org_id,
            BusinessPlan.is_deleted.is_(False),
        )
        if project_id:
            stmt = stmt.where(BusinessPlan.project_id == project_id)
        stmt = stmt.order_by(BusinessPlan.updated_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get(self, plan_id: uuid.UUID) -> BusinessPlan | None:
        stmt = select(BusinessPlan).where(
            BusinessPlan.id == plan_id,
            BusinessPlan.org_id == self.org_id,
            BusinessPlan.is_deleted.is_(False),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update(
        self, plan_id: uuid.UUID, data: BusinessPlanUpdate
    ) -> BusinessPlan | None:
        plan = await self.get(plan_id)
        if not plan:
            return None
        patch = data.model_dump(exclude_unset=True)
        for k, v in patch.items():
            setattr(plan, k, v)
        plan.version += 1
        await self.db.commit()
        await self.db.refresh(plan)
        return plan

    async def delete(self, plan_id: uuid.UUID) -> bool:
        plan = await self.get(plan_id)
        if not plan:
            return False
        plan.is_deleted = True
        await self.db.commit()
        return True
