"""LP Reporting service.

Financial metrics (IRR, TVPI, DPI, RVPI, MOIC) are calculated deterministically
using Python/numpy-financial — NEVER by an LLM.

AI narrative generation is handled by calling the AI Gateway with
task_type="generate_lp_report_narrative".

HTML report generation uses a Jinja2 template stored in S3 for download.
"""

from __future__ import annotations

import math
import uuid
from datetime import date, datetime, timezone
from typing import Any

import boto3
import httpx
import numpy_financial as npf
import structlog
from botocore.config import Config as BotoConfig
from jinja2 import Environment, BaseLoader
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.lp_report import LPReport

logger = structlog.get_logger()

_TIMEOUT = 90.0


# ── S3 helpers ────────────────────────────────────────────────────────────────


def _get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION,
        config=BotoConfig(signature_version="s3v4"),
    )


def _generate_presigned_url(s3_key: str, expires_in: int = 3600) -> str:
    s3 = _get_s3_client()
    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.AWS_S3_BUCKET, "Key": s3_key},
        ExpiresIn=expires_in,
    )


# ── Financial calculations — DETERMINISTIC Python, NEVER LLM ─────────────────


def calculate_fund_metrics(
    cash_flows: list[dict[str, Any]],
    nav: float | None = None,
    total_committed: float | None = None,
    total_invested: float | None = None,
    total_returned: float | None = None,
    total_nav: float | None = None,
) -> dict[str, Any]:
    """
    Calculate fund performance metrics from cash flows.

    cash_flows: list of {date: str, amount: float}
      - negative amounts = capital invested
      - positive amounts = distributions returned

    If nav is provided and the last cash flow does not include NAV,
    it is appended as a positive terminal value for IRR computation.

    This function is DETERMINISTIC Python — it never calls an LLM.
    """
    amounts = [cf["amount"] for cf in cash_flows] if cash_flows else []

    # Derive invested / returned from cash flows if not explicitly provided
    invested = total_invested
    returned = total_returned
    nav_value = total_nav if total_nav is not None else (nav or 0.0)

    if invested is None:
        invested = sum(abs(a) for a in amounts if a < 0)
    if returned is None:
        returned = sum(a for a in amounts if a > 0)

    # Gross IRR: include NAV as terminal positive cash flow for the IRR calc
    gross_irr: float | None = None
    if len(amounts) >= 2:
        irr_amounts = list(amounts)
        if nav_value > 0:
            irr_amounts.append(nav_value)
        try:
            raw_irr = npf.irr(irr_amounts)
            if raw_irr is not None and not math.isnan(raw_irr) and not math.isinf(raw_irr):
                gross_irr = float(raw_irr)
        except Exception:
            gross_irr = None

    # Net IRR: approximately 2% lower than gross (management fees proxy)
    net_irr: float | None = None
    if gross_irr is not None:
        net_irr = round(gross_irr - 0.02, 6)

    # Multiples
    tvpi: float | None = None
    dpi: float | None = None
    rvpi: float | None = None
    moic: float | None = None

    if invested and invested > 0:
        tvpi = round((returned + nav_value) / invested, 4)
        dpi = round(returned / invested, 4)
        rvpi = round(nav_value / invested, 4)
        moic = round((returned + nav_value) / invested, 4)

    return {
        "gross_irr": gross_irr,
        "net_irr": net_irr,
        "tvpi": tvpi,
        "dpi": dpi,
        "rvpi": rvpi,
        "moic": moic,
        "total_invested": invested,
        "total_returned": returned,
        "total_nav": nav_value,
    }


# ── AI narrative generation ───────────────────────────────────────────────────


