"""Search service — ElasticSearch multi-index queries."""

from __future__ import annotations

import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.elasticsearch import (
    INDEX_DOCUMENTS,
    INDEX_MARKETPLACE,
    INDEX_PROJECTS,
    get_es_client,
)
from app.models.dataroom import Document, DocumentExtraction
from app.models.enums import DocumentStatus, ExtractionType, ListingStatus
from app.models.marketplace import Listing
from app.models.projects import Project
from app.modules.search.schemas import (
    DocumentHit,
    ListingHit,
    ProjectHit,
    ReindexResponse,
    SearchResponse,
)

logger = structlog.get_logger()


async def search(
    query: str,
    org_id: uuid.UUID,
    limit: int = 10,
) -> SearchResponse:
    """Multi-index search across projects, marketplace listings, and documents.

    Projects and documents are org-scoped.  Marketplace returns active public
    listings (cross-org) plus the caller's own active listings.
    Fails open — returns empty results if ES is unavailable.
    """
    client = get_es_client()
    projects: list[ProjectHit] = []
    listings: list[ListingHit] = []
    documents: list[DocumentHit] = []
    total = 0

    try:
        org_str = str(org_id)

        msearch_body: list[dict] = [
            # ── Projects (org-scoped) ─────────────────────────────────────────
            {"index": INDEX_PROJECTS},
            {
                "query": {
                    "bool": {
                        "must": [
                            {
                                "multi_match": {
                                    "query": query,
                                    "fields": ["name^3", "description"],
                                    "type": "best_fields",
                                    "fuzziness": "AUTO",
                                }
                            }
                        ],
                        "filter": [{"term": {"org_id": org_str}}],
                    }
                },
                "size": limit,
            },
            # ── Marketplace (public listings + caller's own active listings) ──
            {"index": INDEX_MARKETPLACE},
            {
                "query": {
                    "bool": {
                        "must": [
                            {
                                "multi_match": {
                                    "query": query,
                                    "fields": ["headline^2", "description"],
                                    "type": "best_fields",
                                    "fuzziness": "AUTO",
                                }
                            }
                        ],
                        "filter": [
                            {"term": {"status": "active"}},
                            {
                                "bool": {
                                    "should": [
                                        {"term": {"visibility": "public"}},
                                        {"term": {"org_id": org_str}},
                                    ],
                                    "minimum_should_match": 1,
                                }
                            },
                        ],
                    }
                },
                "size": limit,
            },
            # ── Documents (org-scoped, with highlighted excerpt) ──────────────
            {"index": INDEX_DOCUMENTS},
            {
                "query": {
                    "bool": {
                        "must": [
                            {
                                "multi_match": {
                                    "query": query,
                                    "fields": ["filename^2", "extracted_text"],
                                    "type": "best_fields",
                                    "fuzziness": "AUTO",
                                }
                            }
                        ],
                        "filter": [{"term": {"org_id": org_str}}],
                    }
                },
                "highlight": {
                    "fields": {
                        "extracted_text": {
                            "fragment_size": 200,
                            "number_of_fragments": 1,
                        }
                    },
                    "pre_tags": [""],
                    "post_tags": [""],
                },
                "size": limit,
            },
        ]

        response = await client.msearch(body=msearch_body)
        responses: list[dict] = response.get("responses", [])

        # Projects
        if responses and "hits" in responses[0]:
            r = responses[0]
            total += r["hits"]["total"]["value"]
            for hit in r["hits"]["hits"]:
                src = hit["_source"]
                projects.append(
                    ProjectHit(
                        id=src["id"],
                        org_id=src["org_id"],
                        name=src["name"],
                        project_type=src.get("project_type"),
                        status=src.get("status"),
                        stage=src.get("stage"),
                        geography_country=src.get("geography_country"),
                        total_investment_required=src.get("total_investment_required"),
                        score=hit["_score"] or 0.0,
                    )
                )

        # Listings
        if len(responses) > 1 and "hits" in responses[1]:
            r = responses[1]
            total += r["hits"]["total"]["value"]
            for hit in r["hits"]["hits"]:
                src = hit["_source"]
                listings.append(
                    ListingHit(
                        id=src["id"],
                        org_id=src["org_id"],
                        project_id=src.get("project_id"),
                        headline=src["headline"],
                        listing_type=src.get("listing_type"),
                        sector=src.get("sector"),
                        score=hit["_score"] or 0.0,
                    )
                )

        # Documents
        if len(responses) > 2 and "hits" in responses[2]:
            r = responses[2]
            total += r["hits"]["total"]["value"]
            for hit in r["hits"]["hits"]:
                src = hit["_source"]
                highlights = hit.get("highlight", {}).get("extracted_text", [])
                snippet = highlights[0] if highlights else None
                documents.append(
                    DocumentHit(
                        id=src["id"],
                        org_id=src["org_id"],
                        project_id=src.get("project_id"),
                        filename=src["filename"],
                        document_type=src.get("document_type"),
                        snippet=snippet,
                        score=hit["_score"] or 0.0,
                    )
                )

    except Exception as exc:
        logger.warning("search.failed", error=str(exc), query=query)

    return SearchResponse(
        query=query,
        total=total,
        projects=projects,
        listings=listings,
        documents=documents,
    )


