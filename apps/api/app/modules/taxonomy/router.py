from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.models.taxonomy import IndustryTaxonomy

router = APIRouter(prefix="/taxonomy", tags=["Industry Taxonomy"])

@router.get("")
async def list_taxonomy(
    parent_code: str | None = Query(None),
    level: int | None = Query(None),
    leaf_only: bool = Query(False),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    stmt = select(IndustryTaxonomy).where(IndustryTaxonomy.is_deleted.is_(False))
    if parent_code:
        stmt = stmt.where(IndustryTaxonomy.parent_code == parent_code)
    if level:
        stmt = stmt.where(IndustryTaxonomy.level == level)
    if leaf_only:
        stmt = stmt.where(IndustryTaxonomy.is_leaf.is_(True))
    stmt = stmt.order_by(IndustryTaxonomy.code)
    result = await db.execute(stmt)
    nodes = result.scalars().all()
    return [
        {
            "code": n.code,
            "parent_code": n.parent_code,
            "name": n.name,
            "description": n.description,
            "level": n.level,
            "is_leaf": n.is_leaf,
            "nace_code": n.nace_code,
            "meta": n.meta,
        }
        for n in nodes
    ]

@router.get("/{code}")
async def get_taxonomy_node(
    code: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(
        select(IndustryTaxonomy).where(IndustryTaxonomy.code == code, IndustryTaxonomy.is_deleted.is_(False))
    )
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail=f"Taxonomy code '{code}' not found")
    return {"code": node.code, "parent_code": node.parent_code, "name": node.name, "description": node.description, "level": node.level, "is_leaf": node.is_leaf, "nace_code": node.nace_code, "gics_code": node.gics_code, "meta": node.meta}
