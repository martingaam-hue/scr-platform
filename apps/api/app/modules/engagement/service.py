"""Engagement tracking service — document open/page/close/download events and analytics."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.engagement import DocumentEngagement

logger = structlog.get_logger()


class EngagementService:
    def __init__(self, db: AsyncSession, org_id: uuid.UUID) -> None:
        self.db = db
        self.org_id = org_id

    # ── Event tracking ─────────────────────────────────────────────────────────

    async def track_open(
        self,
        document_id: uuid.UUID,
        user_id: uuid.UUID,
        session_id: str,
        total_pages: int | None = None,
        referrer: str | None = None,
        device: str | None = None,
    ) -> DocumentEngagement:
        """Create a new engagement session record when a viewer opens a document."""
        engagement = DocumentEngagement(
            org_id=self.org_id,
            document_id=document_id,
            user_id=user_id,
            session_id=session_id,
            opened_at=datetime.now(timezone.utc),
            total_pages=total_pages,
            pages_viewed=[],
            pages_viewed_count=0,
            completion_pct=0.0,
            total_time_seconds=0,
            downloaded=False,
            printed=False,
            referrer_page=referrer,
            device_type=device,
        )
        self.db.add(engagement)
        await self.db.flush()
        await self.db.refresh(engagement)
        logger.info(
            "engagement_opened",
            engagement_id=str(engagement.id),
            document_id=str(document_id),
            user_id=str(user_id),
        )
        return engagement

    async def track_page_view(
        self,
        engagement_id: uuid.UUID,
        page_number: int,
        time_seconds: int,
    ) -> DocumentEngagement:
        """Record (or accumulate) dwell time for a single page within an engagement session."""
        engagement = await self._load_engagement(engagement_id)

        # Build updated pages_viewed list — accumulate time if page already seen
        pages: list[dict[str, Any]] = list(engagement.pages_viewed or [])
        for entry in pages:
            if entry.get("page") == page_number:
                entry["time_seconds"] = entry.get("time_seconds", 0) + time_seconds
                break
        else:
            pages.append({"page": page_number, "time_seconds": time_seconds})

        # Derive summary fields
        total_time = sum(e.get("time_seconds", 0) for e in pages)
        viewed_count = len(pages)
        completion = 0.0
        if engagement.total_pages and engagement.total_pages > 0:
            completion = round(min(viewed_count / engagement.total_pages, 1.0) * 100, 1)

        # Reassign the JSONB column so SQLAlchemy detects the mutation
        engagement.pages_viewed = pages
        engagement.total_time_seconds = total_time
        engagement.pages_viewed_count = viewed_count
        engagement.completion_pct = completion

        await self.db.flush()
        await self.db.refresh(engagement)
        return engagement

    async def track_close(self, engagement_id: uuid.UUID) -> DocumentEngagement:
        """Mark the session as closed by recording closed_at."""
        engagement = await self._load_engagement(engagement_id)
        engagement.closed_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(engagement)
        return engagement

    async def track_download(self, engagement_id: uuid.UUID) -> DocumentEngagement:
        """Mark the document as downloaded within this session."""
        engagement = await self._load_engagement(engagement_id)
        engagement.downloaded = True
        await self.db.flush()
        await self.db.refresh(engagement)
        return engagement

    # ── Analytics ──────────────────────────────────────────────────────────────

    async def get_document_analytics(self, document_id: uuid.UUID) -> dict[str, Any]:
        """Return aggregate analytics for a document scoped to the current org."""
        sessions = await self._load_sessions_for_document(document_id)

        if not sessions:
            return {
                "document_id": document_id,
                "total_views": 0,
                "unique_viewers": 0,
                "total_time_seconds": 0,
                "avg_time_seconds": 0.0,
                "avg_completion_pct": 0.0,
                "download_count": 0,
                "page_heatmap": {},
                "recent_sessions": [],
            }

        total_views = len(sessions)
        unique_viewers = len({s.user_id for s in sessions})
        total_time = sum(s.total_time_seconds for s in sessions)
        avg_time = round(total_time / total_views, 1) if total_views else 0.0
        avg_completion = round(
            sum(s.completion_pct for s in sessions) / total_views, 1
        ) if total_views else 0.0
        download_count = sum(1 for s in sessions if s.downloaded)

        # Page heatmap: page_number → total_time_seconds across all sessions
        heatmap: dict[int, int] = {}
        for session in sessions:
            for entry in (session.pages_viewed or []):
                page = entry.get("page")
                t = entry.get("time_seconds", 0)
                if page is not None:
                    heatmap[page] = heatmap.get(page, 0) + t

        # Recent sessions (last 20, most-recent first)
        sorted_sessions = sorted(sessions, key=lambda s: s.opened_at, reverse=True)
        recent_sessions = [s.to_dict() for s in sorted_sessions[:20]]

        return {
            "document_id": document_id,
            "total_views": total_views,
            "unique_viewers": unique_viewers,
            "total_time_seconds": total_time,
            "avg_time_seconds": avg_time,
            "avg_completion_pct": avg_completion,
            "download_count": download_count,
            "page_heatmap": heatmap,
            "recent_sessions": recent_sessions,
        }

    async def get_deal_engagement(
        self,
        project_id: uuid.UUID,
        deal_room_id: uuid.UUID | None = None,
    ) -> list[dict[str, Any]]:
        """Compute per-investor engagement for all documents belonging to a project.

        Groups document_engagement rows by viewer's org, then builds an
        InvestorEngagementResponse-compatible dict for each investor org.
        """
        from app.models.core import User
        from app.models.dataroom import Document

        # Load all documents for the project visible to this org
        doc_stmt = select(Document).where(
            Document.project_id == project_id,
            Document.is_deleted.is_(False),
        )
        doc_result = await self.db.execute(doc_stmt)
        documents = list(doc_result.scalars().all())
        document_ids = {doc.id for doc in documents}
        total_docs = len(documents)

        if not document_ids:
            return []

        # Load all engagement sessions for these documents
        eng_stmt = select(DocumentEngagement).where(
            DocumentEngagement.document_id.in_(document_ids),
        )
        if deal_room_id is not None:
            # Filter by users who are members of the deal room
            from app.models.deal_rooms import DealRoomMember
            member_stmt = select(DealRoomMember.user_id).where(
                DealRoomMember.room_id == deal_room_id,
                DealRoomMember.is_deleted.is_(False),
            )
            member_result = await self.db.execute(member_stmt)
            member_user_ids = {row[0] for row in member_result.all()}
            if not member_user_ids:
                return []
            eng_stmt = eng_stmt.where(DocumentEngagement.user_id.in_(member_user_ids))

        eng_result = await self.db.execute(eng_stmt)
        engagements = list(eng_result.scalars().all())

        if not engagements:
            return []

        # Resolve user_id → org_id via User table (batch lookup)
        user_ids = {e.user_id for e in engagements}
        user_stmt = select(User.id, User.org_id).where(
            User.id.in_(user_ids),
            User.is_deleted.is_(False),
        )
        user_result = await self.db.execute(user_stmt)
        user_org_map: dict[uuid.UUID, uuid.UUID] = {
            row[0]: row[1] for row in user_result.all()
        }

        # Group engagements by investor_org_id
        by_investor: dict[uuid.UUID, list[DocumentEngagement]] = {}
        for eng in engagements:
            investor_org = user_org_map.get(eng.user_id)
            if investor_org is None:
                continue
            by_investor.setdefault(investor_org, []).append(eng)

        results: list[dict[str, Any]] = []
        for investor_org_id, investor_sessions in by_investor.items():
            total_sessions = len(investor_sessions)
            total_time = sum(s.total_time_seconds for s in investor_sessions)
            unique_docs = len({s.document_id for s in investor_sessions})
            downloads = sum(1 for s in investor_sessions if s.downloaded)
            last_activity = max(
                (s.closed_at or s.opened_at for s in investor_sessions),
                default=None,
            )

            docs_viewed_pct = (unique_docs / total_docs * 100) if total_docs > 0 else 0.0
            days_since_last = 0.0
            if last_activity:
                now = datetime.now(timezone.utc)
                last_aware = last_activity if last_activity.tzinfo else last_activity.replace(tzinfo=timezone.utc)
                days_since_last = (now - last_aware).total_seconds() / 86400

            score = self.compute_engagement_score(
                total_time_s=float(total_time),
                docs_viewed_pct=docs_viewed_pct,
                downloaded_count=downloads,
                days_since_last=days_since_last,
            )

            results.append({
                "investor_org_id": investor_org_id,
                "total_sessions": total_sessions,
                "total_time_seconds": total_time,
                "unique_documents_viewed": unique_docs,
                "total_documents_available": total_docs,
                "documents_downloaded": downloads,
                "last_activity_at": last_activity,
                "engagement_score": score,
            })

        # Sort by engagement_score descending
        results.sort(key=lambda x: x["engagement_score"] or 0.0, reverse=True)
        return results

    def compute_engagement_score(
        self,
        total_time_s: float,
        docs_viewed_pct: float,
        downloaded_count: int,
        days_since_last: float,
    ) -> float:
        """Return a 0–100 engagement score.

        Components:
          - Time score:     up to 30 pts for 1 hour+ of viewing
          - Coverage score: up to 30 pts for viewing all available documents
          - Download score: up to 20 pts for 5+ downloads
          - Recency score:  up to 20 pts for activity within the last 14 days
        """
        time_score = min(total_time_s / 3600, 1.0) * 30
        coverage_score = docs_viewed_pct * 0.3
        download_score = min(downloaded_count / 5, 1.0) * 20
        recency_score = max(0, (14 - days_since_last) / 14) * 20
        return round(time_score + coverage_score + download_score + recency_score, 1)

    async def get_page_heatmap(self, document_id: uuid.UUID) -> dict[int, int]:
        """Aggregate per-page dwell time across all sessions for a document."""
        sessions = await self._load_sessions_for_document(document_id)
        heatmap: dict[int, int] = {}
        for session in sessions:
            for entry in (session.pages_viewed or []):
                page = entry.get("page")
                t = entry.get("time_seconds", 0)
                if page is not None:
                    heatmap[page] = heatmap.get(page, 0) + t
        return heatmap

    # ── Internal helpers ───────────────────────────────────────────────────────

    async def _load_engagement(self, engagement_id: uuid.UUID) -> DocumentEngagement:
        """Load a DocumentEngagement row, enforcing org_id scoping."""
        result = await self.db.execute(
            select(DocumentEngagement).where(
                DocumentEngagement.id == engagement_id,
                DocumentEngagement.org_id == self.org_id,
            )
        )
        engagement = result.scalar_one_or_none()
        if not engagement:
            raise LookupError(f"Engagement session {engagement_id} not found")
        return engagement

    async def _load_sessions_for_document(
        self, document_id: uuid.UUID
    ) -> list[DocumentEngagement]:
        """Load all engagement sessions for a document scoped to this org."""
        result = await self.db.execute(
            select(DocumentEngagement).where(
                DocumentEngagement.document_id == document_id,
                DocumentEngagement.org_id == self.org_id,
            ).order_by(DocumentEngagement.opened_at.desc())
        )
        return list(result.scalars().all())
