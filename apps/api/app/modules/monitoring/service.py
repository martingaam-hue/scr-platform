"""Covenant & KPI Monitoring service."""

from __future__ import annotations

import uuid
from datetime import datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.monitoring import Covenant, KPIActual, KPITarget
from app.modules.monitoring.schemas import (
    CovenantCreate,
    CovenantUpdate,
    KPIActualCreate,
    KPITargetCreate,
    KPIVarianceItem,
)

logger = structlog.get_logger()


class MonitoringService:
    def __init__(self, db: AsyncSession, org_id: uuid.UUID) -> None:
        self.db = db
        self.org_id = org_id

    # ── Covenants ─────────────────────────────────────────────────────────────

    async def create_covenant(
        self, project_id: uuid.UUID, body: CovenantCreate
    ) -> Covenant:
        covenant = Covenant(
            org_id=self.org_id,
            project_id=project_id,
            portfolio_id=body.portfolio_id,
            name=body.name,
            description=body.description,
            covenant_type=body.covenant_type,
            metric_name=body.metric_name,
            threshold_value=body.threshold_value,
            comparison=body.comparison,
            threshold_upper=body.threshold_upper,
            warning_threshold_pct=body.warning_threshold_pct,
            check_frequency=body.check_frequency,
            source_document_id=body.source_document_id,
        )
        self.db.add(covenant)
        await self.db.flush()
        await self.db.refresh(covenant)
        return covenant

    async def list_covenants(self, project_id: uuid.UUID) -> list[Covenant]:
        stmt = (
            select(Covenant)
            .where(
                Covenant.org_id == self.org_id,
                Covenant.project_id == project_id,
                Covenant.is_deleted.is_(False),
                Covenant.status != "waived",
            )
            .order_by(Covenant.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_covenant(
        self, covenant_id: uuid.UUID, body: CovenantUpdate
    ) -> Covenant:
        result = await self.db.execute(
            select(Covenant).where(
                Covenant.id == covenant_id,
                Covenant.org_id == self.org_id,
                Covenant.is_deleted.is_(False),
            )
        )
        covenant = result.scalar_one_or_none()
        if not covenant:
            raise LookupError(f"Covenant {covenant_id} not found")
        if body.name is not None:
            covenant.name = body.name
        if body.threshold_value is not None:
            covenant.threshold_value = body.threshold_value
        if body.status is not None:
            covenant.status = body.status
        if body.check_frequency is not None:
            covenant.check_frequency = body.check_frequency
        await self.db.flush()
        await self.db.refresh(covenant)
        return covenant

    async def waive_covenant(
        self,
        covenant_id: uuid.UUID,
        waived_by: uuid.UUID,
        reason: str,
    ) -> Covenant:
        result = await self.db.execute(
            select(Covenant).where(
                Covenant.id == covenant_id,
                Covenant.org_id == self.org_id,
                Covenant.is_deleted.is_(False),
            )
        )
        covenant = result.scalar_one_or_none()
        if not covenant:
            raise LookupError(f"Covenant {covenant_id} not found")
        covenant.status = "waived"
        covenant.waived_by = waived_by
        covenant.waived_reason = reason
        await self.db.flush()
        await self.db.refresh(covenant)
        return covenant

    async def check_covenants(
        self, project_id: uuid.UUID | None = None
    ) -> list[dict]:
        """Check all non-waived covenants. Returns list of status changes."""
        stmt = select(Covenant).where(
            Covenant.org_id == self.org_id,
            Covenant.is_deleted.is_(False),
            Covenant.status != "waived",
        )
        if project_id is not None:
            stmt = stmt.where(Covenant.project_id == project_id)

        result = await self.db.execute(stmt)
        covenants = list(result.scalars().all())

        changes: list[dict] = []
        now = datetime.utcnow()

        for covenant in covenants:
            current = await self._get_current_value(covenant)
            if current is None:
                continue

            covenant.current_value = current
            covenant.last_checked_at = now
            old_status = covenant.status

            if self._is_breached(covenant, current):
                covenant.status = "breach"
                if old_status != "breach":
                    covenant.breach_date = now
            elif self._is_warning(covenant, current):
                covenant.status = "warning"
            else:
                covenant.status = "compliant"

            if covenant.status != old_status:
                changes.append(
                    {
                        "covenant_id": str(covenant.id),
                        "covenant_name": covenant.name,
                        "project_id": str(covenant.project_id),
                        "old_status": old_status,
                        "new_status": covenant.status,
                        "current_value": current,
                    }
                )

        await self.db.flush()
        return changes

    def _is_breached(self, covenant: Covenant, value: float) -> bool:
        """Check if value violates the covenant threshold."""
        comp = covenant.comparison
        t = covenant.threshold_value
        if comp == ">=":
            return value < t
        elif comp == "<=":
            return value > t
        elif comp == "==":
            return abs(value - t) > 0.001
        elif comp == "between":
            return value < t or value > covenant.threshold_upper
        elif comp == "not_null":
            return value is None
        return False

    def _is_warning(self, covenant: Covenant, value: float) -> bool:
        """Check if within warning_threshold_pct of breach."""
        t = covenant.threshold_value
        if t and t != 0:
            pct_from_threshold = abs(value - t) / abs(t)
            if pct_from_threshold < covenant.warning_threshold_pct:
                return not self._is_breached(covenant, value)
        return False

    async def _get_current_value(self, covenant: Covenant) -> float | None:
        """Get latest KPIActual for covenant.metric_name and covenant.project_id."""
        stmt = (
            select(KPIActual)
            .where(
                KPIActual.project_id == covenant.project_id,
                KPIActual.kpi_name == covenant.metric_name,
                KPIActual.org_id == self.org_id,
                KPIActual.is_deleted.is_(False),
            )
            .order_by(KPIActual.created_at.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        actual = result.scalar_one_or_none()
        return actual.value if actual else None

    # ── KPIs ──────────────────────────────────────────────────────────────────

    async def record_kpi_actual(
        self,
        project_id: uuid.UUID,
        body: KPIActualCreate,
        entered_by: uuid.UUID | None = None,
    ) -> KPIActual:
        actual = KPIActual(
            org_id=self.org_id,
            project_id=project_id,
            kpi_name=body.kpi_name,
            value=body.value,
            unit=body.unit,
            period=body.period,
            period_type=body.period_type,
            source=body.source,
            source_document_id=body.source_document_id,
            entered_by=entered_by,
        )
        self.db.add(actual)
        await self.db.flush()
        await self.db.refresh(actual)
        return actual

    async def set_kpi_target(
        self,
        project_id: uuid.UUID,
        body: KPITargetCreate,
    ) -> KPITarget:
        target = KPITarget(
            org_id=self.org_id,
            project_id=project_id,
            kpi_name=body.kpi_name,
            target_value=body.target_value,
            period=body.period,
            tolerance_pct=body.tolerance_pct,
            source=body.source,
        )
        self.db.add(target)
        await self.db.flush()
        await self.db.refresh(target)
        return target

    async def list_kpi_actuals(
        self,
        project_id: uuid.UUID,
        period: str | None = None,
    ) -> list[KPIActual]:
        stmt = select(KPIActual).where(
            KPIActual.org_id == self.org_id,
            KPIActual.project_id == project_id,
            KPIActual.is_deleted.is_(False),
        )
        if period is not None:
            stmt = stmt.where(KPIActual.period == period)
        stmt = stmt.order_by(KPIActual.period.desc(), KPIActual.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_kpi_variance(
        self,
        project_id: uuid.UUID,
        period: str | None = None,
    ) -> list[KPIVarianceItem]:
        # Load actuals
        actuals_stmt = select(KPIActual).where(
            KPIActual.org_id == self.org_id,
            KPIActual.project_id == project_id,
            KPIActual.is_deleted.is_(False),
        )
        if period is not None:
            actuals_stmt = actuals_stmt.where(KPIActual.period == period)
        actuals_result = await self.db.execute(
            actuals_stmt.order_by(KPIActual.created_at.desc())
        )
        actuals = actuals_result.scalars().all()

        # Load targets
        targets_stmt = select(KPITarget).where(
            KPITarget.org_id == self.org_id,
            KPITarget.project_id == project_id,
            KPITarget.is_deleted.is_(False),
        )
        if period is not None:
            targets_stmt = targets_stmt.where(KPITarget.period == period)
        targets_result = await self.db.execute(targets_stmt)
        targets = targets_result.scalars().all()

        # Build a lookup: (kpi_name, period) → target
        target_map: dict[tuple[str, str], KPITarget] = {}
        for t in targets:
            target_map[(t.kpi_name, t.period)] = t

        # De-duplicate actuals by kpi+period — use the most recent value
        seen: dict[tuple[str, str], KPIActual] = {}
        for a in actuals:
            key = (a.kpi_name, a.period)
            if key not in seen:
                seen[key] = a

        items: list[KPIVarianceItem] = []
        for (kpi_name, act_period), actual in seen.items():
            tgt = target_map.get((kpi_name, act_period))
            if tgt is None:
                continue

            target_value = tgt.target_value
            if target_value == 0:
                variance_pct = 0.0
            else:
                variance_pct = ((actual.value - target_value) / abs(target_value)) * 100

            tolerance = tgt.tolerance_pct * 100
            if abs(variance_pct) <= tolerance:
                status = "on_track"
            elif variance_pct > 0:
                status = "above"
            else:
                status = "below"

            items.append(
                KPIVarianceItem(
                    kpi=kpi_name,
                    actual=actual.value,
                    target=target_value,
                    variance_pct=round(variance_pct, 2),
                    status=status,
                    unit=actual.unit,
                )
            )

        return items

    async def get_kpi_trend(
        self, project_id: uuid.UUID, kpi_name: str
    ) -> list[dict]:
        """Load all KPIActuals for project + kpi_name, ordered by period."""
        stmt = (
            select(KPIActual)
            .where(
                KPIActual.org_id == self.org_id,
                KPIActual.project_id == project_id,
                KPIActual.kpi_name == kpi_name,
                KPIActual.is_deleted.is_(False),
            )
            .order_by(KPIActual.period.asc(), KPIActual.created_at.desc())
        )
        result = await self.db.execute(stmt)
        actuals = result.scalars().all()

        # De-duplicate by period — keep most recent per period
        seen: dict[str, KPIActual] = {}
        for a in actuals:
            if a.period not in seen:
                seen[a.period] = a

        return [
            {"period": a.period, "value": a.value, "unit": a.unit}
            for a in sorted(seen.values(), key=lambda x: x.period)
        ]

    async def get_portfolio_dashboard(
        self, portfolio_id: uuid.UUID
    ) -> list[dict]:
        """Load portfolio holdings and return per-project covenant status."""
        from app.models.investors import PortfolioHolding
        from app.models.projects import Project

        # Get project_ids for this portfolio
        holdings_result = await self.db.execute(
            select(PortfolioHolding).where(
                PortfolioHolding.portfolio_id == portfolio_id,
                PortfolioHolding.is_deleted.is_(False),
            )
        )
        holdings = holdings_result.scalars().all()

        project_ids = [h.project_id for h in holdings if h.project_id is not None]
        if not project_ids:
            return []

        # Load project names
        projects_result = await self.db.execute(
            select(Project).where(
                Project.id.in_(project_ids),
                Project.org_id == self.org_id,
                Project.is_deleted.is_(False),
            )
        )
        projects = {p.id: p for p in projects_result.scalars().all()}

        items = []
        for project_id in project_ids:
            project = projects.get(project_id)
            if not project:
                continue

            covenants_result = await self.db.execute(
                select(Covenant).where(
                    Covenant.org_id == self.org_id,
                    Covenant.project_id == project_id,
                    Covenant.is_deleted.is_(False),
                    Covenant.status != "waived",
                )
            )
            covenants = list(covenants_result.scalars().all())

            statuses = {c.status for c in covenants}
            if "breach" in statuses:
                overall_status = "breach"
            elif "warning" in statuses:
                overall_status = "warning"
            else:
                overall_status = "compliant"

            items.append(
                {
                    "project_id": project_id,
                    "project_name": project.name,
                    "covenants": covenants,
                    "overall_status": overall_status,
                }
            )

        return items

    async def auto_extract_kpis(
        self, document_id: uuid.UUID, project_id: uuid.UUID
    ) -> dict:
        """AI extracts KPIs from uploaded document."""
        import httpx

        from app.core.config import settings

        try:
            resp = httpx.post(
                f"{settings.AI_GATEWAY_URL}/v1/completions",
                json={
                    "task_type": "extract_kpis",
                    "messages": [
                        {
                            "role": "user",
                            "content": (
                                f"Extract all financial KPIs and their values from document "
                                f"{document_id}. Return as JSON list of objects with fields: "
                                f"name, value, unit, period."
                            ),
                        }
                    ],
                },
                headers={"X-API-Key": settings.AI_GATEWAY_API_KEY},
                timeout=30,
            )
            data = resp.json()
            kpis = data.get("result", {}).get("kpis", [])
            count = 0
            for kpi in kpis:
                if "name" in kpi and "value" in kpi:
                    actual = KPIActual(
                        org_id=self.org_id,
                        project_id=project_id,
                        kpi_name=kpi["name"],
                        value=float(kpi["value"]),
                        unit=kpi.get("unit"),
                        period=kpi.get("period", "unknown"),
                        source="document_extraction",
                        source_document_id=document_id,
                    )
                    self.db.add(actual)
                    count += 1
            await self.db.flush()
            return {"extracted": count}
        except Exception as e:
            logger.warning("auto_extract_kpis_failed", error=str(e))
            return {"extracted": 0, "error": str(e)}
