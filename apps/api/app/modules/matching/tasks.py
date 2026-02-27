"""Celery tasks for Matching: batch daily refresh of all match scores."""

import uuid

import structlog
from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

logger = structlog.get_logger()

celery_app = Celery("matching", broker=settings.CELERY_BROKER_URL)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

# Daily at 02:00 UTC
celery_app.conf.beat_schedule = {
    "batch-match-refresh": {
        "task": "app.modules.matching.tasks.batch_calculate_matches",
        "schedule": crontab(hour=2, minute=0),
    }
}


@celery_app.task(bind=True, max_retries=2, default_retry_delay=60)
def batch_calculate_matches(self) -> dict:
    """
    Daily batch task: refresh MatchResult scores for all active pairings.

    Steps:
      1. Load all published projects
      2. Load all active InvestorMandates
      3. For each (project, mandate) pair:
         a. Score with MatchingAlgorithm
         b. Upsert MatchResult (create if new, update score_breakdown if score changed)
      4. Only create SUGGESTED records — never downgrade existing status
    """
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session as SyncSession

    from app.models.enums import MatchInitiator, MatchStatus
    from app.models.investors import InvestorMandate
    from app.models.matching import MatchResult
    from app.models.projects import Project, SignalScore
    from app.modules.matching.algorithm import MatchingAlgorithm

    engine = create_engine(settings.DATABASE_URL_SYNC)
    algo = MatchingAlgorithm()

    created = 0
    updated = 0
    errors = 0

    try:
        with SyncSession(engine) as session:
            # Load all published projects
            projects = session.execute(
                select(Project).where(
                    Project.is_published.is_(True),
                    Project.is_deleted.is_(False),
                )
            ).scalars().all()

            # Load all active mandates
            mandates = session.execute(
                select(InvestorMandate).where(
                    InvestorMandate.is_active.is_(True),
                    InvestorMandate.is_deleted.is_(False),
                )
            ).scalars().all()

            logger.info(
                "batch_match_start",
                project_count=len(projects),
                mandate_count=len(mandates),
            )

            # Load latest signal scores for all projects
            signal_scores: dict[uuid.UUID, SignalScore] = {}
            for proj in projects:
                ss = session.execute(
                    select(SignalScore)
                    .where(SignalScore.project_id == proj.id)
                    .order_by(SignalScore.version.desc())
                    .limit(1)
                ).scalar_one_or_none()
                if ss:
                    signal_scores[proj.id] = ss

            # Build existing match lookup
            existing = session.execute(
                select(MatchResult).where(MatchResult.is_deleted.is_(False))
            ).scalars().all()
            existing_map: dict[tuple[uuid.UUID, uuid.UUID], MatchResult] = {
                (m.project_id, m.investor_org_id): m for m in existing
            }

            for mandate in mandates:
                for project in projects:
                    # Skip if same org (ally investing in own project)
                    if mandate.org_id == project.org_id:
                        continue

                    try:
                        ss = signal_scores.get(project.id)
                        alignment = algo.calculate_alignment(mandate, project, ss)

                        # Only create/update for meaningful scores (≥20)
                        if alignment.overall < 20:
                            continue

                        key = (project.id, mandate.org_id)
                        existing_match = existing_map.get(key)

                        if existing_match:
                            # Update score breakdown but never downgrade status
                            existing_match.overall_score = alignment.overall
                            existing_match.score_breakdown = alignment.to_dict()
                            existing_match.mandate_id = mandate.id
                            updated += 1
                        else:
                            # Create new SUGGESTED match
                            new_match = MatchResult(
                                investor_org_id=mandate.org_id,
                                ally_org_id=project.org_id,
                                project_id=project.id,
                                mandate_id=mandate.id,
                                overall_score=alignment.overall,
                                score_breakdown=alignment.to_dict(),
                                status=MatchStatus.SUGGESTED,
                                initiated_by=MatchInitiator.SYSTEM,
                            )
                            session.add(new_match)
                            created += 1

                    except Exception as pair_exc:
                        errors += 1
                        logger.warning(
                            "batch_match_pair_error",
                            project_id=str(project.id),
                            mandate_id=str(mandate.id),
                            error=str(pair_exc),
                        )

            session.commit()

        logger.info(
            "batch_match_complete",
            created=created,
            updated=updated,
            errors=errors,
        )
        return {"status": "success", "created": created, "updated": updated, "errors": errors}

    except Exception as exc:
        logger.error("batch_match_failed", error=str(exc))
        raise self.retry(exc=exc)
