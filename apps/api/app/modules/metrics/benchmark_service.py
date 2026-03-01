"""BenchmarkService — computes and queries peer benchmark statistics."""

import csv
import uuid
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.metrics import BenchmarkAggregate, MetricSnapshot
from app.models.projects import Project

logger = structlog.get_logger()

BENCHMARK_METRICS = ["signal_score", "irr", "moic", "nav", "risk_score", "esg_score", "enterprise_value"]


class BenchmarkService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Benchmark computation ─────────────────────────────────────────────────

    async def compute_benchmarks(self) -> dict[str, int]:
        """Nightly task. Aggregates all metric snapshots into benchmark stats."""
        try:
            import statistics
        except ImportError:
            return {"error": "statistics module unavailable"}

        # Get all projects
        projects_result = await self.db.execute(
            select(Project.id, Project.project_type, Project.geography_country, Project.stage)
            .where(Project.is_deleted.is_(False))
        )
        projects = projects_result.all()

        rows_written = 0
        import datetime as _dt
        period = _dt.date.today().strftime("%Y-%m")

        for metric_name in BENCHMARK_METRICS:
            # Collect latest value per project
            project_values: dict[str, list[tuple[str, str | None, str | None, float]]] = {}
            for proj_id, proj_type, geography, stage in projects:
                latest_result = await self.db.execute(
                    select(MetricSnapshot.value)
                    .where(
                        MetricSnapshot.entity_type == "project",
                        MetricSnapshot.entity_id == proj_id,
                        MetricSnapshot.metric_name == metric_name,
                    )
                    .order_by(MetricSnapshot.recorded_at.desc())
                    .limit(1)
                )
                val = latest_result.scalar_one_or_none()
                if val is None:
                    continue
                key = (
                    proj_type.value if hasattr(proj_type, "value") else str(proj_type or "other"),
                    geography,
                    stage.value if hasattr(stage, "value") else str(stage or ""),
                )
                if key not in project_values:
                    project_values[key] = []
                project_values[key].append(val)

            # Compute stats per group
            for (asset_class, geography, stage), values in project_values.items():
                if not values:
                    continue
                stats = self._compute_stats(values, statistics)
                await self._upsert_benchmark(
                    asset_class=asset_class,
                    geography=geography,
                    stage=stage,
                    vintage_year=None,
                    metric_name=metric_name,
                    period=period,
                    stats={**stats, "count": len(values)},
                )
                rows_written += 1

        await self.db.commit()
        return {"rows_written": rows_written, "period": period}

    def _compute_stats(self, values: list[float], statistics_module) -> dict[str, float | None]:
        if not values:
            return {}
        sorted_vals = sorted(values)
        n = len(sorted_vals)

        def _percentile(p: float) -> float:
            idx = (p / 100) * (n - 1)
            lo, hi = int(idx), min(int(idx) + 1, n - 1)
            return sorted_vals[lo] + (idx - lo) * (sorted_vals[hi] - sorted_vals[lo])

        return {
            "mean": statistics_module.mean(values),
            "median": statistics_module.median(values),
            "p25": _percentile(25),
            "p75": _percentile(75),
            "p10": _percentile(10),
            "p90": _percentile(90),
            "std_dev": statistics_module.stdev(values) if n > 1 else None,
            "min_val": min(values),
            "max_val": max(values),
        }

    async def _upsert_benchmark(
        self, asset_class: str, geography: str | None, stage: str | None,
        vintage_year: int | None, metric_name: str, period: str, stats: dict
    ) -> None:
        stmt = (
            pg_insert(BenchmarkAggregate)
            .values(
                asset_class=asset_class,
                geography=geography,
                stage=stage,
                vintage_year=vintage_year,
                metric_name=metric_name,
                period=period,
                count=stats.get("count", 0),
                mean=stats.get("mean"),
                median=stats.get("median"),
                p25=stats.get("p25"),
                p75=stats.get("p75"),
                p10=stats.get("p10"),
                p90=stats.get("p90"),
                std_dev=stats.get("std_dev"),
                min_val=stats.get("min_val"),
                max_val=stats.get("max_val"),
            )
            .on_conflict_do_update(
                constraint="uq_benchmark_aggregate",
                set_={
                    "count": stats.get("count", 0),
                    "mean": stats.get("mean"),
                    "median": stats.get("median"),
                    "p25": stats.get("p25"),
                    "p75": stats.get("p75"),
                    "p10": stats.get("p10"),
                    "p90": stats.get("p90"),
                    "std_dev": stats.get("std_dev"),
                    "min_val": stats.get("min_val"),
                    "max_val": stats.get("max_val"),
                },
            )
        )
        await self.db.execute(stmt)

    # ── Comparison ────────────────────────────────────────────────────────────

    async def compare_to_benchmark(
        self, project_id: uuid.UUID, org_id: uuid.UUID, metric_names: list[str] | None = None
    ) -> dict[str, Any]:
        """Compare a project to its peer group benchmark."""
        proj_result = await self.db.execute(
            select(Project).where(Project.id == project_id, Project.is_deleted.is_(False))
        )
        project = proj_result.scalar_one_or_none()
        if not project:
            raise LookupError(f"Project {project_id} not found")

        metrics = metric_names or ["signal_score", "irr", "moic"]
        asset_class = project.project_type.value if project.project_type else "other"
        geography = project.geography_country
        stage = project.stage.value if project.stage else None

        comparisons = {}
        from app.modules.metrics.snapshot_service import MetricSnapshotService
        snapshot_svc = MetricSnapshotService(self.db)

        for m in metrics:
            latest = await snapshot_svc._get_latest("project", project_id, m)
            if not latest:
                continue
            benchmark = await self._find_best_benchmark(asset_class, geography, stage, m)
            if not benchmark:
                continue
            percentile = self._calc_percentile(latest.value, benchmark)
            comparisons[m] = {
                "value": latest.value,
                "peer_group": f"{benchmark.asset_class} / {benchmark.geography or 'Global'}",
                "peer_count": benchmark.count,
                "percentile": percentile,
                "quartile": self._calc_quartile(latest.value, benchmark),
                "vs_median": round(latest.value - benchmark.median, 2) if benchmark.median else None,
                "benchmark": {
                    "p25": benchmark.p25, "p50": benchmark.median,
                    "p75": benchmark.p75, "mean": benchmark.mean,
                    "p10": benchmark.p10, "p90": benchmark.p90,
                },
            }
        return {"project_id": str(project_id), "comparisons": comparisons, "asset_class": asset_class}

    async def _find_best_benchmark(
        self, asset_class: str, geography: str | None, stage: str | None, metric_name: str
    ) -> BenchmarkAggregate | None:
        """Try exact → no stage → no geo → no geo/stage."""
        for geo in [geography, None]:
            for stg in [stage, None]:
                result = await self.db.execute(
                    select(BenchmarkAggregate)
                    .where(
                        BenchmarkAggregate.asset_class == asset_class,
                        BenchmarkAggregate.geography == geo,
                        BenchmarkAggregate.stage == stg,
                        BenchmarkAggregate.metric_name == metric_name,
                    )
                    .order_by(BenchmarkAggregate.computed_at.desc())
                    .limit(1)
                )
                b = result.scalar_one_or_none()
                if b and b.count >= 3:
                    return b
        return None

    def _calc_percentile(self, value: float, benchmark: BenchmarkAggregate) -> float | None:
        if benchmark.p25 is None or benchmark.p75 is None or benchmark.median is None:
            return None
        if value <= benchmark.p25:
            return round((value / benchmark.p25) * 25, 1) if benchmark.p25 else 0.0
        elif value <= benchmark.median:
            span = benchmark.median - benchmark.p25
            return round(25 + ((value - benchmark.p25) / span * 25), 1) if span else 50.0
        elif value <= benchmark.p75:
            span = benchmark.p75 - benchmark.median
            return round(50 + ((value - benchmark.median) / span * 25), 1) if span else 75.0
        else:
            return min(99.0, round(75 + ((value - benchmark.p75) / max(benchmark.p75, 1)) * 25, 1))

    def _calc_quartile(self, value: float, benchmark: BenchmarkAggregate) -> int | None:
        if benchmark.p25 is None or benchmark.median is None or benchmark.p75 is None:
            return None
        if value < benchmark.p25:
            return 1
        elif value < benchmark.median:
            return 2
        elif value < benchmark.p75:
            return 3
        else:
            return 4

    async def list_benchmarks(self) -> list[BenchmarkAggregate]:
        result = await self.db.execute(
            select(BenchmarkAggregate).order_by(
                BenchmarkAggregate.asset_class,
                BenchmarkAggregate.metric_name,
                BenchmarkAggregate.computed_at.desc(),
            )
        )
        return list(result.scalars().all())

    # ── B02: External import + cashflow pacing ────────────────────────────────

    async def import_external_benchmarks(self, csv_content: str, source: str) -> dict[str, int]:
        """Import benchmark data from CSV content (e.g., Preqin, Cambridge Associates export).
        Format: asset_class, geography, vintage_year, metric, p25, p50, p75, mean, count"""
        import io
        reader = csv.DictReader(io.StringIO(csv_content))
        imported = 0
        for row in reader:
            try:
                stats = {}
                for k in ["p25", "p75", "mean", "count"]:
                    if row.get(k):
                        stats[k] = float(row[k])
                if row.get("p50"):
                    stats["median"] = float(row["p50"])
                vy = int(row["vintage_year"]) if row.get("vintage_year") else None
                await self._upsert_benchmark(
                    asset_class=row["asset_class"],
                    geography=row.get("geography"),
                    stage=row.get("stage"),
                    vintage_year=vy,
                    metric_name=row["metric"],
                    period=row.get("period", "annual"),
                    stats=stats,
                )
                imported += 1
            except (KeyError, ValueError) as exc:
                logger.warning("benchmark_import_row_error", error=str(exc), row=row)
        await self.db.commit()
        return {"imported": imported, "source": source}

    async def get_cashflow_pacing(
        self, portfolio_id: uuid.UUID, org_id: uuid.UUID, scenario: str = "base"
    ) -> list[dict]:
        """J-curve and cashflow pacing model for portfolio (10-year projection)."""
        from app.models.investors import PortfolioHolding
        holdings_result = await self.db.execute(
            select(PortfolioHolding).where(
                PortfolioHolding.portfolio_id == portfolio_id,
            )
        )
        holdings = list(holdings_result.scalars().all())

        projections = []
        for month in range(1, 121):  # 10-year projection
            contributions = sum(self._pacing_draw(h, month, scenario) for h in holdings)
            distributions = sum(self._pacing_dist(h, month, scenario) for h in holdings)
            nav = sum(self._pacing_nav(h, month, scenario) for h in holdings)
            projections.append({
                "month": month,
                "contributions": round(contributions, 2),
                "distributions": round(distributions, 2),
                "nav": round(nav, 2),
                "net_cashflow": round(distributions - contributions, 2),
            })
        return projections

    def _pacing_draw(self, holding, month: int, scenario: str) -> float:
        """Typical drawdown schedule per asset class."""
        PACING = {
            "solar": [0.3, 0.3, 0.2, 0.1, 0.1],
            "wind": [0.2, 0.3, 0.25, 0.15, 0.1],
            "real_estate": [0.4, 0.3, 0.2, 0.1],
            "infrastructure": [0.2, 0.2, 0.2, 0.2, 0.1, 0.1],
            "_default": [0.25, 0.25, 0.2, 0.15, 0.15],
        }
        scalar = {"base": 1.0, "optimistic": 0.9, "pessimistic": 1.15}.get(scenario, 1.0)
        year = (month - 1) // 12
        committed = float(holding.investment_amount or 0)
        proj_type = ""
        if hasattr(holding, "project") and holding.project:
            pt = getattr(holding.project, "project_type", None)
            proj_type = pt.value if hasattr(pt, "value") else str(pt or "")
        schedule = PACING.get(proj_type, PACING["_default"])
        if year < len(schedule):
            return committed * schedule[year] / 12 * scalar
        return 0.0

    def _pacing_dist(self, holding, month: int, scenario: str) -> float:
        """Simplified distribution schedule: starts year 4, peaks year 7-8."""
        committed = float(holding.investment_amount or 0)
        scalar = {"base": 1.0, "optimistic": 1.2, "pessimistic": 0.8}.get(scenario, 1.0)
        year = (month - 1) // 12
        dist_schedule = [0, 0, 0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.15, 0.1]
        if year < len(dist_schedule):
            return committed * dist_schedule[year] / 12 * scalar
        return committed * 0.05 / 12 * scalar

    def _pacing_nav(self, holding, month: int, scenario: str) -> float:
        """Simplified NAV: grows for first 5 years, then declines as distributions flow."""
        committed = float(holding.investment_amount or 0)
        scalar = {"base": 1.0, "optimistic": 1.3, "pessimistic": 0.75}.get(scenario, 1.0)
        year = (month - 1) // 12
        nav_mult = [0.3, 0.6, 0.85, 1.0, 1.1, 1.15, 1.1, 1.0, 0.8, 0.5]
        if year < len(nav_mult):
            return committed * nav_mult[year] * scalar
        return committed * 0.3 * scalar

    async def get_quartile_chart_data(
        self, project_id: uuid.UUID, org_id: uuid.UUID
    ) -> list[dict]:
        """Return data for a quartile position chart across all benchmark metrics."""
        comparison = await self.compare_to_benchmark(project_id, org_id, BENCHMARK_METRICS)
        result = []
        for metric_name, comp in comparison.get("comparisons", {}).items():
            result.append({
                "metric_name": metric_name,
                "value": comp["value"],
                "p10": comp["benchmark"].get("p10"),
                "p25": comp["benchmark"].get("p25"),
                "p50": comp["benchmark"].get("p50"),
                "p75": comp["benchmark"].get("p75"),
                "p90": comp["benchmark"].get("p90"),
                "percentile": comp.get("percentile"),
                "quartile": comp.get("quartile"),
            })
        return result
