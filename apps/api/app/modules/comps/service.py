"""Comparable Transactions service — search, AI similarity, implied valuation, CSV import."""

from __future__ import annotations

import csv
import io
import json
import statistics
import uuid
from datetime import date
from typing import Any

import httpx
import structlog
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.comps import ComparableTransaction
from app.models.projects import Project
from app.modules.comps.schemas import CompCreate, CompUpdate

logger = structlog.get_logger()

_AI_TIMEOUT = 90.0


# ── Helpers ───────────────────────────────────────────────────────────────────


def _percentile(values: list[float], pct: float) -> float | None:
    """Return the pct-th percentile (0–100) from a sorted list."""
    if not values:
        return None
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    if n == 1:
        return sorted_vals[0]
    k = (pct / 100) * (n - 1)
    lo = int(k)
    hi = lo + 1
    if hi >= n:
        return sorted_vals[-1]
    return sorted_vals[lo] + (k - lo) * (sorted_vals[hi] - sorted_vals[lo])


# ── CRUD ──────────────────────────────────────────────────────────────────────


async def get_comp(
    db: AsyncSession,
    comp_id: uuid.UUID,
    org_id: uuid.UUID,
) -> ComparableTransaction | None:
    """Fetch a single comp accessible by this org (own or global)."""
    comp = await db.get(ComparableTransaction, comp_id)
    if not comp or comp.is_deleted:
        return None
    # Access check: org comp must belong to the requesting org; global comps are public
    if comp.org_id is not None and comp.org_id != org_id:
        return None
    return comp


async def create_comp(
    db: AsyncSession,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    data: CompCreate,
) -> ComparableTransaction:
    """Create a new org-private comparable transaction."""
    payload = data.model_dump()
    # Denormalise close_year from close_date if not explicitly provided
    if payload.get("close_date") and not payload.get("close_year"):
        payload["close_year"] = payload["close_date"].year

    comp = ComparableTransaction(
        org_id=org_id,
        added_by=user_id,
        **payload,
    )
    db.add(comp)
    await db.commit()
    await db.refresh(comp)
    logger.info("comp.created", comp_id=str(comp.id), org_id=str(org_id))
    return comp


async def update_comp(
    db: AsyncSession,
    comp_id: uuid.UUID,
    org_id: uuid.UUID,
    data: CompUpdate,
) -> ComparableTransaction | None:
    """Update an existing comp. Only org-owned comps can be mutated."""
    comp = await db.get(ComparableTransaction, comp_id)
    if not comp or comp.is_deleted:
        return None
    # Only the owning org can update
    if comp.org_id != org_id:
        return None

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(comp, field, value)

    # Re-derive close_year if close_date changed
    if "close_date" in update_data and update_data["close_date"]:
        if not update_data.get("close_year"):
            comp.close_year = update_data["close_date"].year

    await db.commit()
    await db.refresh(comp)
    logger.info("comp.updated", comp_id=str(comp.id), org_id=str(org_id))
    return comp


async def delete_comp(
    db: AsyncSession,
    comp_id: uuid.UUID,
    org_id: uuid.UUID,
) -> bool:
    """Soft-delete a comp. Only org-owned comps can be deleted."""
    comp = await db.get(ComparableTransaction, comp_id)
    if not comp or comp.is_deleted:
        return False
    if comp.org_id != org_id:
        return False

    comp.is_deleted = True
    await db.commit()
    logger.info("comp.deleted", comp_id=str(comp.id), org_id=str(org_id))
    return True


# ── Search ────────────────────────────────────────────────────────────────────