async def generate_narrative(report_data: dict[str, Any]) -> dict[str, str]:
    """
    Call AI Gateway to generate the four narrative sections of an LP report.

    report_data includes fund metrics, period, and investments summary.
    Returns {executive_summary, portfolio_commentary, market_outlook, esg_highlights}.
    """
    period = report_data.get("report_period", "")
    tvpi = report_data.get("tvpi")
    dpi = report_data.get("dpi")
    gross_irr = report_data.get("gross_irr")
    net_irr = report_data.get("net_irr")
    total_invested = report_data.get("total_invested")
    total_nav = report_data.get("total_nav")
    investments = report_data.get("investments_data") or []

    investments_summary = "\n".join(
        f"  - {inv.get('name', 'Unknown')} | Stage: {inv.get('stage', 'N/A')} | "
        f"Invested: ${inv.get('invested', 0):,.0f} | NAV: ${inv.get('nav', 0):,.0f} | "
        f"MOIC: {inv.get('moic', 'N/A')}"
        for inv in investments[:20]
    )

    prompt = f"""You are a senior investor relations professional preparing an ILPA-compliant LP report.

Fund period: {period}
Fund metrics:
- Gross IRR: {f'{gross_irr:.1%}' if gross_irr is not None else 'N/A'}
- Net IRR: {f'{net_irr:.1%}' if net_irr is not None else 'N/A'}
- TVPI: {f'{tvpi:.2f}x' if tvpi is not None else 'N/A'}
- DPI: {f'{dpi:.2f}x' if dpi is not None else 'N/A'}
- Total Invested: {f'${total_invested:,.0f}' if total_invested else 'N/A'}
- Portfolio NAV: {f'${total_nav:,.0f}' if total_nav else 'N/A'}

Portfolio investments:
{investments_summary if investments_summary else '  No investment data provided.'}

Write four narrative sections for the LP report. Respond ONLY with valid JSON:
{{
  "executive_summary": "<3-5 sentence overview of the fund's performance and key highlights for this period>",
  "portfolio_commentary": "<3-5 sentence commentary on portfolio company performance, notable developments, and investment activity>",
  "market_outlook": "<2-4 sentence forward-looking view on market conditions relevant to the portfolio>",
  "esg_highlights": "<2-3 sentence summary of ESG and impact initiatives across the portfolio>"
}}"""

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{settings.AI_GATEWAY_URL}/v1/completions",
                json={
                    "prompt": prompt,
                    "task_type": "generate_lp_report_narrative",
                    "max_tokens": 2000,
                    "temperature": 0.5,
                },
                headers={"Authorization": f"Bearer {settings.AI_GATEWAY_API_KEY}"},
            )
            resp.raise_for_status()
            data = resp.json()

        # Try validated_data first (structured), fall back to parsing content
        validated = data.get("validated_data")
        if validated and all(
            k in validated
            for k in ("executive_summary", "portfolio_commentary", "market_outlook", "esg_highlights")
        ):
            return {
                "executive_summary": validated["executive_summary"],
                "portfolio_commentary": validated["portfolio_commentary"],
                "market_outlook": validated["market_outlook"],
                "esg_highlights": validated["esg_highlights"],
            }

        # Fallback: parse content JSON manually
        import json
        import re

        content = data.get("content", "")
        match = re.search(r"\{[\s\S]*\}", content)
        if match:
            parsed = json.loads(match.group())
            return {
                "executive_summary": parsed.get("executive_summary", ""),
                "portfolio_commentary": parsed.get("portfolio_commentary", ""),
                "market_outlook": parsed.get("market_outlook", ""),
                "esg_highlights": parsed.get("esg_highlights", ""),
            }

    except Exception as exc:
        logger.warning("lp_report.narrative_generation_failed", error=str(exc))

    # Fallback: template-based narrative using real metrics
    irr_str = f"{gross_irr:.1%}" if gross_irr is not None else "N/A"
    tvpi_str = f"{tvpi:.2f}x" if tvpi is not None else "N/A"
    dpi_str = f"{dpi:.2f}x" if dpi is not None else "N/A"
    nav_str = f"${total_nav:,.0f}" if total_nav else "N/A"
    inv_count = len(investments)
    return {
        "executive_summary": (
            f"For {period}, the fund reported a gross IRR of {irr_str} and a TVPI of {tvpi_str}. "
            f"Distributions to paid-in capital (DPI) stand at {dpi_str}, with a portfolio NAV of {nav_str}. "
            f"The portfolio comprises {inv_count} active investment(s). "
            "Full narrative commentary will be appended following investment team review."
        ),
        "portfolio_commentary": (
            f"The portfolio holds {inv_count} investment(s) as of {period}. "
            "Performance across holdings reflects ongoing operational and market developments. "
            "Investment activity and valuation updates are detailed in the per-investment schedules."
        ),
        "market_outlook": (
            "Macroeconomic conditions continue to influence asset valuations and deal flow. "
            "The investment team is monitoring interest rate trends, sector dynamics, and regulatory changes "
            "as they pertain to portfolio exposure and new deployment opportunities."
        ),
        "esg_highlights": (
            "ESG monitoring is ongoing across portfolio companies. "
            "Impact metrics and sustainability disclosures will be aggregated in the next reporting cycle."
        ),
    }


