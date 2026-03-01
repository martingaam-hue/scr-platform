"""LineageService — records and queries data lineage for computed values."""

import uuid
from datetime import datetime
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lineage import DataLineage

logger = structlog.get_logger()


class LineageService:
    def __init__(self, db: AsyncSession, org_id: uuid.UUID):
        self.db = db
        self.org_id = org_id

    async def record_lineage(
        self,
        entity_type: str,
        entity_id: uuid.UUID,
        field_name: str,
        field_value: Any,
        source_type: str,
        source_id: uuid.UUID | None = None,
        source_detail: str | None = None,
        computation_chain: list[dict] | None = None,
        source_version: int | None = None,
        source_updated_at: datetime | None = None,
    ) -> DataLineage:
        """Record the source of a computed or stored value."""
        lineage = DataLineage(
            org_id=self.org_id,
            entity_type=entity_type,
            entity_id=entity_id,
            field_name=field_name,
            field_value=str(field_value)[:500] if field_value is not None else None,
            source_type=source_type,
            source_id=source_id,
            source_detail=source_detail,
            computation_chain=computation_chain,
            source_version=source_version,
            source_updated_at=source_updated_at,
        )
        self.db.add(lineage)
        await self.db.flush()
        return lineage

    async def get_lineage(
        self, entity_type: str, entity_id: uuid.UUID, field_name: str | None = None
    ) -> list[DataLineage]:
        """Get lineage records for an entity."""
        query = select(DataLineage).where(
            DataLineage.org_id == self.org_id,
            DataLineage.entity_type == entity_type,
            DataLineage.entity_id == entity_id,
        )
        if field_name:
            query = query.where(DataLineage.field_name == field_name)
        result = await self.db.execute(query.order_by(DataLineage.recorded_at.desc()))
        return list(result.scalars().all())

    async def get_full_trace(
        self, entity_type: str, entity_id: uuid.UUID, field_name: str
    ) -> dict[str, Any] | None:
        """Get complete derivation chain from raw source to final value."""
        lineage = await self.get_lineage(entity_type, entity_id, field_name)
        if not lineage:
            return None
        latest = lineage[0]

        trace: dict[str, Any] = {
            "value": latest.field_value,
            "source_type": latest.source_type,
            "source_detail": latest.source_detail,
            "last_updated": latest.recorded_at.isoformat(),
            "chain": latest.computation_chain or [],
        }

        # Enrich with document details if source is a document extraction
        if latest.source_type in ("document_extraction", "document") and latest.source_id:
            try:
                from app.models.dataroom import Document, DocumentExtraction
                if latest.source_type == "document_extraction":
                    extraction = await self.db.get(DocumentExtraction, latest.source_id)
                    if extraction:
                        doc = await self.db.get(Document, extraction.document_id)
                        if doc:
                            trace["document"] = {
                                "id": str(doc.id),
                                "name": doc.name,
                                "uploaded_at": doc.created_at.isoformat(),
                                "version": latest.source_version,
                            }
                else:
                    doc = await self.db.get(Document, latest.source_id)
                    if doc:
                        trace["document"] = {
                            "id": str(doc.id),
                            "name": doc.name,
                            "uploaded_at": doc.created_at.isoformat(),
                            "version": latest.source_version,
                        }
            except Exception as exc:
                logger.warning("lineage_doc_enrich_failed", error=str(exc))

        return trace
