"""ElasticSearch async client and index lifecycle management.

Fails open: if ES is unavailable, search returns empty results rather
than crashing the app.  Indices are created at startup if they don't exist.
"""

import structlog
from elasticsearch import AsyncElasticsearch

from app.core.config import settings

logger = structlog.get_logger()

# ── Index names ───────────────────────────────────────────────────────────────

INDEX_PROJECTS = "scr_projects"
INDEX_MARKETPLACE = "scr_marketplace"
INDEX_DOCUMENTS = "scr_documents"

# ── Index mappings ────────────────────────────────────────────────────────────

_MAPPINGS: dict[str, dict] = {
    INDEX_PROJECTS: {
        "mappings": {
            "properties": {
                "id": {"type": "keyword"},
                "org_id": {"type": "keyword"},
                "name": {"type": "text", "analyzer": "standard", "fields": {"keyword": {"type": "keyword"}}},
                "description": {"type": "text", "analyzer": "standard"},
                "project_type": {"type": "keyword"},
                "status": {"type": "keyword"},
                "stage": {"type": "keyword"},
                "geography_country": {"type": "keyword"},
                "total_investment_required": {"type": "double"},
                "is_published": {"type": "boolean"},
                "updated_at": {"type": "date"},
            }
        }
    },
    INDEX_MARKETPLACE: {
        "mappings": {
            "properties": {
                "id": {"type": "keyword"},
                "org_id": {"type": "keyword"},
                "project_id": {"type": "keyword"},
                "headline": {"type": "text", "analyzer": "standard"},
                "description": {"type": "text", "analyzer": "standard"},
                "listing_type": {"type": "keyword"},
                "sector": {"type": "keyword"},
                "status": {"type": "keyword"},
                "visibility": {"type": "keyword"},
                "updated_at": {"type": "date"},
            }
        }
    },
    INDEX_DOCUMENTS: {
        "mappings": {
            "properties": {
                "id": {"type": "keyword"},
                "org_id": {"type": "keyword"},
                "project_id": {"type": "keyword"},
                "filename": {"type": "text", "analyzer": "standard"},
                "extracted_text": {"type": "text", "analyzer": "standard"},
                "document_type": {"type": "keyword"},
                "status": {"type": "keyword"},
                "updated_at": {"type": "date"},
            }
        }
    },
}

# ── Singleton client ──────────────────────────────────────────────────────────

_client: AsyncElasticsearch | None = None


def get_es_client() -> AsyncElasticsearch:
    """Return the shared async ES client (lazy-initialised)."""
    global _client
    if _client is None:
        _client = AsyncElasticsearch(
            hosts=[settings.ELASTICSEARCH_URL],
            request_timeout=10,
            max_retries=2,
            retry_on_timeout=True,
        )
    return _client


async def setup_indices() -> None:
    """Create indices with mappings if they don't exist.

    Called from the FastAPI lifespan handler at startup.  Errors are logged
    but never raised — the app starts even if ES is down.
    """
    client = get_es_client()
    try:
        for index_name, body in _MAPPINGS.items():
            exists = await client.indices.exists(index=index_name)
            if not exists:
                await client.indices.create(index=index_name, body=body)
                logger.info("es.index_created", index=index_name)
            else:
                logger.debug("es.index_exists", index=index_name)
        logger.info("es.indices_ready")
    except Exception as exc:
        logger.warning("es.setup_failed", error=str(exc))


async def close_es_client() -> None:
    """Close the ES connection pool (called on shutdown)."""
    global _client
    if _client is not None:
        await _client.close()
        _client = None
        logger.info("es.client_closed")
