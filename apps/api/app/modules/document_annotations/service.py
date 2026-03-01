"""Service layer for the Document Annotations module."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document_annotations import DocumentAnnotation
from app.modules.document_annotations.schemas import (
    CreateAnnotationRequest,
    UpdateAnnotationRequest,
)


class AnnotationService:
    """Business logic for creating, reading, updating, and deleting annotations."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create_annotation(
        self,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        data: CreateAnnotationRequest,
    ) -> DocumentAnnotation:
        """Create a new annotation and persist it."""
        annotation = DocumentAnnotation(
            org_id=org_id,
            document_id=data.document_id,
            created_by=user_id,
            annotation_type=data.annotation_type,
            page_number=data.page_number,
            position=data.position,
            content=data.content,
            color=data.color,
            linked_qa_question_id=data.linked_qa_question_id,
            linked_citation_id=data.linked_citation_id,
            is_private=data.is_private,
        )
        self._db.add(annotation)
        await self._db.commit()
        await self._db.refresh(annotation)
        return annotation

    async def list_annotations(
        self,
        org_id: uuid.UUID,
        document_id: uuid.UUID,
        page_number: int | None = None,
    ) -> list[DocumentAnnotation]:
        """Return all annotations for a document, optionally filtered by page."""
        conditions = [
            DocumentAnnotation.org_id == org_id,
            DocumentAnnotation.document_id == document_id,
        ]
        if page_number is not None:
            conditions.append(DocumentAnnotation.page_number == page_number)

        stmt = (
            select(DocumentAnnotation)
            .where(and_(*conditions))
            .order_by(DocumentAnnotation.page_number, DocumentAnnotation.created_at)
        )
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def get_annotation(
        self,
        org_id: uuid.UUID,
        annotation_id: uuid.UUID,
    ) -> DocumentAnnotation | None:
        """Fetch a single annotation by ID, scoped to the org."""
        stmt = select(DocumentAnnotation).where(
            and_(
                DocumentAnnotation.id == annotation_id,
                DocumentAnnotation.org_id == org_id,
            )
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_annotation(
        self,
        org_id: uuid.UUID,
        annotation_id: uuid.UUID,
        user_id: uuid.UUID,
        data: UpdateAnnotationRequest,
    ) -> DocumentAnnotation | None:
        """Update mutable fields on an annotation. Returns None if not found."""
        annotation = await self.get_annotation(org_id, annotation_id)
        if annotation is None:
            return None

        if data.content is not None:
            annotation.content = data.content
        if data.color is not None:
            annotation.color = data.color
        if data.is_private is not None:
            annotation.is_private = data.is_private

        annotation.updated_at = datetime.utcnow()
        await self._db.commit()
        await self._db.refresh(annotation)
        return annotation

    async def delete_annotation(
        self,
        org_id: uuid.UUID,
        annotation_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """Delete an annotation. Only the creator may delete their annotation.

        Returns True if deleted, False if not found or not the owner.
        """
        annotation = await self.get_annotation(org_id, annotation_id)
        if annotation is None:
            return False
        if annotation.created_by != user_id:
            return False
        await self._db.delete(annotation)
        await self._db.commit()
        return True
