"""Document Version Control service — diff generation and AI change summaries."""

from __future__ import annotations

import hashlib
import uuid
from difflib import SequenceMatcher, unified_diff
from typing import Any

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.doc_versions import DocumentVersion

logger = structlog.get_logger()

_AI_TIMEOUT = 60.0


# ── Diff ──────────────────────────────────────────────────────────────────────


def generate_diff(old_text: str, new_text: str) -> dict[str, Any]:
    """Generate a structured diff between two text bodies."""
    old_lines = old_text.splitlines()
    new_lines = new_text.splitlines()

    diff_lines = list(unified_diff(old_lines, new_lines, lineterm="", n=3))

    additions = sum(1 for ln in diff_lines if ln.startswith("+") and not ln.startswith("+++"))
    deletions = sum(1 for ln in diff_lines if ln.startswith("-") and not ln.startswith("---"))
    similarity = SequenceMatcher(None, old_text, new_text).ratio()

    return {
        "stats": {
            "additions": additions,
            "deletions": deletions,
            "similarity": round(similarity, 3),
            "total_changes": additions + deletions,
        },
        "diff_lines": diff_lines[:500],
    }


# ── AI summary ────────────────────────────────────────────────────────────────


async def ai_summarize_changes(diff: dict[str, Any], doc_classification: str | None) -> dict[str, Any]:
    """Call AI gateway to summarise document changes."""
    context = {
        "diff_stats": diff["stats"],
        "sample_changes": diff["diff_lines"][:100],
        "doc_type": doc_classification or "unknown",
    }
    try:
        async with httpx.AsyncClient(timeout=_AI_TIMEOUT) as client:
            resp = await client.post(
                f"{settings.AI_GATEWAY_URL}/v1/completions",
                json={"task_type": "summarize_doc_changes", "context": context},
                headers={"X-API-Key": settings.AI_GATEWAY_API_KEY},
            )
            resp.raise_for_status()
            data = resp.json()
        return data.get("validated_data") or {}
    except Exception as exc:
        logger.warning("doc_version.ai_summary_failed", error=str(exc))
        return {
            "summary": f"Document updated with {diff['stats']['additions']} additions and {diff['stats']['deletions']} deletions.",
            "significance": _infer_significance(diff["stats"]),
            "key_changes": [],
        }


def _infer_significance(stats: dict[str, Any]) -> str:
    total = stats.get("total_changes", 0)
    similarity = stats.get("similarity", 1.0)
    if similarity < 0.5 or total > 200:
        return "critical"
    if similarity < 0.7 or total > 100:
        return "major"
    if total > 30:
        return "moderate"
    return "minor"


# ── CRUD ──────────────────────────────────────────────────────────────────────


async def get_latest_version(db: AsyncSession, document_id: uuid.UUID, org_id: uuid.UUID) -> DocumentVersion | None:
    result = await db.execute(
        select(DocumentVersion)
        .where(DocumentVersion.document_id == document_id, DocumentVersion.org_id == org_id)
        .order_by(DocumentVersion.version_number.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def list_versions(db: AsyncSession, document_id: uuid.UUID, org_id: uuid.UUID) -> list[DocumentVersion]:
    result = await db.execute(
        select(DocumentVersion)
        .where(DocumentVersion.document_id == document_id, DocumentVersion.org_id == org_id)
        .order_by(DocumentVersion.version_number.desc())
    )
    return list(result.scalars().all())


async def get_version(db: AsyncSession, version_id: uuid.UUID, org_id: uuid.UUID) -> DocumentVersion | None:
    result = await db.execute(
        select(DocumentVersion)
        .where(DocumentVersion.id == version_id, DocumentVersion.org_id == org_id)
    )
    return result.scalar_one_or_none()


async def create_version(
    db: AsyncSession,
    document_id: uuid.UUID,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    new_s3_key: str,
    file_size: int | None,
    checksum: str | None,
    old_text: str | None = None,
    new_text: str | None = None,
    doc_classification: str | None = None,
) -> DocumentVersion:
    """Create a new version record, computing diff and AI summary if text is provided."""
    prev = await get_latest_version(db, document_id, org_id)
    version_number = (prev.version_number + 1) if prev else 1

    diff_stats = None
    diff_lines_data = None
    change_summary = None
    change_significance = None
    key_changes = None

    if old_text and new_text:
        diff_result = generate_diff(old_text, new_text)
        diff_stats = diff_result["stats"]
        diff_lines_data = diff_result["diff_lines"]

        ai_result = await ai_summarize_changes(diff_result, doc_classification)
        change_summary = ai_result.get("summary")
        change_significance = ai_result.get("significance", "minor")
        key_changes = ai_result.get("key_changes", [])

    version = DocumentVersion(
        document_id=document_id,
        org_id=org_id,
        version_number=version_number,
        s3_key=new_s3_key,
        file_size_bytes=file_size,
        checksum_sha256=checksum,
        uploaded_by=user_id,
        diff_stats=diff_stats,
        diff_lines=diff_lines_data,
        change_summary=change_summary,
        change_significance=change_significance,
        key_changes=key_changes,
    )
    db.add(version)
    await db.flush()
    return version


async def compare_versions(
    db: AsyncSession,
    document_id: uuid.UUID,
    org_id: uuid.UUID,
    version_a_num: int,
    version_b_num: int,
) -> tuple[DocumentVersion | None, DocumentVersion | None]:
    """Retrieve two specific versions for comparison."""
    result = await db.execute(
        select(DocumentVersion)
        .where(
            DocumentVersion.document_id == document_id,
            DocumentVersion.org_id == org_id,
            DocumentVersion.version_number.in_([version_a_num, version_b_num]),
        )
    )
    versions = {v.version_number: v for v in result.scalars().all()}
    return versions.get(version_a_num), versions.get(version_b_num)