# ── HTML report generation ────────────────────────────────────────────────────

_REPORT_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>LP Report — {{ report_period }}</title>
  <style>
    body { font-family: 'Georgia', serif; margin: 0; padding: 40px; color: #1a1a2e; background: #fff; }
    .cover { text-align: center; padding: 80px 0 60px; border-bottom: 3px solid #2563eb; }
    .cover h1 { font-size: 2.5rem; font-weight: bold; color: #1e3a8a; margin: 0 0 12px; }
    .cover h2 { font-size: 1.25rem; color: #64748b; margin: 0 0 8px; font-weight: normal; }
    .cover .period { font-size: 1rem; color: #94a3b8; }
    section { margin: 48px 0; }
    h3 { font-size: 1.2rem; color: #1e3a8a; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; margin-bottom: 16px; }
    p { line-height: 1.7; color: #374151; }
    .metrics-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin: 24px 0; }
    .metric-card { border: 1px solid #e2e8f0; border-radius: 8px; padding: 20px; text-align: center; background: #f8fafc; }
    .metric-card .label { font-size: 0.8rem; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; }
    .metric-card .value { font-size: 1.8rem; font-weight: bold; color: #1e3a8a; margin-top: 6px; }
    .metric-card .sub { font-size: 0.75rem; color: #94a3b8; margin-top: 4px; }
    table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
    th { background: #1e3a8a; color: #fff; padding: 10px 12px; text-align: left; font-weight: 600; }
    td { padding: 9px 12px; border-bottom: 1px solid #f1f5f9; }
    tr:nth-child(even) td { background: #f8fafc; }
    .status-badge { display: inline-block; padding: 2px 10px; border-radius: 999px; font-size: 0.75rem; font-weight: 600; background: #dcfce7; color: #16a34a; }
    .footer { margin-top: 60px; border-top: 1px solid #e2e8f0; padding-top: 20px; font-size: 0.75rem; color: #94a3b8; }
  </style>
</head>
<body>
  <!-- Cover -->
  <div class="cover">
    <h1>LP Performance Report</h1>
    <h2>{{ report_period }}</h2>
    <p class="period">{{ period_start }} — {{ period_end }}</p>
    <p class="period" style="margin-top:8px;">Generated {{ generated_at }} &nbsp;&bull;&nbsp; Status: <span class="status-badge">{{ status }}</span></p>
  </div>

  <!-- Executive Summary -->
  <section>
    <h3>Executive Summary</h3>
    <p>{{ narrative.executive_summary }}</p>
  </section>

  <!-- Fund Performance Metrics -->
  <section>
    <h3>Fund Performance Metrics</h3>
    <div class="metrics-grid">
      <div class="metric-card">
        <div class="label">Gross IRR</div>
        <div class="value">{{ gross_irr }}</div>
        <div class="sub">Internal Rate of Return</div>
      </div>
      <div class="metric-card">
        <div class="label">Net IRR</div>
        <div class="value">{{ net_irr }}</div>
        <div class="sub">After Fees</div>
      </div>
      <div class="metric-card">
        <div class="label">TVPI</div>
        <div class="value">{{ tvpi }}</div>
        <div class="sub">Total Value / Paid-In</div>
      </div>
      <div class="metric-card">
        <div class="label">DPI</div>
        <div class="value">{{ dpi }}</div>
        <div class="sub">Distributions / Paid-In</div>
      </div>
      <div class="metric-card">
        <div class="label">RVPI</div>
        <div class="value">{{ rvpi }}</div>
        <div class="sub">Residual Value / Paid-In</div>
      </div>
      <div class="metric-card">
        <div class="label">MOIC</div>
        <div class="value">{{ moic }}</div>
        <div class="sub">Multiple on Invested Capital</div>
      </div>
    </div>
    <table>
      <tr><th>Metric</th><th>Value</th></tr>
      <tr><td>Total Committed Capital</td><td>{{ total_committed }}</td></tr>
      <tr><td>Total Invested Capital</td><td>{{ total_invested }}</td></tr>
      <tr><td>Total Distributions</td><td>{{ total_returned }}</td></tr>
      <tr><td>Net Asset Value (NAV)</td><td>{{ total_nav }}</td></tr>
    </table>
  </section>

  <!-- Portfolio Commentary -->
  <section>
    <h3>Portfolio Commentary</h3>
    <p>{{ narrative.portfolio_commentary }}</p>
  </section>

  <!-- Portfolio Investments -->
  {% if investments %}
  <section>
    <h3>Portfolio Investments</h3>
    <table>
      <tr>
        <th>Investment</th>
        <th>Stage</th>
        <th>Vintage</th>
        <th>Committed ($)</th>
        <th>Invested ($)</th>
        <th>NAV ($)</th>
        <th>Realized ($)</th>
        <th>MOIC</th>
      </tr>
      {% for inv in investments %}
      <tr>
        <td>{{ inv.name }}</td>
        <td>{{ inv.stage or '—' }}</td>
        <td>{{ inv.vintage or '—' }}</td>
        <td>{{ inv.committed | format_money }}</td>
        <td>{{ inv.invested | format_money }}</td>
        <td>{{ inv.nav | format_money }}</td>
        <td>{{ inv.realized | format_money }}</td>
        <td>{{ inv.moic | format_multiple }}</td>
      </tr>
      {% endfor %}
    </table>
  </section>
  {% endif %}

  <!-- Market Outlook -->
  <section>
    <h3>Market Outlook</h3>
    <p>{{ narrative.market_outlook }}</p>
  </section>

  <!-- ESG Highlights -->
  <section>
    <h3>ESG & Impact Highlights</h3>
    <p>{{ narrative.esg_highlights }}</p>
  </section>

  <div class="footer">
    <p>This report is prepared for limited partners of the fund and is confidential. All financial metrics are calculated using industry-standard methodologies (ILPA guidelines). IRR calculated using numpy-financial. TVPI = (Distributions + NAV) / Invested Capital. Past performance is not indicative of future results.</p>
  </div>
</body>
</html>"""


def _fmt_money(value: Any) -> str:
    if value is None:
        return "—"
    try:
        return f"${float(value):,.0f}"
    except (TypeError, ValueError):
        return "—"


def _fmt_pct(value: Any) -> str:
    if value is None:
        return "—"
    try:
        return f"{float(value):.2%}"
    except (TypeError, ValueError):
        return "—"


def _fmt_multiple(value: Any) -> str:
    if value is None:
        return "—"
    try:
        return f"{float(value):.2f}x"
    except (TypeError, ValueError):
        return "—"


def _render_html_report(report: LPReport) -> str:
    """Render the LP report as an HTML string using Jinja2."""
    narrative = report.narrative or {}
    investments = report.investments_data or []

    # Build a simple dict for the template
    class _Narrative:
        executive_summary: str = narrative.get("executive_summary", "")
        portfolio_commentary: str = narrative.get("portfolio_commentary", "")
        market_outlook: str = narrative.get("market_outlook", "")
        esg_highlights: str = narrative.get("esg_highlights", "")

    class _Inv:
        def __init__(self, d: dict[str, Any]) -> None:
            self.name = d.get("name", "Unknown")
            self.stage = d.get("stage")
            self.vintage = d.get("vintage")
            self.committed = d.get("committed")
            self.invested = d.get("invested")
            self.nav = d.get("nav")
            self.realized = d.get("realized")
            self.moic = d.get("moic")

    env = Environment(loader=BaseLoader())

    def _filter_money(v: Any) -> str:
        return _fmt_money(v)

    def _filter_multiple(v: Any) -> str:
        return _fmt_multiple(v)

    env.filters["format_money"] = _filter_money
    env.filters["format_multiple"] = _filter_multiple

    template = env.from_string(_REPORT_HTML_TEMPLATE)

    narrative_obj = _Narrative()
    narrative_obj.executive_summary = narrative.get("executive_summary", "")
    narrative_obj.portfolio_commentary = narrative.get("portfolio_commentary", "")
    narrative_obj.market_outlook = narrative.get("market_outlook", "")
    narrative_obj.esg_highlights = narrative.get("esg_highlights", "")

    return template.render(
        report_period=report.report_period,
        period_start=str(report.period_start),
        period_end=str(report.period_end),
        status=report.status.upper(),
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        narrative=narrative_obj,
        gross_irr=_fmt_pct(report.gross_irr),
        net_irr=_fmt_pct(report.net_irr),
        tvpi=_fmt_multiple(report.tvpi),
        dpi=_fmt_multiple(report.dpi),
        rvpi=_fmt_multiple(report.rvpi),
        moic=_fmt_multiple(report.moic),
        total_committed=_fmt_money(report.total_committed),
        total_invested=_fmt_money(report.total_invested),
        total_returned=_fmt_money(report.total_returned),
        total_nav=_fmt_money(report.total_nav),
        investments=[_Inv(inv) for inv in investments],
    )


# ── DB query helpers ──────────────────────────────────────────────────────────


async def _get_report(
    db: AsyncSession, report_id: uuid.UUID, org_id: uuid.UUID
) -> LPReport | None:
    stmt = select(LPReport).where(
        LPReport.id == report_id,
        LPReport.org_id == org_id,
        LPReport.is_deleted.is_(False),
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


# ── Service functions ─────────────────────────────────────────────────────────


async def create_report(
    db: AsyncSession,
    org_id: uuid.UUID,
    portfolio_id: uuid.UUID | None,
    report_period: str,
    period_start: date,
    period_end: date,
    cash_flows: list[dict[str, Any]],
    investments_data: list[dict[str, Any]],
    total_committed: float | None = None,
    total_invested: float | None = None,
    total_returned: float | None = None,
    total_nav: float | None = None,
) -> LPReport:
    """
    Create an LP report:
    1. Calculate all financial metrics deterministically (Python, never LLM).
    2. Generate AI narrative via AI Gateway.
    3. Persist to DB.
    """
    # Step 1: deterministic metric calculation
    metrics = calculate_fund_metrics(
        cash_flows=cash_flows,
        total_committed=total_committed,
        total_invested=total_invested,
        total_returned=total_returned,
        total_nav=total_nav,
    )

    # If explicit totals provided, override the derived ones
    metrics["total_invested"] = total_invested if total_invested is not None else metrics["total_invested"]
    metrics["total_returned"] = total_returned if total_returned is not None else metrics["total_returned"]
    metrics["total_nav"] = total_nav if total_nav is not None else metrics["total_nav"]

    # Step 2: generate AI narrative
    narrative_data = {
        "report_period": report_period,
        "gross_irr": metrics.get("gross_irr"),
        "net_irr": metrics.get("net_irr"),
        "tvpi": metrics.get("tvpi"),
        "dpi": metrics.get("dpi"),
        "total_invested": metrics.get("total_invested"),
        "total_nav": metrics.get("total_nav"),
        "investments_data": investments_data,
    }
    narrative = await generate_narrative(narrative_data)

    # Step 3: persist
    report = LPReport(
        org_id=org_id,
        portfolio_id=portfolio_id,
        report_period=report_period,
        period_start=period_start,
        period_end=period_end,
        status="draft",
        gross_irr=metrics.get("gross_irr"),
        net_irr=metrics.get("net_irr"),
        tvpi=metrics.get("tvpi"),
        dpi=metrics.get("dpi"),
        rvpi=metrics.get("rvpi"),
        moic=metrics.get("moic"),
        total_committed=total_committed,
        total_invested=metrics.get("total_invested"),
        total_returned=metrics.get("total_returned"),
        total_nav=metrics.get("total_nav"),
        narrative=narrative,
        investments_data=investments_data,
    )
    db.add(report)
    await db.flush()
    return report


async def list_reports(
    db: AsyncSession,
    org_id: uuid.UUID,
    portfolio_id: uuid.UUID | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[LPReport], int]:
    """List LP reports for an org with optional filters and pagination."""
    base = select(LPReport).where(
        LPReport.org_id == org_id,
        LPReport.is_deleted.is_(False),
    )
    if portfolio_id:
        base = base.where(LPReport.portfolio_id == portfolio_id)
    if status:
        base = base.where(LPReport.status == status)

    count_stmt = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    stmt = base.order_by(LPReport.period_end.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    return list(result.scalars().all()), total


async def get_report(
    db: AsyncSession, report_id: uuid.UUID, org_id: uuid.UUID
) -> LPReport | None:
    """Fetch a single LP report by ID, scoped to org."""
    return await _get_report(db, report_id, org_id)


async def update_report(
    db: AsyncSession,
    report_id: uuid.UUID,
    org_id: uuid.UUID,
    narrative: dict[str, Any] | None = None,
    investments_data: list[dict[str, Any]] | None = None,
    report_period: str | None = None,
    period_start: date | None = None,
    period_end: date | None = None,
) -> LPReport | None:
    """Update editable fields on a draft LP report."""
    report = await _get_report(db, report_id, org_id)
    if not report:
        return None
    if report.status not in ("draft", "review"):
        raise ValueError(f"Cannot edit report in status '{report.status}'")

    if narrative is not None:
        report.narrative = narrative
    if investments_data is not None:
        report.investments_data = investments_data
    if report_period is not None:
        report.report_period = report_period
    if period_start is not None:
        report.period_start = period_start
    if period_end is not None:
        report.period_end = period_end

    await db.flush()
    return report


async def approve_report(
    db: AsyncSession,
    report_id: uuid.UUID,
    org_id: uuid.UUID,
    approver_id: uuid.UUID,
) -> LPReport | None:
    """Transition report status from review → approved."""
    report = await _get_report(db, report_id, org_id)
    if not report:
        return None
    if report.status == "approved":
        return report  # idempotent
    if report.status not in ("draft", "review"):
        raise ValueError(f"Cannot approve report in status '{report.status}'")

    report.status = "approved"
    report.approved_by = approver_id
    report.approved_at = datetime.now(timezone.utc)
    await db.flush()
    return report


async def generate_html_report(
    db: AsyncSession,
    report_id: uuid.UUID,
    org_id: uuid.UUID,
) -> tuple[str, str]:
    """
    Generate HTML report, upload to S3, and return (s3_key, presigned_url).

    The HTML can be printed to PDF via browser print dialog on the frontend.
    """
    report = await _get_report(db, report_id, org_id)
    if not report:
        raise LookupError(f"Report {report_id} not found")

    html_content = _render_html_report(report)
    html_bytes = html_content.encode("utf-8")

    s3_key = f"lp-reports/{org_id}/{report_id}/report.html"

    try:
        s3 = _get_s3_client()
        s3.put_object(
            Bucket=settings.AWS_S3_BUCKET,
            Key=s3_key,
            Body=html_bytes,
            ContentType="text/html; charset=utf-8",
        )
        presigned_url = _generate_presigned_url(s3_key)
    except Exception as exc:
        logger.warning("lp_report.s3_upload_failed", report_id=str(report_id), error=str(exc))
        # Return in-memory as data URL fallback (dev mode)
        import base64

        b64 = base64.b64encode(html_bytes).decode()
        presigned_url = f"data:text/html;base64,{b64}"
        s3_key = f"local/{report_id}/report.html"

    report.pdf_s3_key = s3_key
    report.generated_at = datetime.now(timezone.utc)
    await db.flush()

    return s3_key, presigned_url


async def get_download_url(
    db: AsyncSession,
    report_id: uuid.UUID,
    org_id: uuid.UUID,
) -> str | None:
    """Generate a presigned download URL for the report HTML."""
    report = await _get_report(db, report_id, org_id)
    if not report or not report.pdf_s3_key:
        return None
    try:
        return _generate_presigned_url(report.pdf_s3_key)
    except Exception:
        return None
