"""Signal Score change explainability — explains why scores changed over time."""

import statistics
import uuid
from datetime import datetime, timedelta
from typing import Any

import structlog

logger = structlog.get_logger()


class ScoreExplainability:
    def __init__(self, db):
        self.db = db

    async def explain_changes(
        self,
        project_id: uuid.UUID,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Explain what caused score changes over a period."""
        from app.modules.metrics.snapshot_service import MetricSnapshotService
        svc = MetricSnapshotService(self.db)
        snapshots = await svc.get_trend("project", project_id, "signal_score", from_date, to_date)

        changes = []
        for i in range(1, len(snapshots)):
            snap = snapshots[i]
            prev = snapshots[i - 1]
            if snap.value == prev.value:
                continue
            delta = round(snap.value - prev.value, 2)
            dim_changes = self._diff_dimensions(
                (prev.metadata_ or {}).get("dimensions", {}),
                (snap.metadata_ or {}).get("dimensions", {}),
            )
            changes.append({
                "date": snap.recorded_at.isoformat(),
                "score_from": prev.value,
                "score_to": snap.value,
                "delta": delta,
                "direction": "up" if delta > 0 else "down",
                "trigger_event": snap.trigger_event,
                "trigger_entity": str(snap.trigger_entity_id) if snap.trigger_entity_id else None,
                "dimension_changes": dim_changes,
                "explanation": self._generate_explanation(delta, dim_changes, snap.trigger_event),
            })
        return changes

    def _diff_dimensions(
        self, old_dims: dict[str, Any], new_dims: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Compare two dimension score snapshots, return what changed."""
        diffs = []
        all_dims = set(list(old_dims.keys()) + list(new_dims.keys()))
        for dim in all_dims:
            old_val = float(old_dims.get(dim, 0) or 0)
            new_val = float(new_dims.get(dim, 0) or 0)
            if old_val != new_val:
                diffs.append({
                    "dimension": dim,
                    "from": old_val,
                    "to": new_val,
                    "delta": round(new_val - old_val, 2),
                })
        return sorted(diffs, key=lambda x: abs(x["delta"]), reverse=True)

    def _generate_explanation(
        self, delta: float, dim_changes: list[dict], trigger: str | None
    ) -> str:
        """Human-readable explanation of score change."""
        parts = []
        if trigger == "document_upload":
            parts.append("A new document was uploaded")
        elif trigger == "score_computed":
            parts.append("Score was recalculated")
        elif trigger == "daily_snapshot":
            parts.append("Daily score snapshot")
        else:
            parts.append("Score updated")

        for dc in dim_changes[:3]:
            direction = "improved" if dc["delta"] > 0 else "decreased"
            dim_label = dc["dimension"].replace("_", " ").title()
            parts.append(f"{dim_label} {direction} by {abs(dc['delta']):.1f} points")

        return ". ".join(parts) + "."

    async def get_score_volatility(
        self, project_id: uuid.UUID, period_months: int = 6
    ) -> dict[str, Any]:
        """How stable is this score? High volatility = uncertain or rapidly changing data."""
        from app.modules.metrics.snapshot_service import MetricSnapshotService
        from_date = datetime.utcnow() - timedelta(days=period_months * 30)
        svc = MetricSnapshotService(self.db)
        snapshots = await svc.get_trend("project", project_id, "signal_score", from_date=from_date)

        if len(snapshots) < 3:
            return {
                "volatility": "insufficient_data",
                "label": "Not enough history",
                "std_dev": None,
                "snapshot_count": len(snapshots),
            }
        values = [s.value for s in snapshots]
        std = statistics.stdev(values)
        if std < 2:
            label = "Stable"
            level = "low"
        elif std < 5:
            label = "Moderate changes"
            level = "medium"
        else:
            label = "Volatile"
            level = "high"
        return {
            "volatility": level,
            "label": label,
            "std_dev": round(std, 2),
            "snapshot_count": len(snapshots),
            "min": round(min(values), 1),
            "max": round(max(values), 1),
        }

    async def get_dimension_history(
        self,
        project_id: uuid.UUID,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Get per-dimension score breakdown over time for stacked bar charts."""
        from app.modules.metrics.snapshot_service import MetricSnapshotService
        svc = MetricSnapshotService(self.db)
        snapshots = await svc.get_trend("project", project_id, "signal_score", from_date, to_date)
        result = []
        for s in snapshots:
            dims = (s.metadata_ or {}).get("dimensions", {})
            result.append({
                "date": s.recorded_at.isoformat(),
                "overall": s.value,
                "dimensions": dims,
                "trigger": s.trigger_event,
            })
        return result