async def reindex_all(db: AsyncSession) -> ReindexResponse:
    """Bulk reindex all projects, listings, and documents into ElasticSearch."""
    client = get_es_client()
    errors: list[str] = []
    indexed_projects = 0
    indexed_listings = 0
    indexed_documents = 0

    # ── Projects ──────────────────────────────────────────────────────────────
    try:
        result = await db.execute(
            select(Project).where(Project.is_deleted.is_(False))
        )
        project_rows = result.scalars().all()

        if project_rows:
            actions: list[dict] = []
            for p in project_rows:
                actions.append({"index": {"_index": INDEX_PROJECTS, "_id": str(p.id)}})
                actions.append(
                    {
                        "id": str(p.id),
                        "org_id": str(p.org_id),
                        "name": p.name,
                        "description": p.description or "",
                        "project_type": p.project_type.value if p.project_type else None,
                        "status": p.status.value if p.status else None,
                        "stage": p.stage.value if p.stage else None,
                        "geography_country": p.geography_country,
                        "total_investment_required": float(p.total_investment_required)
                        if p.total_investment_required
                        else None,
                        "is_published": p.is_published,
                        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
                    }
                )
            resp = await client.bulk(body=actions)
            if resp.get("errors"):
                for item in resp.get("items", []):
                    err = item.get("index", {}).get("error")
                    if err:
                        errors.append(f"project:{item['index']['_id']}: {err}")
            indexed_projects = len(project_rows)
    except Exception as exc:
        errors.append(f"projects: {exc}")

    # ── Listings ──────────────────────────────────────────────────────────────
    try:
        result = await db.execute(
            select(Listing).where(
                Listing.is_deleted.is_(False),
                Listing.status == ListingStatus.ACTIVE,
            )
        )
        listing_rows = result.scalars().all()

        if listing_rows:
            actions = []
            for li in listing_rows:
                actions.append({"index": {"_index": INDEX_MARKETPLACE, "_id": str(li.id)}})
                actions.append(
                    {
                        "id": str(li.id),
                        "org_id": str(li.org_id),
                        "project_id": str(li.project_id) if li.project_id else None,
                        "headline": li.title,  # model field `title` → ES field `headline`
                        "description": li.description or "",
                        "listing_type": li.listing_type.value if li.listing_type else None,
                        "sector": li.details.get("sector") if li.details else None,
                        "status": li.status.value if li.status else None,
                        "visibility": li.visibility.value if li.visibility else None,
                        "updated_at": li.updated_at.isoformat() if li.updated_at else None,
                    }
                )
            resp = await client.bulk(body=actions)
            if resp.get("errors"):
                for item in resp.get("items", []):
                    err = item.get("index", {}).get("error")
                    if err:
                        errors.append(f"listing:{item['index']['_id']}: {err}")
            indexed_listings = len(listing_rows)
    except Exception as exc:
        errors.append(f"listings: {exc}")

    # ── Documents ─────────────────────────────────────────────────────────────
    try:
        result = await db.execute(
            select(Document)
            .where(
                Document.is_deleted.is_(False),
                Document.status == DocumentStatus.READY,
            )
            .options(joinedload(Document.extractions))
        )
        doc_rows = result.unique().scalars().all()

        if doc_rows:
            actions = []
            for d in doc_rows:
                # Use SUMMARY extraction text when available
                extracted_text = ""
                for ext in d.extractions:
                    if ext.extraction_type == ExtractionType.SUMMARY:
                        extracted_text = (
                            ext.result.get("text")
                            or ext.result.get("summary")
                            or ""
                        )
                        break

                actions.append({"index": {"_index": INDEX_DOCUMENTS, "_id": str(d.id)}})
                actions.append(
                    {
                        "id": str(d.id),
                        "org_id": str(d.org_id),
                        "project_id": str(d.project_id) if d.project_id else None,
                        "filename": d.name,  # model field `name` → ES field `filename`
                        "extracted_text": extracted_text,
                        "document_type": d.classification.value if d.classification else None,
                        "status": d.status.value if d.status else None,
                        "updated_at": d.updated_at.isoformat() if d.updated_at else None,
                    }
                )
            resp = await client.bulk(body=actions)
            if resp.get("errors"):
                for item in resp.get("items", []):
                    err = item.get("index", {}).get("error")
                    if err:
                        errors.append(f"document:{item['index']['_id']}: {err}")
            indexed_documents = len(doc_rows)
    except Exception as exc:
        errors.append(f"documents: {exc}")

    logger.info(
        "search.reindex_complete",
        projects=indexed_projects,
        listings=indexed_listings,
        documents=indexed_documents,
        errors=len(errors),
    )
    return ReindexResponse(
        indexed_projects=indexed_projects,
        indexed_listings=indexed_listings,
        indexed_documents=indexed_documents,
        errors=errors,
    )
