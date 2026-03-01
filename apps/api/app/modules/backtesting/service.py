"""Business logic for the Score Backtesting module."""

from __future__ import annotations

import math
import uuid
from datetime import date
from decimal import Decimal

import structlog
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.tenant import tenant_filter
from app.models.backtesting import BacktestRun, DealOutcome
from app.modules.backtesting.schemas import (
    BacktestRunRequest,
    BacktestSummaryResponse,
    RecordOutcomeRequest,
)

logger = structlog.get_logger()


class BacktestService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Outcome recording ────────────────────────────────────────────────────

    async def record_outcome(
        self,
        org_id: uuid.UUID,
        data: RecordOutcomeRequest,
    ) -> DealOutcome:
        """Persist a single deal outcome record."""
        outcome = DealOutcome(
            org_id=org_id,
            project_id=data.project_id,
            outcome_type=data.outcome_type,
            actual_irr=data.actual_irr,
            actual_moic=data.actual_moic,
            actual_revenue_eur=data.actual_revenue_eur,
            signal_score_at_evaluation=data.signal_score_at_evaluation,
            signal_score_at_decision=data.signal_score_at_decision,
            signal_dimensions_at_decision=data.signal_dimensions_at_decision,
            decision_date=data.decision_date,
            outcome_date=data.outcome_date,
            notes=data.notes,
        )
        self.db.add(outcome)
        await self.db.commit()
        await self.db.refresh(outcome)
        logger.info(
            "deal_outcome_recorded",
            org_id=str(org_id),
            outcome_id=str(outcome.id),
            outcome_type=data.outcome_type,
        )
        return outcome

    # ── Backtest execution ───────────────────────────────────────────────────

    async def run_backtest(
        self,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        data: BacktestRunRequest,
    ) -> BacktestRun:
        """Run a backtest over historical outcomes and persist the results."""
        # Fetch outcomes in date range for org
        stmt = select(DealOutcome).where(DealOutcome.org_id == org_id)
        if data.date_from:
            stmt = stmt.where(
                (DealOutcome.decision_date >= data.date_from)
                | (DealOutcome.outcome_date >= data.date_from)
            )
        if data.date_to:
            stmt = stmt.where(
                (DealOutcome.decision_date <= data.date_to)
                | (DealOutcome.outcome_date <= data.date_to)
            )
        result = await self.db.execute(stmt)
        outcomes = list(result.scalars().all())

        threshold = float(data.min_score_threshold) if data.min_score_threshold is not None else 50.0

        if data.methodology == "cohort":
            analysis = self._cohort_analysis(outcomes)
            # For cohort we still compute threshold metrics from the same data
            metrics = self._threshold_analysis(outcomes, threshold)
        else:
            # "threshold" and "time_series" both use threshold analysis
            metrics = self._threshold_analysis(outcomes, threshold)
            analysis = self._cohort_analysis(outcomes)

        results_payload = {
            "methodology": data.methodology,
            "threshold": threshold,
            "metrics": metrics,
            "cohort_analysis": analysis,
        }

        run = BacktestRun(
            org_id=org_id,
            run_by=user_id,
            methodology=data.methodology,
            date_from=data.date_from,
            date_to=data.date_to,
            min_score_threshold=data.min_score_threshold,
            accuracy=Decimal(str(round(metrics["accuracy"], 4))) if metrics["accuracy"] is not None else None,
            precision=Decimal(str(round(metrics["precision"], 4))) if metrics["precision"] is not None else None,
            recall=Decimal(str(round(metrics["recall"], 4))) if metrics["recall"] is not None else None,
            auc_roc=Decimal(str(round(metrics["auc_roc"], 4))) if metrics["auc_roc"] is not None else None,
            f1_score=Decimal(str(round(metrics["f1_score"], 4))) if metrics["f1_score"] is not None else None,
            sample_size=metrics["sample_size"],
            results=results_payload,
        )
        self.db.add(run)
        await self.db.commit()
        await self.db.refresh(run)
        logger.info(
            "backtest_run_completed",
            org_id=str(org_id),
            run_id=str(run.id),
            methodology=data.methodology,
            sample_size=metrics["sample_size"],
        )
        return run

    # ── Statistical helpers ──────────────────────────────────────────────────

    def _threshold_analysis(
        self,
        outcomes: list[DealOutcome],
        threshold: float,
    ) -> dict:
        """
        For each outcome with a score, classify as:
          predicted positive  = score >= threshold
          actual positive     = outcome_type in ("funded",)
        Then compute precision, recall, accuracy, F1, and a simple AUC-ROC
        approximation by sweeping thresholds.
        """
        # Only use outcomes that have a score at decision
        scoreable = [
            o for o in outcomes if o.signal_score_at_decision is not None
        ]
        n = len(scoreable)

        if n == 0:
            return {
                "accuracy": None,
                "precision": None,
                "recall": None,
                "f1_score": None,
                "auc_roc": None,
                "sample_size": 0,
                "tp": 0,
                "fp": 0,
                "tn": 0,
                "fn": 0,
                "calibration": [],
            }

        tp = fp = tn = fn = 0
        for o in scoreable:
            score = float(o.signal_score_at_decision)
            predicted_positive = score >= threshold
            actual_positive = o.outcome_type == "funded"
            if predicted_positive and actual_positive:
                tp += 1
            elif predicted_positive and not actual_positive:
                fp += 1
            elif not predicted_positive and not actual_positive:
                tn += 1
            else:
                fn += 1

        accuracy = (tp + tn) / n
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        )

        # AUC-ROC: sweep thresholds 0..100 by 5, compute trapezoid
        auc_roc = self._compute_auc_roc(scoreable)

        # Calibration: score buckets 0-19, 20-39, 40-59, 60-79, 80-100
        calibration = self._calibration_buckets(scoreable)

        return {
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1_score": f1,
            "auc_roc": auc_roc,
            "sample_size": n,
            "tp": tp,
            "fp": fp,
            "tn": tn,
            "fn": fn,
            "calibration": calibration,
        }

    def _compute_auc_roc(self, scoreable: list[DealOutcome]) -> float:
        """Compute AUC-ROC by sweeping thresholds and computing the trapezoid area."""
        thresholds = [t / 10.0 for t in range(0, 105, 5)]
        points: list[tuple[float, float]] = []

        total_pos = sum(1 for o in scoreable if o.outcome_type == "funded")
        total_neg = len(scoreable) - total_pos

        if total_pos == 0 or total_neg == 0:
            return 0.5

        for thr in thresholds:
            tp = fp = 0
            for o in scoreable:
                score = float(o.signal_score_at_decision)  # type: ignore[arg-type]
                predicted = score >= thr
                actual = o.outcome_type == "funded"
                if predicted and actual:
                    tp += 1
                elif predicted and not actual:
                    fp += 1
            tpr = tp / total_pos
            fpr = fp / total_neg
            points.append((fpr, tpr))

        # Sort by FPR ascending for trapezoidal rule
        points.sort(key=lambda p: p[0])

        auc = 0.0
        for i in range(1, len(points)):
            x0, y0 = points[i - 1]
            x1, y1 = points[i]
            auc += (x1 - x0) * (y0 + y1) / 2.0

        return round(abs(auc), 4)

    def _calibration_buckets(self, scoreable: list[DealOutcome]) -> list[dict]:
        """Group outcomes into score bands and compute actual funding rate per band."""
        bands = [
            ("0-19", 0, 20),
            ("20-39", 20, 40),
            ("40-59", 40, 60),
            ("60-79", 60, 80),
            ("80-100", 80, 101),
        ]
        result = []
        for label, low, high in bands:
            bucket = [
                o for o in scoreable
                if low <= float(o.signal_score_at_decision) < high  # type: ignore[arg-type]
            ]
            funded = sum(1 for o in bucket if o.outcome_type == "funded")
            result.append({
                "score_band": label,
                "count": len(bucket),
                "funded_count": funded,
                "funded_rate": round(funded / len(bucket), 3) if bucket else None,
            })
        return result

    def _cohort_analysis(self, outcomes: list[DealOutcome]) -> dict:
        """
        Group outcomes by score quartile and compute funded rate + avg IRR per quartile.
        """
        scoreable = [o for o in outcomes if o.signal_score_at_decision is not None]

        quartiles = [
            ("Q1 (0-25)", 0, 25),
            ("Q2 (25-50)", 25, 50),
            ("Q3 (50-75)", 50, 75),
            ("Q4 (75-100)", 75, 101),
        ]
        cohorts = []
        for label, low, high in quartiles:
            bucket = [
                o for o in scoreable
                if low <= float(o.signal_score_at_decision) < high  # type: ignore[arg-type]
            ]
            funded = [o for o in bucket if o.outcome_type == "funded"]
            irr_values = [
                float(o.actual_irr) for o in funded if o.actual_irr is not None
            ]
            avg_irr = round(sum(irr_values) / len(irr_values), 4) if irr_values else None
            cohorts.append({
                "quartile": label,
                "count": len(bucket),
                "funded_count": len(funded),
                "funded_rate": round(len(funded) / len(bucket), 3) if bucket else None,
                "avg_irr": avg_irr,
            })
        return {"quartiles": cohorts, "total_scored": len(scoreable)}

    # ── Query helpers ────────────────────────────────────────────────────────

    async def list_runs(self, org_id: uuid.UUID) -> list[BacktestRun]:
        """Return all backtest runs for org, ordered by created_at desc."""
        stmt = (
            select(BacktestRun)
            .where(BacktestRun.org_id == org_id)
            .order_by(BacktestRun.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_run(
        self,
        org_id: uuid.UUID,
        run_id: uuid.UUID,
    ) -> BacktestRun | None:
        """Get a single backtest run."""
        stmt = select(BacktestRun).where(
            BacktestRun.id == run_id,
            BacktestRun.org_id == org_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_outcomes(self, org_id: uuid.UUID) -> list[DealOutcome]:
        """Return all outcomes for org, ordered by created_at desc."""
        stmt = (
            select(DealOutcome)
            .where(DealOutcome.org_id == org_id)
            .order_by(DealOutcome.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_summary(self, org_id: uuid.UUID) -> BacktestSummaryResponse:
        """Compute org-level summary statistics."""
        outcomes = await self.list_outcomes(org_id)

        counts: dict[str, int] = {}
        for o in outcomes:
            counts[o.outcome_type] = counts.get(o.outcome_type, 0) + 1

        total = len(outcomes)
        funded_count = counts.get("funded", 0)
        funded_rate = round(funded_count / total, 3) if total > 0 else None

        funded_outcomes = [o for o in outcomes if o.outcome_type == "funded"]
        scores_of_funded = [
            float(o.signal_score_at_decision)
            for o in funded_outcomes
            if o.signal_score_at_decision is not None
        ]
        avg_score_funded = (
            round(sum(scores_of_funded) / len(scores_of_funded), 2)
            if scores_of_funded
            else None
        )

        # Latest backtest run
        runs = await self.list_runs(org_id)
        latest_run = runs[0] if runs else None

        from app.modules.backtesting.schemas import BacktestRunResponse

        return BacktestSummaryResponse(
            total_outcomes=total,
            funded_count=funded_count,
            pass_count=counts.get("passed", 0),
            closed_lost_count=counts.get("closed_lost", 0),
            in_progress_count=counts.get("in_progress", 0),
            funded_rate=funded_rate,
            avg_score_of_funded=avg_score_funded,
            latest_run=BacktestRunResponse.model_validate(latest_run) if latest_run else None,
        )
