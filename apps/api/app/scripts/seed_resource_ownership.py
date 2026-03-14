#!/usr/bin/env python3
"""Seed ResourceOwnership records for all existing resources.

Run BEFORE setting OBJECT_LEVEL_RBAC_ENABLED=True to ensure no user loses
access to their existing data when enforcement is enabled.

Strategy:
  - Projects:       all org members get access (owner/editor/viewer by role)
  - Deal rooms:     room members + creator get access
  - Conversations:  conversation creator gets owner access
  - LP reports:     all org viewers/analysts get viewer access
  - Documents:      all org members get viewer access

Idempotent: uses INSERT ... ON CONFLICT DO NOTHING (safe to re-run).

Usage (from apps/api directory):
    poetry run python -m app.scripts.seed_resource_ownership
    poetry run python -m app.scripts.seed_resource_ownership --dry-run
"""
from __future__ import annotations

import argparse
import os
import sys
import uuid

# Ensure apps/api root is on sys.path
_api_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _api_root not in sys.path:
    sys.path.insert(0, _api_root)

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.enums import UserRole

# ── Role → permission level mapping ──────────────────────────────────────────

_ROLE_LEVEL: dict[UserRole, str] = {
    UserRole.ADMIN: "owner",
    UserRole.MANAGER: "owner",
    UserRole.ANALYST: "editor",
    UserRole.VIEWER: "viewer",
}

# ── Counter ───────────────────────────────────────────────────────────────────

inserted = 0
skipped = 0


def _upsert(
    conn,
    *,
    user_id: uuid.UUID,
    org_id: uuid.UUID,
    resource_type: str,
    resource_id: uuid.UUID,
    permission_level: str,
    granted_by: uuid.UUID,
    dry_run: bool,
) -> bool:
    """Insert ownership record, skip if already exists. Returns True if inserted."""
    global inserted, skipped

    check = conn.execute(
        text(
            "SELECT 1 FROM resource_ownership "
            "WHERE user_id = :uid AND resource_type = :rt AND resource_id = :rid "
            "LIMIT 1"
        ),
        {"uid": str(user_id), "rt": resource_type, "rid": str(resource_id)},
    ).fetchone()

    if check:
        skipped += 1
        return False

    if not dry_run:
        conn.execute(
            text(
                "INSERT INTO resource_ownership "
                "(id, user_id, org_id, resource_type, resource_id, permission_level, granted_by) "
                "VALUES (:id, :uid, :oid, :rt, :rid, :pl, :gb) "
                "ON CONFLICT (user_id, resource_type, resource_id) DO NOTHING"
            ),
            {
                "id": str(uuid.uuid4()),
                "uid": str(user_id),
                "oid": str(org_id),
                "rt": resource_type,
                "rid": str(resource_id),
                "pl": permission_level,
                "gb": str(granted_by),
            },
        )
    inserted += 1
    return True


