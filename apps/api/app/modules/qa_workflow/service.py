"""Q&A Workflow — async service layer."""

import csv
import io
import uuid
from datetime import datetime, timedelta

import httpx
import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.qa import QAAnswer, QAQuestion
from app.modules.qa_workflow.schemas import (
    QAAnswerCreate,
    QAQuestionCreate,
    QAQuestionUpdate,
    QAStatsResponse,
)

logger = structlog.get_logger()

_OPEN_STATUSES = ["open", "assigned", "in_progress"]


class QAService:
    SLA_HOURS: dict[str, int] = {
        "urgent": 4,
        "high": 24,
        "normal": 72,
        "low": 168,
    }
    ROUTING: dict[str, str] = {
        "financial": "finance",
        "legal": "legal",
        "technical": "technical",
        "commercial": "commercial",
        "regulatory": "legal",
        "esg": "esg",
        "operational": "technical",
    }

    def __init__(self, db: AsyncSession, org_id: uuid.UUID) -> None:
        self.db = db
        self.org_id = org_id

    # ── Create ─────────────────────────────────────────────────────────────────

    async def create_question(
        self,
        project_id: uuid.UUID,
        asked_by: uuid.UUID,
        body: QAQuestionCreate,
    ) -> QAQuestion:
        # Auto-increment question_number per project
        result = await self.db.execute(
            select(func.coalesce(func.max(QAQuestion.question_number), 0)).where(
                QAQuestion.project_id == project_id,
                QAQuestion.org_id == self.org_id,
            )
        )
        next_number: int = result.scalar_one() + 1

        sla_hours = self.SLA_HOURS.get(body.priority, 72)
        sla_deadline = datetime.utcnow() + timedelta(hours=sla_hours)
        assigned_team = self.ROUTING.get(body.category)

        question = QAQuestion(
            org_id=self.org_id,
            project_id=project_id,
            deal_room_id=body.deal_room_id,
            question_number=next_number,
            question=body.question,
            category=body.category,
            priority=body.priority,
            asked_by=asked_by,
            assigned_team=assigned_team,
            status="open",
            sla_deadline=sla_deadline,
            tags=body.tags or [],
            linked_documents=[],
        )
        self.db.add(question)
        await self.db.flush()
        await self.db.refresh(question)
        logger.info(
            "qa_question_created",
            question_id=str(question.id),
            project_id=str(project_id),
            number=next_number,
        )
        return question

    # ── List / Get ──────────────────────────────────────────────────────────────

    async def list_questions(
        self,
        project_id: uuid.UUID,
        status: str | None = None,
        category: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[QAQuestion]:
        stmt = (
            select(QAQuestion)
            .where(
                QAQuestion.org_id == self.org_id,
                QAQuestion.project_id == project_id,
                QAQuestion.is_deleted.is_(False),
            )
            .order_by(QAQuestion.question_number.asc())
            .offset(skip)
            .limit(limit)
        )
        if status is not None:
            stmt = stmt.where(QAQuestion.status == status)
        if category is not None:
            stmt = stmt.where(QAQuestion.category == category)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_question(self, question_id: uuid.UUID) -> QAQuestion | None:
        stmt = (
            select(QAQuestion)
            .where(
                QAQuestion.id == question_id,
                QAQuestion.org_id == self.org_id,
                QAQuestion.is_deleted.is_(False),
            )
            .options(
                selectinload(QAQuestion.answers).execution_options(
                    populate_existing=True
                )
            )
            .execution_options(populate_existing=True)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    # ── Answer ──────────────────────────────────────────────────────────────────

    async def answer_question(
        self,
        question_id: uuid.UUID,
        answered_by: uuid.UUID,
        body: QAAnswerCreate,
    ) -> QAAnswer:
        question = await self.get_question(question_id)
        if question is None:
            raise ValueError(f"Question {question_id} not found")

        answer = QAAnswer(
            question_id=question_id,
            answered_by=answered_by,
            content=body.content,
            is_official=body.is_official,
            linked_documents=body.linked_documents or [],
        )
        self.db.add(answer)

        if body.is_official:
            question.status = "answered"  # type: ignore[assignment]
            question.answered_at = datetime.utcnow()  # type: ignore[assignment]

        await self.db.flush()
        await self.db.refresh(answer)
        logger.info(
            "qa_answer_created",
            answer_id=str(answer.id),
            question_id=str(question_id),
            is_official=body.is_official,
        )
        return answer

    # ── AI Suggestion ───────────────────────────────────────────────────────────

    async def suggest_answer(self, question_id: uuid.UUID) -> dict:
        question = await self.get_question(question_id)
        if question is None:
            return {"suggestion": "AI suggestion unavailable", "sources": []}

        prompt = (
            f"You are an investment due diligence analyst. "
            f"Please suggest a concise, professional answer for the following "
            f"{question.category} question from an investor during due diligence.\n\n"
            f"Question #{question.question_number}: {question.question}\n\n"
            f"Provide a clear, factual answer suitable for inclusion in a Q&A log."
        )

        try:
            resp = httpx.post(
                f"{settings.AI_GATEWAY_URL}/v1/completions",
                json={
                    "task_type": "suggest_qa_answer",
                    "messages": [{"role": "user", "content": prompt}],
                },
                headers={"X-API-Key": settings.AI_GATEWAY_API_KEY},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            suggestion = (
                data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )
            sources = data.get("sources", [])
            return {"suggestion": suggestion or "No suggestion returned.", "sources": sources}
        except Exception as exc:
            logger.warning("qa_suggest_answer_failed", error=str(exc), question_id=str(question_id))
            return {"suggestion": "AI suggestion unavailable", "sources": []}

    # ── Update / Assign ─────────────────────────────────────────────────────────

    async def update_question(
        self, question_id: uuid.UUID, body: QAQuestionUpdate
    ) -> QAQuestion:
        question = await self.get_question(question_id)
        if question is None:
            raise ValueError(f"Question {question_id} not found")

        if body.status is not None:
            question.status = body.status  # type: ignore[assignment]
        if body.assigned_to is not None:
            question.assigned_to = body.assigned_to  # type: ignore[assignment]
        if body.tags is not None:
            question.tags = body.tags  # type: ignore[assignment]

        await self.db.flush()
        await self.db.refresh(question)
        return question

    async def assign_question(
        self,
        question_id: uuid.UUID,
        assigned_to: uuid.UUID,
        assigned_team: str | None = None,
    ) -> QAQuestion:
        question = await self.get_question(question_id)
        if question is None:
            raise ValueError(f"Question {question_id} not found")

        question.assigned_to = assigned_to  # type: ignore[assignment]
        if assigned_team is not None:
            question.assigned_team = assigned_team  # type: ignore[assignment]
        if question.status == "open":
            question.status = "assigned"  # type: ignore[assignment]

        await self.db.flush()
        await self.db.refresh(question)
        logger.info(
            "qa_question_assigned",
            question_id=str(question_id),
            assigned_to=str(assigned_to),
        )
        return question

    # ── Stats ───────────────────────────────────────────────────────────────────

    async def get_stats(self, project_id: uuid.UUID) -> QAStatsResponse:
        now = datetime.utcnow()

        base_where = [
            QAQuestion.org_id == self.org_id,
            QAQuestion.project_id == project_id,
            QAQuestion.is_deleted.is_(False),
        ]

        total_result = await self.db.execute(
            select(func.count(QAQuestion.id)).where(*base_where)
        )
        total: int = total_result.scalar_one()

        open_result = await self.db.execute(
            select(func.count(QAQuestion.id)).where(
                *base_where,
                QAQuestion.status.in_(_OPEN_STATUSES),
            )
        )
        open_count: int = open_result.scalar_one()

        answered_result = await self.db.execute(
            select(func.count(QAQuestion.id)).where(
                *base_where,
                QAQuestion.status == "answered",
            )
        )
        answered_count: int = answered_result.scalar_one()

        overdue_result = await self.db.execute(
            select(func.count(QAQuestion.id)).where(
                *base_where,
                QAQuestion.status.in_(_OPEN_STATUSES),
                QAQuestion.sla_deadline < now,
            )
        )
        overdue_count: int = overdue_result.scalar_one()

        # Average response time in hours for answered questions
        avg_hours: float | None = None
        avg_result = await self.db.execute(
            select(QAQuestion.created_at, QAQuestion.answered_at).where(
                *base_where,
                QAQuestion.status == "answered",
                QAQuestion.answered_at.is_not(None),
            )
        )
        rows = avg_result.all()
        if rows:
            durations = [
                (row.answered_at - row.created_at).total_seconds() / 3600.0
                for row in rows
                if row.answered_at and row.created_at
            ]
            if durations:
                avg_hours = sum(durations) / len(durations)

        return QAStatsResponse(
            total=total,
            open=open_count,
            answered=answered_count,
            overdue=overdue_count,
            avg_response_hours=avg_hours,
        )

    # ── CSV Export ──────────────────────────────────────────────────────────────

    async def export_qa_log(self, project_id: uuid.UUID) -> bytes:
        questions = await self.list_questions(project_id, limit=10000)

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Q#", "Category", "Question", "Status", "Priority",
            "Team", "Answer", "Asked By", "Date",
        ])

        for q in questions:
            # Use the first official answer if present, otherwise first answer
            official = next((a for a in q.answers if a.is_official), None)
            first_answer = official or (q.answers[0] if q.answers else None)
            answer_text = first_answer.content if first_answer else ""

            writer.writerow([
                q.question_number,
                q.category,
                q.question,
                q.status,
                q.priority,
                q.assigned_team or "",
                answer_text,
                str(q.asked_by),
                q.created_at.strftime("%Y-%m-%d %H:%M") if q.created_at else "",
            ])

        return output.getvalue().encode("utf-8")

    # ── SLA Breach Check ────────────────────────────────────────────────────────

    async def check_sla_breaches(self) -> list[dict]:
        now = datetime.utcnow()

        stmt = select(QAQuestion).where(
            QAQuestion.org_id == self.org_id,
            QAQuestion.is_deleted.is_(False),
            QAQuestion.status.in_(_OPEN_STATUSES),
            QAQuestion.sla_deadline < now,
            QAQuestion.sla_breached.is_(False),
        )
        result = await self.db.execute(stmt)
        questions = list(result.scalars().all())

        breached = []
        for q in questions:
            q.sla_breached = True  # type: ignore[assignment]
            breached.append({"question_id": str(q.id), "project_id": str(q.project_id)})

        if questions:
            await self.db.flush()
            logger.info(
                "qa_sla_breaches_flagged",
                count=len(breached),
                org_id=str(self.org_id),
            )

        return breached
