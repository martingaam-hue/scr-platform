"""Automatic module router discovery.

Scans ``app/modules/`` recursively for ``router.py`` files and imports
them so that every module is registered without touching ``main.py``.

Adding a new module is as simple as creating
``app/modules/<name>/router.py`` — no changes to ``main.py`` required.

Disabling a module temporarily: add its dotted label to
:data:`DISABLED_MODULES` below.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import structlog
from fastapi import APIRouter

logger = structlog.get_logger()

# ── Disabled modules ──────────────────────────────────────────────────────────
# Add the dotted label (relative to app/modules/) for any module that should
# be excluded from the API.  The label matches what appears in startup logs.
#
# Examples:
#   "voice_input"          – top-level module
#   "alley.advisor"        – nested module
#   "admin.prompts"        – nested sub-module
#
DISABLED_MODULES: list[str] = []


# ── Discovery ─────────────────────────────────────────────────────────────────


def discover_routers(
    modules_base: str = "app.modules",
) -> list[tuple[str, APIRouter]]:
    """Scan *modules_base* recursively for ``router.py`` files.

    Each ``router.py`` must expose a module-level ``router`` attribute that
    is a :class:`fastapi.APIRouter` instance (already configured with its own
    prefix and tags).

    Returns a list of ``(label, router)`` tuples where *label* is the dotted
    path relative to ``app/modules/``, e.g. ``"signal_score"`` or
    ``"alley.advisor"``.

    Failures are logged but do **not** abort startup — a broken module will
    be skipped so the rest of the API remains available.
    """
    # Resolve the filesystem path of the modules package.
    base_pkg = importlib.import_module(modules_base)
    modules_dir = Path(base_pkg.__file__).parent  # type: ignore[arg-type]

    routers: list[tuple[str, APIRouter]] = []
    failed: list[str] = []

    for router_file in sorted(modules_dir.rglob("router.py")):
        # Derive the dotted label, e.g. "alley/advisor/router.py" → "alley.advisor"
        rel = router_file.relative_to(modules_dir)
        label = ".".join(rel.parent.parts)  # e.g. "signal_score" / "alley.advisor"

        if label in DISABLED_MODULES:
            logger.info("module_discovery_disabled", module=label)
            continue

        import_path = f"{modules_base}.{label}.router"
        try:
            mod = importlib.import_module(import_path)
        except Exception as exc:
            failed.append(label)
            logger.error(
                "module_discovery_import_failed",
                module=label,
                import_path=import_path,
                error=str(exc),
            )
            continue

        router = getattr(mod, "router", None)
        if router is None:
            logger.warning("module_discovery_no_router_attr", module=label)
            continue

        routers.append((label, router))
        logger.debug("module_discovery_found", module=label)

    logger.info(
        "module_discovery_complete",
        registered=len(routers),
        disabled=len(DISABLED_MODULES),
        failed=len(failed),
        modules=sorted(label for label, _ in routers),
    )

    if failed:
        logger.warning("module_discovery_some_failed", failed_modules=failed)

    return routers
