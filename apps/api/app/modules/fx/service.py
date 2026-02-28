"""FX service — ECB rate fetching, currency conversion, exposure analysis."""

from __future__ import annotations

import uuid
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from typing import Any

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fx import FXRate

logger = structlog.get_logger()

ECB_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
ECB_NS = {
    "gesmes": "http://www.gesmes.org/xml/2002-08-01",
    "ecb": "http://www.ecb.int/vocabulary/2002-08-01/eurofxref",
}
SUPPORTED_CURRENCIES = ["EUR", "USD", "GBP", "CHF", "SEK", "NOK", "DKK", "JPY", "AUD", "CAD", "SGD", "HKD"]


# ── ECB fetch ─────────────────────────────────────────────────────────────────


async def fetch_ecb_rates(db: AsyncSession) -> dict[str, float]:
    """Fetch ECB reference rates and upsert into DB. Returns {currency: rate_vs_EUR}."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(ECB_URL)
        resp.raise_for_status()

    root = ET.fromstring(resp.text)
    cube = root.find(".//ecb:Cube/ecb:Cube", ECB_NS)
    if cube is None:
        logger.warning("ecb_fetch.no_cube_element")
        return {}

    rate_date_str = cube.get("time")
    rate_date = date.fromisoformat(rate_date_str) if rate_date_str else date.today()

    rates: dict[str, float] = {}
    for node in cube:
        currency = node.get("currency")
        rate_str = node.get("rate")
        if currency and rate_str:
            try:
                rates[currency] = float(rate_str)
            except ValueError:
                pass

    # Upsert into DB
    for currency, rate in rates.items():
        stmt = (
            pg_insert(FXRate)
            .values(
                base_currency="EUR",
                quote_currency=currency,
                rate=rate,
                rate_date=rate_date,
                source="ecb",
            )
            .on_conflict_do_nothing(
                index_elements=["base_currency", "quote_currency", "rate_date"]
            )
        )
        await db.execute(stmt)

    await db.commit()
    logger.info("ecb_fetch.complete", currencies=len(rates), rate_date=str(rate_date))
    return rates


# ── Rate lookup ───────────────────────────────────────────────────────────────


async def _get_rate(db: AsyncSession, base: str, quote: str, on_date: date) -> float | None:
    """Get EUR-based rate for a pair on or before the given date."""
    result = await db.execute(
        select(FXRate.rate)
        .where(
            FXRate.base_currency == base,
            FXRate.quote_currency == quote,
            FXRate.rate_date <= on_date,
        )
        .order_by(FXRate.rate_date.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    return float(row) if row is not None else None


async def get_latest_rates(db: AsyncSession) -> tuple[dict[str, float], date | None]:
    """Return the most recent rates for all supported currencies."""
    result = await db.execute(
        select(FXRate.quote_currency, FXRate.rate, FXRate.rate_date)
        .where(FXRate.base_currency == "EUR")
        .order_by(FXRate.rate_date.desc(), FXRate.quote_currency)
    )
    rows = result.all()
    seen: dict[str, float] = {}
    latest_date: date | None = None
    for currency, rate, rdate in rows:
        if currency not in seen:
            seen[currency] = float(rate)
            if latest_date is None:
                latest_date = rdate
    seen["EUR"] = 1.0
    return seen, latest_date


async def convert_amount(
    db: AsyncSession, amount: float, from_currency: str, to_currency: str, on_date: date | None = None
) -> tuple[float, float | None]:
    """Convert amount between currencies via EUR. Returns (converted, rate_used)."""
    if from_currency == to_currency:
        return amount, 1.0

    on_date = on_date or date.today()

    # Convert to EUR first
    eur_amount = amount
    rate_from = None
    if from_currency != "EUR":
        rate_from = await _get_rate(db, "EUR", from_currency, on_date)
        if rate_from:
            eur_amount = amount / rate_from
        else:
            return amount, None  # No rate available

    if to_currency == "EUR":
        return eur_amount, (1.0 / rate_from) if rate_from else None

    rate_to = await _get_rate(db, "EUR", to_currency, on_date)
    if not rate_to:
        return eur_amount, None

    return eur_amount * rate_to, rate_to / (rate_from or 1.0)


# ── Exposure analysis ─────────────────────────────────────────────────────────


async def get_fx_exposure(
    db: AsyncSession,
    org_id: uuid.UUID,
    portfolio_id: uuid.UUID | None = None,
    base_currency: str = "EUR",
) -> dict[str, Any]:
    """Portfolio value breakdown by project currency."""
    from sqlalchemy import func
    from app.models.projects import Project
    from app.models.financial import Valuation

    # Group projects by currency and sum their latest valuations
    stmt = (
        select(
            Project.project_currency,
            func.count(Project.id).label("project_count"),
            func.sum(Valuation.equity_value).label("total_equity"),
        )
        .outerjoin(Valuation, Valuation.project_id == Project.id)
        .where(Project.org_id == org_id, Project.is_deleted == False)
        .group_by(Project.project_currency)
    )
    if portfolio_id:
        from app.models.investors import PortfolioHolding
        stmt = stmt.join(PortfolioHolding, PortfolioHolding.project_id == Project.id).where(
            PortfolioHolding.portfolio_id == portfolio_id
        )

    result = await db.execute(stmt)
    rows = result.all()

    today = date.today()
    exposure: list[dict[str, Any]] = []
    total_base = 0.0

    for currency, count, total_equity in rows:
        value_eur = float(total_equity or 0)
        if currency and currency != "EUR":
            rate = await _get_rate(db, "EUR", currency, today)
            if rate:
                value_eur = value_eur / rate
        total_base += value_eur
        exposure.append({
            "currency": currency or "EUR",
            "value_eur": value_eur,
            "pct": 0.0,
            "project_count": int(count),
        })

    # Calculate percentages
    for item in exposure:
        item["pct"] = round((item["value_eur"] / total_base * 100) if total_base else 0, 1)

    # Hedging recommendation
    recommendation = _hedging_recommendation(exposure, total_base)

    return {
        "base_currency": base_currency,
        "total_value_base": total_base,
        "exposure": exposure,
        "hedging_recommendation": recommendation,
    }


def _hedging_recommendation(exposure: list[dict[str, Any]], total: float) -> str:
    if total == 0:
        return "No portfolio data available."
    non_eur = [e for e in exposure if e["currency"] != "EUR"]
    total_non_eur = sum(e["value_eur"] for e in non_eur)
    warnings = []
    for e in non_eur:
        if total_non_eur > 0 and (e["value_eur"] / total_non_eur) > 0.4:
            warnings.append(
                f"High concentration in {e['currency']} ({e['pct']:.1f}% of portfolio). Consider currency hedging."
            )
    if not warnings:
        return "FX exposure is well diversified. No immediate hedging action required."
    return " ".join(warnings)