async def search_comps(
    db: AsyncSession,
    org_id: uuid.UUID,
    asset_type: str | None = None,
    geography: str | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    stage: str | None = None,
    min_size_eur: float | None = None,
    max_size_eur: float | None = None,
    limit: int = 50,
) -> list[ComparableTransaction]:
    """Structured filter search — returns org's own comps + global comps.

    WHERE (org_id = :org_id OR org_id IS NULL)
    AND is_deleted = false
    AND optional filters
    """
    stmt = select(ComparableTransaction).where(
        or_(
            ComparableTransaction.org_id == org_id,
            ComparableTransaction.org_id.is_(None),
        ),
        ComparableTransaction.is_deleted.is_(False),
    )

    if asset_type:
        stmt = stmt.where(ComparableTransaction.asset_type == asset_type)
    if geography:
        stmt = stmt.where(
            ComparableTransaction.geography.ilike(f"%{geography}%")
        )
    if year_from is not None:
        stmt = stmt.where(ComparableTransaction.close_year >= year_from)
    if year_to is not None:
        stmt = stmt.where(ComparableTransaction.close_year <= year_to)
    if stage:
        stmt = stmt.where(ComparableTransaction.stage_at_close == stage)
    if min_size_eur is not None:
        stmt = stmt.where(ComparableTransaction.deal_size_eur >= min_size_eur)
    if max_size_eur is not None:
        stmt = stmt.where(ComparableTransaction.deal_size_eur <= max_size_eur)

    stmt = stmt.order_by(ComparableTransaction.close_year.desc().nullslast()).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ── AI similarity ─────────────────────────────────────────────────────────────


