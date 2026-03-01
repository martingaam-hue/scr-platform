from __future__ import annotations

import uuid
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.modules.financial_templates.schemas import TemplateComputeRequest, DCFResult
from app.modules.financial_templates.service import FinancialTemplateService

router = APIRouter(prefix="/financial-templates", tags=["Financial Templates"])

@router.get("")
async def list_templates(
    taxonomy_code: str | None = Query(None),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    svc = FinancialTemplateService(db, current_user.org_id)
    templates = await svc.list_templates(taxonomy_code)
    return [
        {
            "id": str(t.id),
            "taxonomy_code": t.taxonomy_code,
            "name": t.name,
            "description": t.description,
            "is_system": t.is_system,
            "assumptions": t.assumptions,
        }
        for t in templates
    ]

@router.get("/{template_id}")
async def get_template(
    template_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    svc = FinancialTemplateService(db, current_user.org_id)
    t = await svc.get_template(template_id)
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"id": str(t.id), "taxonomy_code": t.taxonomy_code, "name": t.name, "assumptions": t.assumptions, "revenue_formula": t.revenue_formula, "cashflow_model": t.cashflow_model, "is_system": t.is_system}

@router.post("/{template_id}/compute")
async def compute_dcf(
    template_id: uuid.UUID,
    body: TemplateComputeRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DCFResult:
    svc = FinancialTemplateService(db, current_user.org_id)
    try:
        result = await svc.compute_dcf(template_id, body.overrides)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return DCFResult(**result)
