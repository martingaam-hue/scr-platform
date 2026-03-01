"""Nightly Celery tasks for benchmark computation and daily metric snapshots."""

import uuid

import structlog
from celery import shared_task

from app.core.config import settings

logger = structlog.get_logger()


@shared_task(name="tasks.compute_nightly_benchmarks")
def compute_nightly_benchmarks() -> dict:
    """Run at 3am daily. Aggregates all snapshots into benchmark stats."""
    import asyncio
    from sqlalchemy import create_engine
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker

    async def _run():
        from app.core.database import async_session_factory
        from app.modules.metrics.benchmark_service import BenchmarkService
        async with async_session_factory() as db:
            svc = BenchmarkService(db)
            return await svc.compute_benchmarks()

    result = asyncio.run(_run())
    logger.info("nightly_benchmarks_computed", **result)
    return result


@shared_task(name="tasks.record_daily_snapshots")
def record_daily_snapshots() -> dict:
    """Run at 2am daily. Snapshot current values for all active projects/portfolios."""
    import asyncio

    async def _run():
        from app.core.database import async_session_factory
        from app.models.projects import Project, SignalScore
        from app.models.investors import Portfolio, PortfolioMetrics
        from app.modules.metrics.snapshot_service import MetricSnapshotService
        from sqlalchemy import select

        snapshots_recorded = 0

        async with async_session_factory() as db:
            svc = MetricSnapshotService(db)

            # Snapshot latest signal scores for active projects
            scores_result = await db.execute(
                select(SignalScore, Project.org_id)
                .join(Project, Project.id == SignalScore.project_id)
                .where(Project.is_deleted.is_(False))
                .distinct(SignalScore.project_id)
                .order_by(SignalScore.project_id, SignalScore.version.desc())
            )
            for score, org_id in scores_result.all():
                try:
                    await svc.record_snapshot(
                        org_id=org_id,
                        entity_type="project",
                        entity_id=score.project_id,
                        metric_name="signal_score",
                        value=float(score.overall_score),
                        metadata={
                            "dimensions": {
                                "project_viability": score.project_viability_score,
                                "financial_planning": score.financial_planning_score,
                                "team_strength": score.team_strength_score,
                                "risk_assessment": score.risk_assessment_score,
                                "esg": score.esg_score,
                            },
                            "version": score.version,
                        },
                        trigger_event="daily_snapshot",
                    )
                    snapshots_recorded += 1
                except Exception as exc:
                    logger.warning("daily_snapshot_failed", error=str(exc))

            await db.commit()

        return {"snapshots_recorded": snapshots_recorded}

    result = asyncio.run(_run())
    logger.info("daily_snapshots_recorded", **result)
    return result
