"""Tests for the search module: ES multi-index query, fail-open, org scoping."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.search import service as search_service
from app.modules.search.schemas import SearchResponse
from tests.conftest import SAMPLE_ORG_ID

pytestmark = pytest.mark.asyncio

OTHER_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000066")

# ── Mock ES response builder ──────────────────────────────────────────────────

_SAMPLE_PROJECT_ID = str(uuid.uuid4())
_SAMPLE_LISTING_ID = str(uuid.uuid4())
_SAMPLE_DOCUMENT_ID = str(uuid.uuid4())


def _make_es_hit(source: dict, score: float = 1.5) -> dict:
    return {"_score": score, "_source": source}


def _make_msearch_response(
    project_hits: list[dict] | None = None,
    listing_hits: list[dict] | None = None,
    document_hits: list[dict] | None = None,
) -> dict:
    """Build a synthetic msearch response with three index buckets."""

    def _bucket(hits: list[dict]) -> dict:
        return {"hits": {"total": {"value": len(hits)}, "hits": hits}}

    return {
        "responses": [
            _bucket(project_hits or []),
            _bucket(listing_hits or []),
            _bucket(document_hits or []),
        ]
    }


# ── Service-level tests ───────────────────────────────────────────────────────


async def test_search_returns_empty_when_es_not_configured():
    """search() fails open and returns empty SearchResponse when ES client is None."""
    with patch("app.modules.search.service.get_es_client", return_value=None):
        result = await search_service.search("solar energy", SAMPLE_ORG_ID)

    assert isinstance(result, SearchResponse)
    assert result.total == 0
    assert result.projects == []
    assert result.listings == []
    assert result.documents == []
    assert result.query == "solar energy"


async def test_search_returns_project_hits():
    """search() maps ES project hits to ProjectHit objects correctly."""
    project_source = {
        "id": _SAMPLE_PROJECT_ID,
        "org_id": str(SAMPLE_ORG_ID),
        "name": "Solar Farm Kenya",
        "project_type": "solar",
        "status": "active",
        "stage": "development",
        "geography_country": "Kenya",
        "total_investment_required": 5_000_000.0,
    }
    mock_response = _make_msearch_response(
        project_hits=[_make_es_hit(project_source, score=2.7)]
    )

    mock_client = AsyncMock()
    mock_client.msearch = AsyncMock(return_value=mock_response)

    with patch("app.modules.search.service.get_es_client", return_value=mock_client):
        result = await search_service.search("solar", SAMPLE_ORG_ID)

    assert result.total == 1
    assert len(result.projects) == 1
    hit = result.projects[0]
    assert hit.id == _SAMPLE_PROJECT_ID
    assert hit.name == "Solar Farm Kenya"
    assert hit.project_type == "solar"
    assert hit.score == pytest.approx(2.7)


async def test_search_returns_listing_and_document_hits():
    """search() maps listing and document hits alongside project hits."""
    listing_source = {
        "id": _SAMPLE_LISTING_ID,
        "org_id": str(SAMPLE_ORG_ID),
        "project_id": _SAMPLE_PROJECT_ID,
        "headline": "Wind Investment Opportunity",
        "listing_type": "equity",
        "sector": "energy",
    }
    document_source = {
        "id": _SAMPLE_DOCUMENT_ID,
        "org_id": str(SAMPLE_ORG_ID),
        "project_id": _SAMPLE_PROJECT_ID,
        "filename": "feasibility_study.pdf",
        "document_type": "technical_study",
    }
    mock_response = _make_msearch_response(
        listing_hits=[_make_es_hit(listing_source)],
        document_hits=[_make_es_hit(document_source)],
    )

    mock_client = AsyncMock()
    mock_client.msearch = AsyncMock(return_value=mock_response)

    with patch("app.modules.search.service.get_es_client", return_value=mock_client):
        result = await search_service.search("wind", SAMPLE_ORG_ID)

    assert len(result.listings) == 1
    assert result.listings[0].headline == "Wind Investment Opportunity"
    assert result.listings[0].sector == "energy"

    assert len(result.documents) == 1
    assert result.documents[0].filename == "feasibility_study.pdf"
    assert result.documents[0].document_type == "technical_study"


async def test_search_document_hit_includes_snippet():
    """Document hits include the highlighted snippet from extracted_text."""
    document_source = {
        "id": _SAMPLE_DOCUMENT_ID,
        "org_id": str(SAMPLE_ORG_ID),
        "project_id": None,
        "filename": "annual_report.pdf",
        "document_type": "financial_statement",
    }
    hit_with_highlight = {
        "_score": 1.2,
        "_source": document_source,
        "highlight": {
            "extracted_text": ["...revenue grew 40% year-on-year driven by solar assets..."]
        },
    }
    mock_response = _make_msearch_response(document_hits=[hit_with_highlight])

    mock_client = AsyncMock()
    mock_client.msearch = AsyncMock(return_value=mock_response)

    with patch("app.modules.search.service.get_es_client", return_value=mock_client):
        result = await search_service.search("revenue", SAMPLE_ORG_ID)

    doc = result.documents[0]
    assert doc.snippet is not None
    assert "revenue" in doc.snippet


async def test_search_returns_empty_results_on_no_matches():
    """search() handles an msearch response with zero hits without errors."""
    mock_response = _make_msearch_response()

    mock_client = AsyncMock()
    mock_client.msearch = AsyncMock(return_value=mock_response)

    with patch("app.modules.search.service.get_es_client", return_value=mock_client):
        result = await search_service.search("xyzzy_no_match_term_abc", SAMPLE_ORG_ID)

    assert result.total == 0
    assert result.projects == []
    assert result.listings == []
    assert result.documents == []


async def test_search_fails_open_on_es_exception():
    """search() swallows ES exceptions and returns empty results (fail-open)."""
    mock_client = AsyncMock()
    mock_client.msearch = AsyncMock(side_effect=Exception("ES connection refused"))

    with patch("app.modules.search.service.get_es_client", return_value=mock_client):
        result = await search_service.search("anything", SAMPLE_ORG_ID)

    # Should not raise — returns empty SearchResponse
    assert isinstance(result, SearchResponse)
    assert result.total == 0


async def test_search_org_scoping_passed_to_query():
    """search() sends the org_id as a filter term in the ES msearch body."""
    mock_client = AsyncMock()
    mock_client.msearch = AsyncMock(return_value=_make_msearch_response())
    captured_body = {}

    async def capture_msearch(*, body):
        captured_body["body"] = body
        return _make_msearch_response()

    mock_client.msearch = capture_msearch

    with patch("app.modules.search.service.get_es_client", return_value=mock_client):
        await search_service.search("test query", SAMPLE_ORG_ID, limit=5)

    body = captured_body["body"]
    # body is a flat list: [header, query, header, query, ...]
    # Find the project query dict (index 1) and check the org filter
    project_query = body[1]
    filters = project_query["query"]["bool"]["filter"]
    org_filter = next(f for f in filters if "term" in f and "org_id" in f["term"])
    assert org_filter["term"]["org_id"] == str(SAMPLE_ORG_ID)


# ── HTTP endpoint tests ───────────────────────────────────────────────────────


async def test_http_search_returns_200_with_es_none(
    authenticated_client: AsyncClient, db: AsyncSession, sample_org, sample_user
):
    """GET /v1/search?q=... returns 200 even when ES is not configured."""
    with patch("app.modules.search.service.get_es_client", return_value=None):
        resp = await authenticated_client.get("/v1/search", params={"q": "solar"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["query"] == "solar"
    assert data["total"] == 0
    assert "projects" in data
    assert "listings" in data
    assert "documents" in data


async def test_http_search_returns_results_from_es(
    authenticated_client: AsyncClient, db: AsyncSession, sample_org, sample_user
):
    """GET /v1/search?q=... maps ES hits to response shape."""
    project_source = {
        "id": _SAMPLE_PROJECT_ID,
        "org_id": str(SAMPLE_ORG_ID),
        "name": "Hydro Power Project",
        "project_type": "hydro",
        "status": "active",
        "stage": "concept",
        "geography_country": "Ghana",
        "total_investment_required": 2_000_000.0,
    }
    mock_response = _make_msearch_response(
        project_hits=[_make_es_hit(project_source, score=3.0)]
    )
    mock_client = AsyncMock()
    mock_client.msearch = AsyncMock(return_value=mock_response)

    with patch("app.modules.search.service.get_es_client", return_value=mock_client):
        resp = await authenticated_client.get("/v1/search", params={"q": "hydro"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert len(data["projects"]) == 1
    assert data["projects"][0]["name"] == "Hydro Power Project"


async def test_http_search_missing_query_returns_422(
    authenticated_client: AsyncClient, db: AsyncSession, sample_org, sample_user
):
    """GET /v1/search without ?q= returns 422 (required param)."""
    resp = await authenticated_client.get("/v1/search")
    assert resp.status_code == 422