def seed(dry_run: bool = False) -> None:
    global inserted, skipped

    engine = create_engine(settings.DATABASE_URL_SYNC, echo=False)

    with engine.connect() as conn:
        # ── 1. Projects ───────────────────────────────────────────────────────
        print("Seeding projects...")
        projects = conn.execute(text("SELECT id, org_id FROM projects")).fetchall()
        for proj_id, org_id in projects:
            users = conn.execute(
                text("SELECT id, role FROM users WHERE org_id = :oid AND is_active = TRUE"),
                {"oid": str(org_id)},
            ).fetchall()
            # Pick one admin/manager as the grantor (or fall back to first user)
            grantor = next(
                (u[0] for u in users if u[1] in (UserRole.ADMIN.value, UserRole.MANAGER.value)),
                users[0][0] if users else None,
            )
            if grantor is None:
                continue
            for u_id, role in users:
                level = _ROLE_LEVEL.get(UserRole(role), "viewer")
                _upsert(
                    conn,
                    user_id=uuid.UUID(str(u_id)),
                    org_id=uuid.UUID(str(org_id)),
                    resource_type="project",
                    resource_id=uuid.UUID(str(proj_id)),
                    permission_level=level,
                    granted_by=uuid.UUID(str(grantor)),
                    dry_run=dry_run,
                )

        # ── 2. Deal rooms ─────────────────────────────────────────────────────
        print("Seeding deal rooms...")
        rooms = conn.execute(text("SELECT id, org_id, created_by FROM deal_rooms")).fetchall()
        for room_id, org_id, created_by in rooms:
            # Creator → owner
            _upsert(
                conn,
                user_id=uuid.UUID(str(created_by)),
                org_id=uuid.UUID(str(org_id)),
                resource_type="deal_room",
                resource_id=uuid.UUID(str(room_id)),
                permission_level="owner",
                granted_by=uuid.UUID(str(created_by)),
                dry_run=dry_run,
            )
            # Explicit members
            members = conn.execute(
                text(
                    "SELECT drm.user_id, u.role FROM deal_room_members drm "
                    "JOIN users u ON u.id = drm.user_id "
                    "WHERE drm.room_id = :rid AND drm.user_id IS NOT NULL"
                ),
                {"rid": str(room_id)},
            ).fetchall()
            for u_id, role in members:
                level = _ROLE_LEVEL.get(UserRole(role), "viewer")
                _upsert(
                    conn,
                    user_id=uuid.UUID(str(u_id)),
                    org_id=uuid.UUID(str(org_id)),
                    resource_type="deal_room",
                    resource_id=uuid.UUID(str(room_id)),
                    permission_level=level,
                    granted_by=uuid.UUID(str(created_by)),
                    dry_run=dry_run,
                )

        # ── 3. AI Conversations ───────────────────────────────────────────────
        print("Seeding conversations...")
        convs = conn.execute(
            text("SELECT id, org_id, user_id FROM ai_conversations")
        ).fetchall()
        for conv_id, org_id, user_id in convs:
            _upsert(
                conn,
                user_id=uuid.UUID(str(user_id)),
                org_id=uuid.UUID(str(org_id)),
                resource_type="conversation",
                resource_id=uuid.UUID(str(conv_id)),
                permission_level="owner",
                granted_by=uuid.UUID(str(user_id)),
                dry_run=dry_run,
            )

        # ── 4. LP Reports ─────────────────────────────────────────────────────
        print("Seeding LP reports...")
        reports = conn.execute(text("SELECT id, org_id FROM lp_reports")).fetchall()
        for report_id, org_id in reports:
            # Grant viewer/analyst users in the same org viewer access
            users = conn.execute(
                text(
                    "SELECT id FROM users WHERE org_id = :oid AND is_active = TRUE "
                    "AND role IN ('viewer', 'analyst')"
                ),
                {"oid": str(org_id)},
            ).fetchall()
            # Need a grantor
            grantor_row = conn.execute(
                text(
                    "SELECT id FROM users WHERE org_id = :oid AND is_active = TRUE "
                    "AND role IN ('admin', 'manager') LIMIT 1"
                ),
                {"oid": str(org_id)},
            ).fetchone()
            if not grantor_row:
                continue
            grantor = grantor_row[0]
            for (u_id,) in users:
                _upsert(
                    conn,
                    user_id=uuid.UUID(str(u_id)),
                    org_id=uuid.UUID(str(org_id)),
                    resource_type="lp_report",
                    resource_id=uuid.UUID(str(report_id)),
                    permission_level="viewer",
                    granted_by=uuid.UUID(str(grantor)),
                    dry_run=dry_run,
                )

        # ── 5. Documents ──────────────────────────────────────────────────────
        print("Seeding documents...")
        docs = conn.execute(text("SELECT id, org_id FROM documents")).fetchall()
        for doc_id, org_id in docs:
            users = conn.execute(
                text("SELECT id, role FROM users WHERE org_id = :oid AND is_active = TRUE"),
                {"oid": str(org_id)},
            ).fetchall()
            grantor = next(
                (u[0] for u in users if u[1] in (UserRole.ADMIN.value, UserRole.MANAGER.value)),
                users[0][0] if users else None,
            )
            if grantor is None:
                continue
            for u_id, role in users:
                level = _ROLE_LEVEL.get(UserRole(role), "viewer")
                _upsert(
                    conn,
                    user_id=uuid.UUID(str(u_id)),
                    org_id=uuid.UUID(str(org_id)),
                    resource_type="document",
                    resource_id=uuid.UUID(str(doc_id)),
                    permission_level=level,
                    granted_by=uuid.UUID(str(grantor)),
                    dry_run=dry_run,
                )

        if not dry_run:
            conn.commit()

    label = "[DRY RUN] Would insert" if dry_run else "Inserted"
    print(f"\n{label}: {inserted} records  |  Already existed: {skipped}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed ResourceOwnership records")
    parser.add_argument("--dry-run", action="store_true", help="Count without inserting")
    args = parser.parse_args()
    seed(dry_run=args.dry_run)
