"""Tests for app.core.module_discovery.

All tests run without a running database or network — module-level imports
are enough since routers only read env-level config at import time.
"""

from __future__ import annotations

import importlib
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import APIRouter

from app.core.module_discovery import DISABLED_MODULES, discover_routers

# ── Helpers ───────────────────────────────────────────────────────────────────


def _discovered_labels() -> list[str]:
    """Return just the label part of every discovered router."""
    return [name for name, _ in discover_routers()]


# ── Basic discovery ───────────────────────────────────────────────────────────


class TestDiscoverRouters:
    def test_returns_list_of_tuples(self) -> None:
        result = discover_routers()
        assert isinstance(result, list)
        assert all(isinstance(item, tuple) and len(item) == 2 for item in result)

    def test_routers_are_apirouter_instances(self) -> None:
        for _label, router in discover_routers():
            assert isinstance(router, APIRouter), f"Expected APIRouter, got {type(router)}"

    def test_total_count_matches_filesystem(self) -> None:
        """Number of discovered routers must equal number of router.py files."""
        import app.modules as modules_pkg

        modules_dir = Path(modules_pkg.__file__).parent
        fs_count = len(list(modules_dir.rglob("router.py")))

        # Subtract any that are in DISABLED_MODULES
        routers = discover_routers()
        assert len(routers) == fs_count - len(DISABLED_MODULES)

    def test_top_level_modules_present(self) -> None:
        labels = _discovered_labels()
        expected = [
            "ai_feedback",
            "backtesting",
            "blockchain_audit",
            "board_advisor",
            "business_plans",
            "capital_efficiency",
            "carbon_credits",
            "certification",
            "citations",
            "collaboration",
            "compliance",
            "comps",
            "connectors",
            "crm_sync",
            "custom_domain",
            "dataroom",
            "deal_flow",
            "deal_intelligence",
            "deal_rooms",
            "development_os",
            "digest",
            "doc_versions",
            "document_annotations",
            "due_diligence",
            "ecosystem",
            "engagement",
            "equity_calculator",
            "esg",
            "excel_api",
            "expert_insights",
            "financial_templates",
            "fx",
            "gamification",
            "impact",
            "insurance",
            "investor_personas",
            "investor_signal_score",
            "launch",
            "legal",
            "lineage",
            "lp_reporting",
            "market_data",
            "market_enrichment",
            "marketplace",
            "matching",
            "meeting_prep",
            "metrics",
            "monitoring",
            "notifications",
            "onboarding",
            "pacing",
            "portfolio",
            "projects",
            "qa_workflow",
            "ralph_ai",
            "redaction",
            "reporting",
            "risk",
            "risk_profile",
            "search",
            "settings",
            "signal_score",
            "smart_screener",
            "stress_test",
            "tax_credits",
            "taxonomy",
            "tokenization",
            "valuation",
            "value_quantifier",
            "voice_input",
            "warm_intros",
            "watchlists",
            "webhooks",
        ]
        for name in expected:
            assert name in labels, f"Expected module '{name}' not discovered"

    def test_nested_modules_present(self) -> None:
        labels = _discovered_labels()
        nested = [
            "admin",
            "admin.prompts",
            "alley.advisor",
            "alley.analytics",
            "alley.risk",
            "alley.score_performance",
            "alley.signal_score",
        ]
        for name in nested:
            assert name in labels, f"Expected nested module '{name}' not discovered"

    def test_labels_are_unique(self) -> None:
        labels = _discovered_labels()
        assert len(labels) == len(set(labels)), "Duplicate module labels found"

    def test_order_is_deterministic(self) -> None:
        """discover_routers must return the same order on repeated calls."""
        labels_a = _discovered_labels()
        labels_b = _discovered_labels()
        assert labels_a == labels_b


# ── DISABLED_MODULES ─────────────────────────────────────────────────────────


class TestDisabledModules:
    def test_disabled_module_is_skipped(self) -> None:
        with patch("app.core.module_discovery.DISABLED_MODULES", ["signal_score"]):
            labels = _discovered_labels()
        assert "signal_score" not in labels

    def test_disabled_nested_module_is_skipped(self) -> None:
        with patch("app.core.module_discovery.DISABLED_MODULES", ["alley.advisor"]):
            labels = _discovered_labels()
        assert "alley.advisor" not in labels
        # Other alley modules should still be present
        assert "alley.risk" in labels

    def test_disabling_does_not_affect_others(self) -> None:
        with patch("app.core.module_discovery.DISABLED_MODULES", ["signal_score"]):
            labels = _discovered_labels()
        # Unrelated modules are unaffected
        assert "portfolio" in labels
        assert "projects" in labels

    def test_default_disabled_list_is_empty(self) -> None:
        """No modules are disabled by default."""
        assert DISABLED_MODULES == []


# ── Error handling ────────────────────────────────────────────────────────────


class TestErrorHandling:
    def test_import_error_does_not_abort_discovery(self) -> None:
        """A module that fails to import should be skipped; others still load."""
        original_import = importlib.import_module

        def patched_import(name: str, *args, **kwargs):
            if name == "app.modules.signal_score.router":
                raise ImportError("simulated import failure")
            return original_import(name, *args, **kwargs)

        with patch("app.core.module_discovery.importlib.import_module", side_effect=patched_import):
            routers = discover_routers()

        labels = [n for n, _ in routers]
        # signal_score is gone
        assert "signal_score" not in labels
        # but everything else loaded fine
        assert "portfolio" in labels
        assert len(routers) > 50

    def test_missing_router_attr_is_skipped(self) -> None:
        """router.py without a 'router' attribute at module level is skipped."""
        fake_mod = types.ModuleType("fake")
        # No 'router' attribute — should be skipped gracefully
        original_import = importlib.import_module

        def patched_import(name: str, *args, **kwargs):
            if name == "app.modules.signal_score.router":
                return fake_mod
            return original_import(name, *args, **kwargs)

        with patch("app.core.module_discovery.importlib.import_module", side_effect=patched_import):
            routers = discover_routers()

        labels = [n for n, _ in routers]
        assert "signal_score" not in labels
        assert "portfolio" in labels


# ── Router config ─────────────────────────────────────────────────────────────


class TestRouterConfig:
    def test_routers_keep_their_own_prefix(self) -> None:
        """Each router should retain its own prefix (no extra prefix injected)."""
        routers = dict(discover_routers())

        # carbon_credits uses prefix="/carbon"
        assert routers["carbon_credits"].prefix == "/carbon"

        # ralph_ai uses prefix="/ralph"
        assert routers["ralph_ai"].prefix == "/ralph"

        # deal_rooms uses prefix="/deal-rooms"
        assert routers["deal_rooms"].prefix == "/deal-rooms"

    def test_nested_routers_keep_their_own_prefix(self) -> None:
        routers = dict(discover_routers())

        # alley.advisor uses prefix="/alley/advisor"
        assert routers["alley.advisor"].prefix == "/alley/advisor"

        # admin.prompts has its own prefix
        admin_prompts = routers["admin.prompts"]
        assert isinstance(admin_prompts, APIRouter)
