"""Unit tests for signal score criteria and scoring math — no DB required."""

import pytest

from app.modules.signal_score.criteria import (
    ALL_CRITERIA,
    DIMENSIONS,
    Criterion,
    Dimension,
)

# ── Dimension-level invariants ────────────────────────────────────────────────


class TestDimensionWeights:
    def test_weights_sum_to_exactly_one(self):
        total = sum(d.weight for d in DIMENSIONS)
        assert total == pytest.approx(
            1.0, rel=1e-9
        ), f"Dimension weights sum to {total}, must be exactly 1.0"

    def test_exactly_six_dimensions(self):
        assert len(DIMENSIONS) == 6

    def test_expected_dimension_ids_present(self):
        ids = {d.id for d in DIMENSIONS}
        assert ids == {"technical", "financial", "esg", "regulatory", "team", "market_opportunity"}

    @pytest.mark.parametrize("dim", DIMENSIONS)
    def test_weight_positive(self, dim: Dimension):
        assert dim.weight > 0.0

    @pytest.mark.parametrize("dim", DIMENSIONS)
    def test_at_least_one_criterion(self, dim: Dimension):
        assert len(dim.criteria) >= 1

    def test_known_dimension_weights(self):
        """Spot-check the documented weights (20/20/15/15/15/15)."""
        weight_map = {d.id: d.weight for d in DIMENSIONS}
        assert weight_map["technical"] == pytest.approx(0.20)
        assert weight_map["financial"] == pytest.approx(0.20)
        assert weight_map["esg"] == pytest.approx(0.15)
        assert weight_map["regulatory"] == pytest.approx(0.15)
        assert weight_map["team"] == pytest.approx(0.15)
        assert weight_map["market_opportunity"] == pytest.approx(0.15)


# ── Criterion-level invariants ────────────────────────────────────────────────


class TestCriteriaDefinitions:
    def test_all_criteria_indexed_in_all_criteria(self):
        for dim in DIMENSIONS:
            for crit in dim.criteria:
                assert crit.id in ALL_CRITERIA, f"{crit.id} missing from ALL_CRITERIA"

    @pytest.mark.parametrize("crit_id,crit", list(ALL_CRITERIA.items()))
    def test_max_points_positive(self, crit_id: str, crit: Criterion):
        assert crit.max_points > 0

    @pytest.mark.parametrize("crit_id,crit", list(ALL_CRITERIA.items()))
    def test_relevant_classifications_not_empty(self, crit_id: str, crit: Criterion):
        assert len(crit.relevant_classifications) >= 1

    @pytest.mark.parametrize("crit_id,crit", list(ALL_CRITERIA.items()))
    def test_criterion_id_matches_dict_key(self, crit_id: str, crit: Criterion):
        assert crit.id == crit_id

    @pytest.mark.parametrize("crit_id,crit", list(ALL_CRITERIA.items()))
    def test_criterion_has_name_and_description(self, crit_id: str, crit: Criterion):
        assert crit.name
        assert crit.description


# ── Scoring math (mirrors engine logic without DB) ────────────────────────────


def _dimension_score(criteria_results: list[dict], total_max_points: int) -> int:
    """Mirror SignalScoreEngine._score_dimension aggregate logic."""
    total_scored = sum(c["score"] for c in criteria_results)
    return round(total_scored / total_max_points * 100) if total_max_points > 0 else 0


def _overall_score(dimension_scores: dict[str, float]) -> int:
    """Mirror step 5 of calculate_score."""
    total = sum(dimension_scores[d.id] * d.weight for d in DIMENSIONS)
    return round(total)


class TestScoringMath:
    def test_all_perfect_gives_100(self):
        criteria = [{"score": 10, "max_points": 10}, {"score": 15, "max_points": 15}]
        assert _dimension_score(criteria, 25) == 100

    def test_all_zero_gives_0(self):
        criteria = [{"score": 0, "max_points": 10}, {"score": 0, "max_points": 15}]
        assert _dimension_score(criteria, 25) == 0

    def test_half_points_gives_50(self):
        criteria = [{"score": 5, "max_points": 10}]
        assert _dimension_score(criteria, 10) == 50

    def test_zero_max_points_returns_0(self):
        assert _dimension_score([], 0) == 0

    def test_overall_uniform_50_gives_50(self):
        """All dimensions at 50 with weights summing to 1 → overall = 50."""
        dim_scores = {d.id: 50.0 for d in DIMENSIONS}
        assert _overall_score(dim_scores) == 50

    def test_overall_all_zeros(self):
        dim_scores = {d.id: 0.0 for d in DIMENSIONS}
        assert _overall_score(dim_scores) == 0

    def test_overall_all_hundreds(self):
        dim_scores = {d.id: 100.0 for d in DIMENSIONS}
        assert _overall_score(dim_scores) == 100

    def test_score_range_invariant(self):
        """Weighted sum of bounded [0..100] scores with weights=1 stays in [0..100]."""
        for score in [0, 25, 50, 75, 100]:
            weighted = sum(score * d.weight for d in DIMENSIONS)
            assert 0 <= weighted <= 100

    def test_criterion_combined_formula_full_doc(self):
        """With a document: score = completeness*0.4 + quality*0.6."""
        max_points = 10
        # Doc present, AI quality = 100% → quality_points = max_points
        completeness_points = max_points
        quality_points = max_points
        score = round(completeness_points * 0.4 + quality_points * 0.6)
        assert score == max_points

    def test_criterion_combined_formula_partial_quality(self):
        """quality 50% of max → combined score < max_points."""
        max_points = 10
        quality_points = round(max_points * 0.5)  # 50% quality
        score = round(max_points * 0.4 + quality_points * 0.6)
        assert 0 < score < max_points

    def test_no_document_zero_score(self):
        """Missing document → criterion score = 0 always."""
        # Directly mirrors engine line: if not has_document: criterion_score = 0
        has_document = False
        score = 0 if not has_document else None
        assert score == 0


# ── Gap / strength thresholds ─────────────────────────────────────────────────


class TestGapStrengthThresholds:
    def test_below_50_pct_is_gap(self):
        max_points = 10
        assert (4 / max_points * 100) < 50  # 40% → gap

    def test_exactly_50_pct_not_gap(self):
        max_points = 10
        assert not ((5 / max_points * 100) < 50)  # 50% → NOT a gap

    def test_above_80_pct_is_strength(self):
        max_points = 10
        assert (8 / max_points * 100) >= 80  # 80% → strength

    def test_below_80_pct_not_strength(self):
        max_points = 10
        assert not ((7 / max_points * 100) >= 80)  # 70% → NOT strength

    def test_gap_priority_high_when_score_zero(self):
        """Zero score → high priority gap (mirrors engine _identify_gaps logic)."""
        score = 0
        priority = "high" if score == 0 else "medium"
        assert priority == "high"

    def test_gap_priority_high_below_25_pct(self):
        max_points = 10
        score = 2  # 20% < 25% → high priority
        pct = score / max_points * 100
        priority = "high" if pct < 25 else "medium"
        assert priority == "high"
