"""Signal Score Engine: deterministic + AI scoring pipeline.

Runs synchronously inside Celery workers using sync DB sessions.
"""

import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.dataroom import Document, DocumentExtraction
from app.models.enums import DocumentStatus, ExtractionType
from app.models.projects import Project, SignalScore
from app.modules.signal_score.ai_scorer import AIScorer
from app.modules.signal_score.criteria import DIMENSIONS, Criterion, Dimension

logger = structlog.get_logger()


class SignalScoreEngine:
    """Core scoring engine combining completeness (40%) + AI quality (60%)."""

    def __init__(self, session: Session, ai_scorer: AIScorer | None = None):
        self.session = session
        self.ai_scorer = ai_scorer or AIScorer()

    def calculate_score(
        self,
        project_id: uuid.UUID,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> SignalScore:
        """Run full scoring pipeline and persist result."""
        # 1. Load project
        project = self.session.execute(
            select(Project).where(
                Project.id == project_id,
                Project.is_deleted.is_(False),
            )
        ).scalar_one()

        # 2. Load project documents
        documents = list(
            self.session.execute(
                select(Document).where(
                    Document.project_id == project_id,
                    Document.org_id == org_id,
                    Document.is_deleted.is_(False),
                    Document.status == DocumentStatus.READY,
                )
            ).scalars().all()
        )

        # 3. Load all extractions for those documents
        doc_ids = [d.id for d in documents]
        extractions: list[DocumentExtraction] = []
        if doc_ids:
            extractions = list(
                self.session.execute(
                    select(DocumentExtraction).where(
                        DocumentExtraction.document_id.in_(doc_ids)
                    )
                ).scalars().all()
            )

        # Build extraction lookup by document_id
        extraction_map: dict[uuid.UUID, list[DocumentExtraction]] = {}
        for ext in extractions:
            extraction_map.setdefault(ext.document_id, []).append(ext)

        # Project context for AI calls
        project_context = {
            "project_type": project.project_type.value,
            "stage": project.stage.value,
            "country": project.geography_country,
            "org_id": str(org_id),
            "user_id": str(user_id),
        }

        # 4. Score each dimension
        dimension_results = {}
        total_tokens = 0
        model_used = "deterministic"

        for dimension in DIMENSIONS:
            result = self._score_dimension(
                dimension, documents, extraction_map, project_context
            )
            dimension_results[dimension.id] = result
            total_tokens += result.get("tokens_used", 0)
            if result.get("model_used"):
                model_used = result["model_used"]

        # 5. Calculate weighted overall score
        overall = 0.0
        for dim in DIMENSIONS:
            dim_score = dimension_results[dim.id]["score"]
            overall += dim_score * dim.weight

        overall_score = round(overall)

        # 6. Identify gaps and strengths
        gaps = self._identify_gaps(dimension_results)
        strengths = self._identify_strengths(dimension_results)

        # 7. Determine version
        latest_version = self.session.execute(
            select(func.max(SignalScore.version)).where(
                SignalScore.project_id == project_id
            )
        ).scalar()
        next_version = (latest_version or 0) + 1

        # 8. Build scoring_details
        scoring_details = {"dimensions": {}}
        for dim_id, result in dimension_results.items():
            scoring_details["dimensions"][dim_id] = {
                "score": result["score"],
                "completeness_score": result["completeness_score"],
                "quality_score": result["quality_score"],
                "criteria": result["criteria"],
            }

        # 9. Build improvement guidance summary
        improvement_guidance = self._build_improvement_guidance(
            dimension_results, gaps
        )

        # 10. Create SignalScore record
        signal_score = SignalScore(
            project_id=project_id,
            overall_score=overall_score,
            # 6 dimension scores (renamed from P01 migration)
            project_viability_score=dimension_results["technical"]["score"],
            financial_planning_score=dimension_results["financial"]["score"],
            esg_score=dimension_results["esg"]["score"],
            risk_assessment_score=dimension_results["regulatory"]["score"],
            team_strength_score=dimension_results["team"]["score"],
            market_opportunity_score=dimension_results["market_opportunity"]["score"],
            scoring_details=scoring_details,
            gaps={"items": gaps},
            strengths={"items": strengths},
            improvement_guidance=improvement_guidance,
            is_live=False,
            model_used=model_used,
            version=next_version,
            calculated_at=datetime.now(timezone.utc),
        )
        self.session.add(signal_score)
        self.session.flush()

        logger.info(
            "signal_score_calculated",
            project_id=str(project_id),
            overall_score=overall_score,
            version=next_version,
            total_tokens=total_tokens,
        )

        return signal_score

    def _score_dimension(
        self,
        dimension: Dimension,
        documents: list[Document],
        extraction_map: dict[uuid.UUID, list[DocumentExtraction]],
        project_context: dict,
    ) -> dict:
        """Score a single dimension across all its criteria."""
        criteria_results = []
        total_completeness = 0.0
        total_quality = 0.0
        total_max_points = 0
        tokens_used = 0
        model_used = None

        for criterion in dimension.criteria:
            # Find matching documents
            matching_docs = self._find_matching_documents(criterion, documents)
            has_document = len(matching_docs) > 0

            # Completeness: binary per criterion (has doc or not)
            completeness_points = criterion.max_points if has_document else 0
            total_completeness += completeness_points
            total_max_points += criterion.max_points

            # Quality: AI evaluation if document exists
            ai_assessment = None
            quality_points = 0

            if has_document:
                doc_text = self._get_document_text(matching_docs, extraction_map)
                if doc_text:
                    ai_assessment = self.ai_scorer.evaluate_document_quality(
                        doc_text,
                        criterion.name,
                        criterion.description,
                        project_context,
                    )
                    quality_points = round(
                        criterion.max_points * ai_assessment["score"] / 100
                    )
                    tokens_used += ai_assessment.get("tokens_used", 0)
                    if ai_assessment.get("model_used"):
                        model_used = ai_assessment["model_used"]
                else:
                    # Doc exists but no text extracted yet
                    quality_points = round(criterion.max_points * 0.3)

            # Combined criterion score: completeness 40% + quality 60%
            if has_document:
                criterion_score = round(
                    completeness_points * 0.4 + quality_points * 0.6
                )
            else:
                criterion_score = 0

            criteria_results.append({
                "id": criterion.id,
                "name": criterion.name,
                "max_points": criterion.max_points,
                "score": criterion_score,
                "has_document": has_document,
                "document_ids": [str(d.id) for d in matching_docs],
                "ai_assessment": ai_assessment,
            })

        # Dimension score: sum of criterion scores as percentage
        total_scored = sum(c["score"] for c in criteria_results)
        dimension_score = round(total_scored / total_max_points * 100) if total_max_points > 0 else 0

        completeness_pct = round(total_completeness / total_max_points * 100) if total_max_points > 0 else 0
        quality_pct = round(total_quality / total_max_points * 100) if total_max_points > 0 else 0

        return {
            "score": dimension_score,
            "completeness_score": completeness_pct,
            "quality_score": quality_pct,
            "criteria": criteria_results,
            "tokens_used": tokens_used,
            "model_used": model_used,
        }

    def _find_matching_documents(
        self, criterion: Criterion, documents: list[Document]
    ) -> list[Document]:
        """Find documents matching a criterion's relevant classifications."""
        matching = []
        for doc in documents:
            if doc.classification and doc.classification.value in criterion.relevant_classifications:
                matching.append(doc)
        return matching

    def _get_document_text(
        self,
        documents: list[Document],
        extraction_map: dict[uuid.UUID, list[DocumentExtraction]],
    ) -> str | None:
        """Get text content from document extractions (summaries preferred)."""
        texts = []
        for doc in documents:
            doc_extractions = extraction_map.get(doc.id, [])
            for ext in doc_extractions:
                if ext.extraction_type == ExtractionType.SUMMARY:
                    result = ext.result or {}
                    summary = result.get("summary", "")
                    if summary:
                        texts.append(f"[{doc.name}]: {summary}")

            # Fallback: use any extraction result text
            if not texts:
                for ext in doc_extractions:
                    result = ext.result or {}
                    text = result.get("text", result.get("summary", ""))
                    if text:
                        texts.append(f"[{doc.name}]: {str(text)[:2000]}")
                        break

        return "\n\n".join(texts) if texts else None

    def _identify_gaps(self, dimension_results: dict) -> list[dict]:
        """Identify criteria scoring below 50% of their max points."""
        gaps = []
        for dim in DIMENSIONS:
            dim_result = dimension_results[dim.id]
            for crit_result in dim_result["criteria"]:
                criterion_pct = (
                    crit_result["score"] / crit_result["max_points"] * 100
                    if crit_result["max_points"] > 0 else 0
                )
                if criterion_pct < 50:
                    # Determine priority based on points and score
                    if crit_result["score"] == 0:
                        priority = "high"
                    elif criterion_pct < 25:
                        priority = "high"
                    else:
                        priority = "medium"

                    recommendation = (
                        crit_result.get("ai_assessment", {}).get("recommendation", "")
                        if crit_result.get("ai_assessment")
                        else f"Upload documentation for: {crit_result['name']}"
                    )

                    # Look up criterion for doc types
                    from app.modules.signal_score.criteria import ALL_CRITERIA
                    criterion = ALL_CRITERIA.get(crit_result["id"])
                    doc_types = list(criterion.relevant_classifications) if criterion else []

                    gaps.append({
                        "dimension_id": dim.id,
                        "dimension_name": dim.name,
                        "criterion_id": crit_result["id"],
                        "criterion_name": crit_result["name"],
                        "current_score": crit_result["score"],
                        "max_points": crit_result["max_points"],
                        "priority": priority,
                        "recommendation": recommendation,
                        "relevant_doc_types": doc_types,
                    })

        # Sort by priority (high first) then by max_points descending
        priority_order = {"high": 0, "medium": 1, "low": 2}
        gaps.sort(key=lambda g: (priority_order.get(g["priority"], 2), -g["max_points"]))
        return gaps

    def _build_improvement_guidance(
        self, dimension_results: dict, gaps: list[dict]
    ) -> dict:
        """Derive structured improvement guidance from gaps and dimension scores."""
        high_gaps = [g for g in gaps if g["priority"] == "high"]
        medium_gaps = [g for g in gaps if g["priority"] == "medium"]

        # Quick wins: medium-priority gaps with low max_points (easy wins)
        quick_wins = [
            g["recommendation"]
            for g in medium_gaps
            if g["max_points"] <= 10
        ][:3]

        # Lowest scoring dimension
        dim_scores = {
            dim.id: dimension_results[dim.id]["score"] for dim in DIMENSIONS
        }
        weakest_dim_id = min(dim_scores, key=lambda k: dim_scores[k])
        weakest_dim = next((d for d in DIMENSIONS if d.id == weakest_dim_id), None)

        # Estimated potential: if all high gaps were filled
        high_gap_points = sum(g["max_points"] - g["current_score"] for g in high_gaps)
        total_max = sum(
            sum(c["max_points"] for c in dimension_results[dim.id]["criteria"])
            for dim in DIMENSIONS
        )
        potential_gain = round(high_gap_points / total_max * 100) if total_max > 0 else 0

        return {
            "quick_wins": quick_wins,
            "focus_area": weakest_dim.name if weakest_dim else None,
            "high_priority_count": len(high_gaps),
            "medium_priority_count": len(medium_gaps),
            "estimated_max_gain": potential_gain,
            "top_actions": [
                {
                    "dimension_id": g["dimension_id"],
                    "dimension_name": g["dimension_name"],
                    "action": g["recommendation"],
                    "expected_gain": round(
                        (g["max_points"] - g["current_score"])
                        / total_max * 100
                    ) if total_max > 0 else 0,
                    "effort": "high" if g["max_points"] >= 15 else "medium",
                    "doc_types_needed": g["relevant_doc_types"],
                }
                for g in (high_gaps + medium_gaps)[:5]
            ],
        }

    def _identify_strengths(self, dimension_results: dict) -> list[dict]:
        """Identify criteria scoring at or above 80% of their max points."""
        strengths = []
        for dim in DIMENSIONS:
            dim_result = dimension_results[dim.id]
            for crit_result in dim_result["criteria"]:
                criterion_pct = (
                    crit_result["score"] / crit_result["max_points"] * 100
                    if crit_result["max_points"] > 0 else 0
                )
                if criterion_pct >= 80:
                    summary = ""
                    if crit_result.get("ai_assessment"):
                        ai_strengths = crit_result["ai_assessment"].get("strengths", [])
                        summary = ai_strengths[0] if ai_strengths else ""

                    strengths.append({
                        "dimension_id": dim.id,
                        "dimension_name": dim.name,
                        "criterion_id": crit_result["id"],
                        "criterion_name": crit_result["name"],
                        "score": crit_result["score"],
                        "summary": summary,
                    })
        return strengths