async def find_similar_comps(
    db: AsyncSession,
    org_id: uuid.UUID,
    project_id: uuid.UUID,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """AI-powered similarity ranking: score each comp against a project.

    Steps:
    1. Load project details
    2. Fetch candidate comps by asset_type (structured filter)
    3. Call AI Gateway task_type="rank_comparable_transactions" to score similarity
    4. Return top-N sorted by similarity_score desc with rationale
    """
    # 1. Load project
    project = await db.get(Project, project_id)
    if not project:
        raise LookupError(f"Project {project_id} not found")

    project_asset_type = (
        project.project_type.value if project.project_type else None
    )

    # 2. Get candidate comps (same asset type preferred, fallback to all)
    candidates = await search_comps(
        db,
        org_id=org_id,
        asset_type=project_asset_type,
        limit=100,
    )
    if not candidates:
        # Fallback: all asset types
        candidates = await search_comps(db, org_id=org_id, limit=100)

    if not candidates:
        return []

    # Build lightweight comp summaries for the AI prompt
    comp_summaries = [
        {
            "comp_id": str(c.id),
            "deal_name": c.deal_name,
            "asset_type": c.asset_type,
            "geography": c.geography,
            "close_year": c.close_year,
            "capacity_mw": c.capacity_mw,
            "stage_at_close": c.stage_at_close,
            "offtake_type": c.offtake_type,
            "ev_per_mw": c.ev_per_mw,
            "equity_irr": c.equity_irr,
            "data_quality": c.data_quality,
        }
        for c in candidates
    ]

    # 3. Build project context for AI
    project_context = {
        "name": project.name,
        "asset_type": project_asset_type,
        "stage": project.stage.value if project.stage else None,
        "geography": project.geography_country,
        "capacity_mw": getattr(project, "capacity_mw", None),
        "total_investment_required": getattr(
            project, "total_investment_required", None
        ),
    }

    prompt = _build_similarity_prompt(project_context, comp_summaries)

    ranked_comps: list[dict[str, Any]] = []
    try:
        async with httpx.AsyncClient(timeout=_AI_TIMEOUT) as client:
            resp = await client.post(
                f"{settings.AI_GATEWAY_URL}/v1/completions",
                json={
                    "messages": [{"role": "user", "content": prompt}],
                    "task_type": "rank_comparable_transactions",
                    "max_tokens": 2000,
                    "temperature": 0.2,
                    "org_id": str(org_id),
                    "user_id": "system",
                },
                headers={"Authorization": f"Bearer {settings.AI_GATEWAY_API_KEY}"},
            )
            resp.raise_for_status()
            data = resp.json()
            content = data.get("content", "")

            # Parse ranked_comps from AI response
            try:
                parsed = json.loads(content)
                ranked_comps = parsed.get("ranked_comps", [])
            except json.JSONDecodeError:
                import re
                match = re.search(r"\{[\s\S]*\}", content)
                if match:
                    parsed = json.loads(match.group())
                    ranked_comps = parsed.get("ranked_comps", [])

    except Exception as exc:
        logger.warning(
            "comps.similarity_ai_failed",
            project_id=str(project_id),
            error=str(exc),
        )
        # Graceful fallback: return all candidates with neutral score
        comp_map = {str(c.id): c for c in candidates}
        return [
            {
                "comp": comp_map[str(c.id)].to_dict(),
                "similarity_score": 50,
                "rationale": "AI scoring unavailable — showing unranked results.",
            }
            for c in candidates[:limit]
            if str(c.id) in comp_map
        ]

    # 4. Join AI scores back to full comp data
    comp_map = {str(c.id): c for c in candidates}
    results: list[dict[str, Any]] = []
    for item in ranked_comps:
        comp_id = item.get("comp_id", "")
        comp = comp_map.get(comp_id)
        if comp:
            results.append(
                {
                    "comp": comp.to_dict(),
                    "similarity_score": max(0, min(100, int(item.get("similarity_score", 0)))),
                    "rationale": str(item.get("rationale", "")),
                }
            )

    results.sort(key=lambda x: x["similarity_score"], reverse=True)
    return results[:limit]


def _build_similarity_prompt(
    project: dict[str, Any],
    comps: list[dict[str, Any]],
) -> str:
    return f"""You are a renewable energy M&A analyst. Rank the following comparable transactions by similarity to the target project.

TARGET PROJECT:
{json.dumps(project, indent=2)}

CANDIDATE COMPARABLES ({len(comps)} total):
{json.dumps(comps, indent=2)}

Score each comp 0–100 for similarity to the target project. Consider:
- Asset type match (solar vs wind vs BESS etc.) — most important
- Geography / regulatory regime proximity
- Stage at close vs current project stage
- Size (capacity MW) similarity
- Offtake structure similarity
- Recency (prefer last 5 years)

Respond ONLY with valid JSON (no markdown):
{{
  "ranked_comps": [
    {{
      "comp_id": "<uuid>",
      "similarity_score": <integer 0-100>,
      "rationale": "<1-2 sentence explanation of similarity>"
    }}
  ]
}}

Include ALL {len(comps)} comps in ranked_comps, sorted highest score first."""


# ── Implied valuation ─────────────────────────────────────────────────────────


async def calculate_implied_valuation(
    db: AsyncSession,
    org_id: uuid.UUID,
    comp_ids: list[uuid.UUID],
    project: dict[str, Any],
) -> dict[str, Any]:
    """Calculate implied valuation from selected comps using deterministic statistics.

    Financial calculations use statistics.median() and percentile math.
    NEVER LLM for calculations.
    """
    # Load all requested comps (must be accessible to this org)
    comps = []
    for cid in comp_ids:
        comp = await get_comp(db, cid, org_id)
        if comp:
            comps.append(comp)

    if not comps:
        return {
            "ev_per_mw_median": None,
            "ev_per_mw_p25": None,
            "ev_per_mw_p75": None,
            "implied_ev_eur": None,
            "ebitda_multiple_median": None,
            "ebitda_multiple_p25": None,
            "ebitda_multiple_p75": None,
            "implied_ev_from_ebitda": None,
            "comps_used": 0,
            "rationale": "No accessible comps found for the provided IDs.",
        }

    # ── EV/MW metrics ─────────────────────────────────────────────────────────
    ev_per_mw_values = [c.ev_per_mw for c in comps if c.ev_per_mw is not None]

    ev_per_mw_median: float | None = None
    ev_per_mw_p25: float | None = None
    ev_per_mw_p75: float | None = None
    implied_ev_eur: float | None = None

    if ev_per_mw_values:
        ev_per_mw_median = statistics.median(ev_per_mw_values)
        ev_per_mw_p25 = _percentile(ev_per_mw_values, 25)
        ev_per_mw_p75 = _percentile(ev_per_mw_values, 75)
        project_capacity_mw = project.get("capacity_mw")
        if project_capacity_mw:
            implied_ev_eur = ev_per_mw_median * float(project_capacity_mw)

    # ── EBITDA multiple metrics ────────────────────────────────────────────────
    ebitda_values = [c.ebitda_multiple for c in comps if c.ebitda_multiple is not None]

    ebitda_multiple_median: float | None = None
    ebitda_multiple_p25: float | None = None
    ebitda_multiple_p75: float | None = None
    implied_ev_from_ebitda: float | None = None

    if ebitda_values:
        ebitda_multiple_median = statistics.median(ebitda_values)
        ebitda_multiple_p25 = _percentile(ebitda_values, 25)
        ebitda_multiple_p75 = _percentile(ebitda_values, 75)
        project_ebitda = project.get("ebitda")
        if project_ebitda:
            implied_ev_from_ebitda = ebitda_multiple_median * float(project_ebitda)

    # ── Rationale ─────────────────────────────────────────────────────────────
    rationale_parts = []
    if ev_per_mw_values:
        rationale_parts.append(
            f"EV/MW based on median of {len(ev_per_mw_values)} comparable transactions "
            f"(range: {min(ev_per_mw_values):,.0f}–{max(ev_per_mw_values):,.0f} €k/MW)"
        )
    if ebitda_values:
        rationale_parts.append(
            f"EBITDA multiple based on median of {len(ebitda_values)} comparable transactions "
            f"(range: {min(ebitda_values):.1f}x–{max(ebitda_values):.1f}x)"
        )
    rationale = (
        ". ".join(rationale_parts) + "."
        if rationale_parts
        else "Insufficient comp data for valuation."
    )

    return {
        "ev_per_mw_median": ev_per_mw_median,
        "ev_per_mw_p25": ev_per_mw_p25,
        "ev_per_mw_p75": ev_per_mw_p75,
        "implied_ev_eur": implied_ev_eur,
        "ebitda_multiple_median": ebitda_multiple_median,
        "ebitda_multiple_p25": ebitda_multiple_p25,
        "ebitda_multiple_p75": ebitda_multiple_p75,
        "implied_ev_from_ebitda": implied_ev_from_ebitda,
        "comps_used": len(comps),
        "rationale": rationale,
    }


# ── CSV import ────────────────────────────────────────────────────────────────

# Column name aliases: canonical_field → list of accepted CSV header names
_COLUMN_ALIASES: dict[str, list[str]] = {
    "deal_name": ["deal_name", "deal name", "name", "transaction"],
    "asset_type": ["asset_type", "asset type", "type", "technology"],
    "geography": ["geography", "region", "country"],
    "country_code": ["country_code", "country code", "iso"],
    "close_date": ["close_date", "close date", "date", "transaction_date"],
    "close_year": ["close_year", "close year", "year"],
    "deal_size_eur": ["deal_size_eur", "deal size eur", "deal size", "size_eur", "size eur"],
    "capacity_mw": ["capacity_mw", "capacity mw", "capacity", "mw"],
    "ev_per_mw": ["ev_per_mw", "ev/mw", "ev per mw", "enterprise value per mw"],
    "equity_value_eur": ["equity_value_eur", "equity value eur", "equity value"],
    "equity_irr": ["equity_irr", "equity irr", "irr"],
    "project_irr": ["project_irr", "project irr"],
    "ebitda_multiple": ["ebitda_multiple", "ebitda multiple", "ebitda x"],
    "stage_at_close": ["stage_at_close", "stage", "development stage"],
    "offtake_type": ["offtake_type", "offtake", "offtake type"],
    "offtake_counterparty_rating": ["offtake_counterparty_rating", "rating", "counterparty rating"],
    "buyer_type": ["buyer_type", "buyer type", "buyer"],
    "seller_type": ["seller_type", "seller type", "seller"],
    "source": ["source", "data source"],
    "source_url": ["source_url", "source url", "url"],
    "data_quality": ["data_quality", "data quality", "quality"],
    "description": ["description", "notes", "comment"],
}


def _normalise_header(header: str) -> str:
    return header.strip().lower().replace("-", " ").replace("_", " ")


def _build_column_map(headers: list[str]) -> dict[str, str]:
    """Map CSV headers → canonical field names."""
    normalised = {_normalise_header(h): h for h in headers}
    mapping: dict[str, str] = {}
    for canonical, aliases in _COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in normalised:
                mapping[canonical] = normalised[alias]
                break
    return mapping


def _parse_float(val: str | None) -> float | None:
    if not val or not val.strip():
        return None
    try:
        return float(val.strip().replace(",", "").replace("%", ""))
    except (ValueError, TypeError):
        return None


def _parse_int(val: str | None) -> int | None:
    f = _parse_float(val)
    return int(f) if f is not None else None


def _parse_date(val: str | None) -> date | None:
    if not val or not val.strip():
        return None
    from datetime import datetime

    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y"):
        try:
            return datetime.strptime(val.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _parse_row(row: dict[str, str], col_map: dict[str, str]) -> dict[str, Any]:
    """Convert a raw CSV row dict to a ComparableTransaction field dict."""

    def get(field: str) -> str | None:
        csv_col = col_map.get(field)
        return row.get(csv_col, "").strip() if csv_col else None

    parsed: dict[str, Any] = {}

    # String fields
    for str_field in (
        "deal_name",
        "asset_type",
        "geography",
        "country_code",
        "stage_at_close",
        "offtake_type",
        "offtake_counterparty_rating",
        "buyer_type",
        "seller_type",
        "source",
        "source_url",
        "description",
    ):
        val = get(str_field)
        if val:
            parsed[str_field] = val

    # Data quality (with default)
    dq = get("data_quality")
    parsed["data_quality"] = dq if dq in {"confirmed", "estimated", "rumored"} else "estimated"

    # Float fields
    for float_field in (
        "deal_size_eur",
        "capacity_mw",
        "ev_per_mw",
        "equity_value_eur",
        "equity_irr",
        "project_irr",
        "ebitda_multiple",
    ):
        val = _parse_float(get(float_field))
        if val is not None:
            parsed[float_field] = val

    # Date / year
    close_date = _parse_date(get("close_date"))
    if close_date:
        parsed["close_date"] = close_date
        parsed["close_year"] = close_date.year

    year = _parse_int(get("close_year"))
    if year and "close_year" not in parsed:
        parsed["close_year"] = year

    return parsed


async def import_comps_csv(
    db: AsyncSession,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    csv_content: str,
) -> dict[str, Any]:
    """Parse CSV and bulk-insert comparable transactions.

    Expected columns (flexible, see _COLUMN_ALIASES):
        deal_name, asset_type, geography, close_year, deal_size_eur,
        capacity_mw, equity_irr, ev_per_mw, stage_at_close, ...

    Returns: {created: int, errors: list[{row, error}]}
    """
    reader = csv.DictReader(io.StringIO(csv_content))
    headers = reader.fieldnames or []
    col_map = _build_column_map(list(headers))

    # deal_name and asset_type are mandatory
    if "deal_name" not in col_map:
        return {
            "created": 0,
            "errors": [{"row": {}, "error": "CSV must contain a 'deal_name' column"}],
        }
    if "asset_type" not in col_map:
        return {
            "created": 0,
            "errors": [{"row": {}, "error": "CSV must contain an 'asset_type' column"}],
        }

    created = 0
    errors: list[dict[str, Any]] = []

    for row_num, row in enumerate(reader, start=2):  # 1-indexed, row 1 = header
        try:
            fields = _parse_row(row, col_map)

            # Validate required fields
            if not fields.get("deal_name"):
                raise ValueError("deal_name is empty")
            if not fields.get("asset_type"):
                raise ValueError("asset_type is empty")

            comp = ComparableTransaction(
                org_id=org_id,
                added_by=user_id,
                **fields,
            )
            db.add(comp)
            created += 1
        except Exception as exc:
            errors.append({"row_number": row_num, "row": dict(row), "error": str(exc)})

    if created > 0:
        await db.commit()

    logger.info(
        "comps.csv_import",
        org_id=str(org_id),
        created=created,
        errors=len(errors),
    )
    return {"created": created, "errors": errors}
