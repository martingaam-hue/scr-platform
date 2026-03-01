"""Comprehensive tests for the Data Room Management module."""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.main import app
from app.models.core import Organization, User
from app.models.dataroom import (
    Document,
    DocumentAccessLog,
    DocumentExtraction,
    DocumentFolder,
    ShareLink,
)
from app.models.enums import (
    DocumentAccessAction,
    DocumentClassification,
    DocumentStatus,
    ExtractionType,
    OrgType,
    ProjectStatus,
    ProjectStage,
    ProjectType,
    UserRole,
)
from app.models.projects import Project
from app.modules.dataroom import service
from app.modules.dataroom.schemas import ALLOWED_FILE_TYPES, MAX_FILE_SIZE_BYTES
from app.schemas.auth import CurrentUser

# ── Test Data ────────────────────────────────────────────────────────────────

ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
VIEWER_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000003")
PROJECT_ID = uuid.UUID("00000000-0000-0000-0000-000000000010")
OTHER_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000099")

CURRENT_USER = CurrentUser(
    user_id=USER_ID,
    org_id=ORG_ID,
    role=UserRole.ADMIN,
    email="test@example.com",
    external_auth_id="user_test_123",
)

VIEWER_USER = CurrentUser(
    user_id=VIEWER_USER_ID,
    org_id=ORG_ID,
    role=UserRole.VIEWER,
    email="viewer@example.com",
    external_auth_id="user_test_viewer",
)

SAMPLE_CHECKSUM = hashlib.sha256(b"test file content").hexdigest()


# ── Fixtures ─────────────────────────────────────────────────────────────────


def _override_auth(user: CurrentUser):
    """Create a get_current_user override for the given user."""
    async def _override():
        return user
    return _override


@pytest.fixture
async def seed_data(db: AsyncSession) -> None:
    """Seed Organization, Users, and Project for FK constraints."""
    org = Organization(id=ORG_ID, name="Test Org", slug="test-org", type=OrgType.ALLY)
    db.add(org)

    other_org = Organization(
        id=OTHER_ORG_ID, name="Other Org", slug="other-org", type=OrgType.INVESTOR
    )
    db.add(other_org)

    user = User(
        id=USER_ID,
        org_id=ORG_ID,
        email="test@example.com",
        full_name="Test User",
        role=UserRole.ADMIN,
        external_auth_id="user_test_123",
        is_active=True,
    )
    db.add(user)

    viewer = User(
        id=VIEWER_USER_ID,
        org_id=ORG_ID,
        email="viewer@example.com",
        full_name="Viewer User",
        role=UserRole.VIEWER,
        external_auth_id="user_test_viewer",
        is_active=True,
    )
    db.add(viewer)

    from decimal import Decimal

    project = Project(
        id=PROJECT_ID,
        org_id=ORG_ID,
        name="Test Project",
        slug="test-project",
        description="Test project for dataroom tests",
        project_type=ProjectType.SOLAR,
        status=ProjectStatus.ACTIVE,
        stage=ProjectStage.DEVELOPMENT,
        geography_country="US",
        total_investment_required=Decimal("1000000"),
    )
    db.add(project)
    await db.flush()


@pytest.fixture
def mock_s3():
    """Mock boto3 S3 client for all dataroom tests."""
    mock_client = MagicMock()
    mock_client.generate_presigned_url.return_value = "https://s3.example.com/presigned-url"
    mock_client.head_object.return_value = {"ContentLength": 1024}
    mock_client.exceptions.ClientError = Exception

    with patch("app.modules.dataroom.service.boto3") as mock_boto3:
        mock_boto3.client.return_value = mock_client
        yield mock_client


@pytest.fixture
async def client_with_db(db: AsyncSession, mock_s3, seed_data) -> AsyncClient:
    """AsyncClient with DB session and S3 mock injected, authenticated as ADMIN."""
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = _override_auth(CURRENT_USER)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
async def viewer_client(db: AsyncSession, mock_s3, seed_data) -> AsyncClient:
    """AsyncClient authenticated as VIEWER (read-only)."""
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = _override_auth(VIEWER_USER)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
async def sample_folder(db: AsyncSession, seed_data) -> DocumentFolder:
    """Create a test folder."""
    folder = DocumentFolder(
        id=uuid.uuid4(),
        org_id=ORG_ID,
        project_id=PROJECT_ID,
        name="Test Folder",
    )
    db.add(folder)
    await db.flush()
    return folder


@pytest.fixture
async def sample_document(db: AsyncSession, seed_data) -> Document:
    """Create a test document in READY state."""
    doc = Document(
        id=uuid.uuid4(),
        org_id=ORG_ID,
        project_id=PROJECT_ID,
        name="test-report.pdf",
        file_type="pdf",
        mime_type="application/pdf",
        s3_key=f"{ORG_ID}/{PROJECT_ID}/root/{uuid.uuid4()}_test-report.pdf",
        s3_bucket="scr-documents",
        file_size_bytes=1024,
        status=DocumentStatus.READY,
        uploaded_by=USER_ID,
        checksum_sha256=SAMPLE_CHECKSUM,
    )
    db.add(doc)
    await db.flush()
    return doc


@pytest.fixture
async def sample_extraction(db: AsyncSession, sample_document: Document) -> DocumentExtraction:
    """Create a test extraction."""
    extraction = DocumentExtraction(
        id=uuid.uuid4(),
        document_id=sample_document.id,
        extraction_type=ExtractionType.SUMMARY,
        result={"summary": "Test summary", "word_count": 100},
        model_used="test-model",
        confidence_score=0.9,
        tokens_used=500,
        processing_time_ms=200,
    )
    db.add(extraction)
    await db.flush()
    return extraction


@pytest.fixture
async def sample_share(db: AsyncSession, sample_document: Document) -> ShareLink:
    """Create a test share link."""
    share = ShareLink(
        id=uuid.uuid4(),
        document_id=sample_document.id,
        org_id=ORG_ID,
        created_by=USER_ID,
        share_token=secrets.token_urlsafe(32),
        allow_download=True,
        watermark_enabled=False,
    )
    db.add(share)
    await db.flush()
    return share


# ═══════════════════════════════════════════════════════════════════════════════
# FOLDER TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestFolders:
    async def test_create_folder(self, client_with_db: AsyncClient):
        resp = await client_with_db.post("/v1/dataroom/folders", json={
            "name": "Financial Reports",
            "project_id": str(PROJECT_ID),
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Financial Reports"
        assert data["project_id"] == str(PROJECT_ID)
        assert data["parent_folder_id"] is None

    async def test_create_subfolder(
        self, client_with_db: AsyncClient, sample_folder: DocumentFolder
    ):
        resp = await client_with_db.post("/v1/dataroom/folders", json={
            "name": "Q4 Reports",
            "project_id": str(PROJECT_ID),
            "parent_folder_id": str(sample_folder.id),
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["parent_folder_id"] == str(sample_folder.id)

    async def test_create_folder_empty_name_rejected(self, client_with_db: AsyncClient):
        resp = await client_with_db.post("/v1/dataroom/folders", json={
            "name": "",
            "project_id": str(PROJECT_ID),
        })
        assert resp.status_code == 422

    async def test_get_folder_tree(
        self, client_with_db: AsyncClient, sample_folder: DocumentFolder
    ):
        resp = await client_with_db.get(f"/v1/dataroom/folders/{PROJECT_ID}")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["name"] == "Test Folder"

    async def test_update_folder_rename(
        self, client_with_db: AsyncClient, sample_folder: DocumentFolder
    ):
        resp = await client_with_db.put(
            f"/v1/dataroom/folders/{sample_folder.id}",
            json={"name": "Renamed Folder"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Renamed Folder"

    async def test_delete_empty_folder(
        self, client_with_db: AsyncClient, sample_folder: DocumentFolder
    ):
        resp = await client_with_db.delete(f"/v1/dataroom/folders/{sample_folder.id}")
        assert resp.status_code == 204

    async def test_delete_folder_with_documents_rejected(
        self,
        client_with_db: AsyncClient,
        sample_folder: DocumentFolder,
        db: AsyncSession,
    ):
        # Add a doc to the folder
        doc = Document(
            org_id=ORG_ID,
            project_id=PROJECT_ID,
            folder_id=sample_folder.id,
            name="doc.pdf",
            file_type="pdf",
            mime_type="application/pdf",
            s3_key="test/key",
            s3_bucket="scr-documents",
            file_size_bytes=100,
            status=DocumentStatus.READY,
            uploaded_by=USER_ID,
            checksum_sha256=SAMPLE_CHECKSUM,
        )
        db.add(doc)
        await db.flush()

        resp = await client_with_db.delete(f"/v1/dataroom/folders/{sample_folder.id}")
        assert resp.status_code == 400
        assert "contains documents" in resp.json()["detail"]

    async def test_delete_nonexistent_folder(self, client_with_db: AsyncClient):
        fake_id = uuid.uuid4()
        resp = await client_with_db.delete(f"/v1/dataroom/folders/{fake_id}")
        assert resp.status_code == 404

    async def test_folder_self_parent_rejected(
        self, client_with_db: AsyncClient, sample_folder: DocumentFolder
    ):
        resp = await client_with_db.put(
            f"/v1/dataroom/folders/{sample_folder.id}",
            json={"parent_folder_id": str(sample_folder.id)},
        )
        assert resp.status_code == 400
        assert "own parent" in resp.json()["detail"]


# ═══════════════════════════════════════════════════════════════════════════════
# DOCUMENT UPLOAD TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestDocumentUpload:
    async def test_presigned_upload(self, client_with_db: AsyncClient):
        resp = await client_with_db.post("/v1/dataroom/upload/presigned", json={
            "file_name": "report.pdf",
            "file_type": "pdf",
            "file_size_bytes": 5000,
            "project_id": str(PROJECT_ID),
            "checksum_sha256": SAMPLE_CHECKSUM,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "upload_url" in data
        assert "document_id" in data
        assert "s3_key" in data
        assert str(ORG_ID) in data["s3_key"]

    async def test_upload_invalid_file_type(self, client_with_db: AsyncClient):
        resp = await client_with_db.post("/v1/dataroom/upload/presigned", json={
            "file_name": "malware.exe",
            "file_type": "exe",
            "file_size_bytes": 5000,
            "project_id": str(PROJECT_ID),
            "checksum_sha256": SAMPLE_CHECKSUM,
        })
        assert resp.status_code == 422
        assert "not allowed" in resp.json()["detail"][0]["msg"]

    async def test_upload_exceeds_max_size(self, client_with_db: AsyncClient):
        resp = await client_with_db.post("/v1/dataroom/upload/presigned", json={
            "file_name": "huge.pdf",
            "file_type": "pdf",
            "file_size_bytes": MAX_FILE_SIZE_BYTES + 1,
            "project_id": str(PROJECT_ID),
            "checksum_sha256": SAMPLE_CHECKSUM,
        })
        assert resp.status_code == 422
        assert "100 MB" in resp.json()["detail"][0]["msg"]

    async def test_confirm_upload(
        self, client_with_db: AsyncClient, db: AsyncSession, mock_s3
    ):
        # Create a doc in UPLOADING state
        doc = Document(
            org_id=ORG_ID,
            project_id=PROJECT_ID,
            name="upload-test.pdf",
            file_type="pdf",
            mime_type="application/pdf",
            s3_key="test/upload-test.pdf",
            s3_bucket="scr-documents",
            file_size_bytes=1024,
            status=DocumentStatus.UPLOADING,
            uploaded_by=USER_ID,
            checksum_sha256=SAMPLE_CHECKSUM,
        )
        db.add(doc)
        await db.flush()

        with patch("app.modules.dataroom.tasks.process_document") as mock_task:
            mock_task.delay = MagicMock()
            resp = await client_with_db.post("/v1/dataroom/upload/confirm", json={
                "document_id": str(doc.id),
            })

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "processing"
        assert data["document_id"] == str(doc.id)

    async def test_confirm_upload_already_processing(
        self, client_with_db: AsyncClient, sample_document: Document
    ):
        # sample_document is in READY state, not UPLOADING
        resp = await client_with_db.post("/v1/dataroom/upload/confirm", json={
            "document_id": str(sample_document.id),
        })
        assert resp.status_code == 400

    async def test_viewer_cannot_upload(self, viewer_client: AsyncClient):
        resp = await viewer_client.post("/v1/dataroom/upload/presigned", json={
            "file_name": "report.pdf",
            "file_type": "pdf",
            "file_size_bytes": 5000,
            "project_id": str(PROJECT_ID),
            "checksum_sha256": SAMPLE_CHECKSUM,
        })
        assert resp.status_code == 403

    async def test_all_allowed_file_types(self, client_with_db: AsyncClient):
        for ft in ALLOWED_FILE_TYPES:
            resp = await client_with_db.post("/v1/dataroom/upload/presigned", json={
                "file_name": f"test.{ft}",
                "file_type": ft,
                "file_size_bytes": 1000,
                "project_id": str(PROJECT_ID),
                "checksum_sha256": SAMPLE_CHECKSUM,
            })
            assert resp.status_code == 200, f"Failed for file type: {ft}"


# ═══════════════════════════════════════════════════════════════════════════════
# DOCUMENT CRUD TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestDocumentCRUD:
    async def test_list_documents(
        self, client_with_db: AsyncClient, sample_document: Document
    ):
        resp = await client_with_db.get(
            "/v1/dataroom/documents",
            params={"project_id": str(PROJECT_ID)},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1
        assert data["items"][0]["name"] == "test-report.pdf"

    async def test_list_documents_pagination(
        self, client_with_db: AsyncClient, db: AsyncSession
    ):
        # Create 5 documents
        for i in range(5):
            db.add(Document(
                org_id=ORG_ID,
                project_id=PROJECT_ID,
                name=f"doc-{i}.pdf",
                file_type="pdf",
                mime_type="application/pdf",
                s3_key=f"test/doc-{i}.pdf",
                s3_bucket="scr-documents",
                file_size_bytes=100,
                status=DocumentStatus.READY,
                uploaded_by=USER_ID,
                checksum_sha256=SAMPLE_CHECKSUM,
            ))
        await db.flush()

        resp = await client_with_db.get(
            "/v1/dataroom/documents",
            params={"project_id": str(PROJECT_ID), "page": 1, "page_size": 2},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["page_size"] == 2
        assert len(data["items"]) == 2
        assert data["total"] == 5

    async def test_list_documents_search(
        self, client_with_db: AsyncClient, sample_document: Document
    ):
        resp = await client_with_db.get(
            "/v1/dataroom/documents",
            params={"search": "test-report"},
        )
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    async def test_list_documents_filter_by_status(
        self, client_with_db: AsyncClient, sample_document: Document
    ):
        resp = await client_with_db.get(
            "/v1/dataroom/documents",
            params={"status": "ready"},
        )
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    async def test_get_document_detail(
        self, client_with_db: AsyncClient, sample_document: Document, sample_extraction
    ):
        resp = await client_with_db.get(f"/v1/dataroom/documents/{sample_document.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(sample_document.id)
        assert data["name"] == "test-report.pdf"
        assert len(data["extractions"]) == 1

    async def test_get_nonexistent_document(self, client_with_db: AsyncClient):
        resp = await client_with_db.get(f"/v1/dataroom/documents/{uuid.uuid4()}")
        assert resp.status_code == 404

    async def test_update_document(
        self, client_with_db: AsyncClient, sample_document: Document
    ):
        resp = await client_with_db.put(
            f"/v1/dataroom/documents/{sample_document.id}",
            json={"name": "renamed-report.pdf", "metadata": {"category": "finance"}},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "renamed-report.pdf"
        assert data["metadata"]["category"] == "finance"

    async def test_delete_document(
        self, client_with_db: AsyncClient, sample_document: Document
    ):
        resp = await client_with_db.delete(f"/v1/dataroom/documents/{sample_document.id}")
        assert resp.status_code == 204

        # Verify it's soft-deleted (no longer appears in list)
        resp = await client_with_db.get(
            "/v1/dataroom/documents",
            params={"project_id": str(PROJECT_ID)},
        )
        ids = [item["id"] for item in resp.json()["items"]]
        assert str(sample_document.id) not in ids

    async def test_download_document(
        self, client_with_db: AsyncClient, sample_document: Document
    ):
        resp = await client_with_db.get(
            f"/v1/dataroom/documents/{sample_document.id}/download"
        )
        assert resp.status_code == 200
        assert "download_url" in resp.json()

    async def test_download_logs_access(
        self, client_with_db: AsyncClient, sample_document: Document, db: AsyncSession
    ):
        await client_with_db.get(
            f"/v1/dataroom/documents/{sample_document.id}/download"
        )

        # Check access log was created
        stmt = select(DocumentAccessLog).where(
            DocumentAccessLog.document_id == sample_document.id,
            DocumentAccessLog.action == DocumentAccessAction.DOWNLOAD,
        )
        result = await db.execute(stmt)
        logs = result.scalars().all()
        assert len(logs) >= 1

    async def test_viewer_can_list_and_view(
        self, viewer_client: AsyncClient, sample_document: Document
    ):
        resp = await viewer_client.get("/v1/dataroom/documents")
        assert resp.status_code == 200

        resp = await viewer_client.get(f"/v1/dataroom/documents/{sample_document.id}")
        assert resp.status_code == 200

    async def test_viewer_cannot_delete(
        self, viewer_client: AsyncClient, sample_document: Document
    ):
        resp = await viewer_client.delete(f"/v1/dataroom/documents/{sample_document.id}")
        assert resp.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════════
# VERSIONING TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestVersioning:
    async def test_create_new_version(
        self, client_with_db: AsyncClient, sample_document: Document
    ):
        resp = await client_with_db.post(
            f"/v1/dataroom/documents/{sample_document.id}/versions",
            json={
                "file_name": "report-v2.pdf",
                "file_type": "pdf",
                "file_size_bytes": 2048,
                "checksum_sha256": SAMPLE_CHECKSUM,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["document_id"] != str(sample_document.id)
        assert "upload_url" in data

    async def test_list_versions(
        self, client_with_db: AsyncClient, sample_document: Document, db: AsyncSession
    ):
        # Create a v2
        v2 = Document(
            org_id=ORG_ID,
            project_id=PROJECT_ID,
            name="test-report-v2.pdf",
            file_type="pdf",
            mime_type="application/pdf",
            s3_key="test/v2.pdf",
            s3_bucket="scr-documents",
            file_size_bytes=2048,
            status=DocumentStatus.READY,
            uploaded_by=USER_ID,
            checksum_sha256=SAMPLE_CHECKSUM,
            version=2,
            parent_version_id=sample_document.id,
        )
        db.add(v2)
        await db.flush()

        resp = await client_with_db.get(
            f"/v1/dataroom/documents/{sample_document.id}/versions"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["version"] == 1
        assert data[1]["version"] == 2


# ═══════════════════════════════════════════════════════════════════════════════
# ACCESS LOG TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestAccessLog:
    async def test_get_access_log(
        self, client_with_db: AsyncClient, sample_document: Document, db: AsyncSession
    ):
        # Create some access log entries
        for action in [DocumentAccessAction.VIEW, DocumentAccessAction.DOWNLOAD]:
            db.add(DocumentAccessLog(
                document_id=sample_document.id,
                user_id=USER_ID,
                org_id=ORG_ID,
                action=action,
                ip_address="127.0.0.1",
            ))
        await db.flush()

        resp = await client_with_db.get(
            f"/v1/dataroom/documents/{sample_document.id}/access-log"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2


# ═══════════════════════════════════════════════════════════════════════════════
# BULK OPERATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestBulkOperations:
    async def test_bulk_upload(self, client_with_db: AsyncClient):
        resp = await client_with_db.post("/v1/dataroom/bulk/upload", json={
            "files": [
                {
                    "file_name": "doc1.pdf",
                    "file_type": "pdf",
                    "file_size_bytes": 1000,
                    "checksum_sha256": SAMPLE_CHECKSUM,
                },
                {
                    "file_name": "doc2.xlsx",
                    "file_type": "xlsx",
                    "file_size_bytes": 2000,
                    "checksum_sha256": SAMPLE_CHECKSUM,
                },
            ],
            "project_id": str(PROJECT_ID),
        })
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["uploads"]) == 2

    async def test_bulk_move(
        self,
        client_with_db: AsyncClient,
        sample_document: Document,
        sample_folder: DocumentFolder,
    ):
        resp = await client_with_db.post("/v1/dataroom/bulk/move", json={
            "document_ids": [str(sample_document.id)],
            "target_folder_id": str(sample_folder.id),
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success_count"] == 1
        assert data["failure_count"] == 0

    async def test_bulk_delete(
        self, client_with_db: AsyncClient, sample_document: Document
    ):
        resp = await client_with_db.post("/v1/dataroom/bulk/delete", json={
            "document_ids": [str(sample_document.id)],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success_count"] == 1

    async def test_bulk_move_with_missing_docs(
        self,
        client_with_db: AsyncClient,
        sample_document: Document,
        sample_folder: DocumentFolder,
    ):
        fake_id = uuid.uuid4()
        resp = await client_with_db.post("/v1/dataroom/bulk/move", json={
            "document_ids": [str(sample_document.id), str(fake_id)],
            "target_folder_id": str(sample_folder.id),
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success_count"] == 1
        assert data["failure_count"] == 1
        assert len(data["errors"]) == 1

    async def test_bulk_upload_empty_list_rejected(self, client_with_db: AsyncClient):
        resp = await client_with_db.post("/v1/dataroom/bulk/upload", json={
            "files": [],
            "project_id": str(PROJECT_ID),
        })
        assert resp.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════════
# AI EXTRACTION TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestExtraction:
    async def test_trigger_extraction(
        self, client_with_db: AsyncClient, sample_document: Document
    ):
        with patch("app.modules.dataroom.tasks.trigger_extraction") as mock_task:
            mock_task.delay = MagicMock()
            resp = await client_with_db.post(
                f"/v1/dataroom/documents/{sample_document.id}/extract",
                json={"extraction_types": ["kpi", "summary"]},
            )
        assert resp.status_code == 202

    async def test_trigger_extraction_all_types(
        self, client_with_db: AsyncClient, sample_document: Document
    ):
        with patch("app.modules.dataroom.tasks.trigger_extraction") as mock_task:
            mock_task.delay = MagicMock()
            resp = await client_with_db.post(
                f"/v1/dataroom/documents/{sample_document.id}/extract",
            )
        assert resp.status_code == 202

    async def test_get_extractions(
        self,
        client_with_db: AsyncClient,
        sample_document: Document,
        sample_extraction: DocumentExtraction,
    ):
        resp = await client_with_db.get(
            f"/v1/dataroom/documents/{sample_document.id}/extractions"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["extraction_type"] == "summary"

    async def test_project_extraction_summary_empty(
        self, client_with_db: AsyncClient
    ):
        resp = await client_with_db.get(
            f"/v1/dataroom/extractions/summary/{PROJECT_ID}"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["document_count"] == 0

    async def test_project_extraction_summary_with_data(
        self,
        client_with_db: AsyncClient,
        sample_document: Document,
        sample_extraction: DocumentExtraction,
        db: AsyncSession,
    ):
        # Add more extraction types
        db.add(DocumentExtraction(
            document_id=sample_document.id,
            extraction_type=ExtractionType.KPI,
            result={"kpi": "IRR", "value": "12%"},
            model_used="test-model",
            confidence_score=0.85,
            tokens_used=300,
            processing_time_ms=150,
        ))
        db.add(DocumentExtraction(
            document_id=sample_document.id,
            extraction_type=ExtractionType.CLASSIFICATION,
            result={"classification": "financial_statement"},
            model_used="test-model",
            confidence_score=0.9,
            tokens_used=100,
            processing_time_ms=50,
        ))
        await db.flush()

        resp = await client_with_db.get(
            f"/v1/dataroom/extractions/summary/{PROJECT_ID}"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["document_count"] == 1
        assert data["extraction_count"] == 3
        assert len(data["kpis"]) == 1
        assert len(data["summaries"]) == 1
        assert data["classifications"]["financial_statement"] == 1


# ═══════════════════════════════════════════════════════════════════════════════
# SHARING TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestSharing:
    async def test_create_share_link(
        self, client_with_db: AsyncClient, sample_document: Document
    ):
        resp = await client_with_db.post("/v1/dataroom/share", json={
            "document_id": str(sample_document.id),
            "allow_download": True,
            "watermark_enabled": True,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert "share_token" in data
        assert data["allow_download"] is True
        assert data["watermark_enabled"] is True
        assert data["view_count"] == 0

    async def test_create_share_link_with_password(
        self, client_with_db: AsyncClient, sample_document: Document
    ):
        resp = await client_with_db.post("/v1/dataroom/share", json={
            "document_id": str(sample_document.id),
            "password": "secret123",
            "max_views": 10,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["max_views"] == 10

    async def test_create_share_link_with_expiry(
        self, client_with_db: AsyncClient, sample_document: Document
    ):
        expires = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        resp = await client_with_db.post("/v1/dataroom/share", json={
            "document_id": str(sample_document.id),
            "expires_at": expires,
        })
        assert resp.status_code == 201
        assert resp.json()["expires_at"] is not None

    async def test_access_share_link(
        self, client_with_db: AsyncClient, sample_share: ShareLink
    ):
        resp = await client_with_db.get(f"/v1/dataroom/share/{sample_share.share_token}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["document_name"] == "test-report.pdf"
        assert data["allow_download"] is True

    async def test_access_share_link_increments_view_count(
        self, client_with_db: AsyncClient, sample_share: ShareLink, db: AsyncSession
    ):
        assert sample_share.view_count == 0
        await client_with_db.get(f"/v1/dataroom/share/{sample_share.share_token}")

        await db.refresh(sample_share)
        assert sample_share.view_count == 1

    async def test_access_expired_share_link(
        self, client_with_db: AsyncClient, db: AsyncSession, sample_document: Document
    ):
        share = ShareLink(
            document_id=sample_document.id,
            org_id=ORG_ID,
            created_by=USER_ID,
            share_token=secrets.token_urlsafe(32),
            expires_at=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1),
        )
        db.add(share)
        await db.flush()

        resp = await client_with_db.get(f"/v1/dataroom/share/{share.share_token}")
        assert resp.status_code == 403
        assert "expired" in resp.json()["detail"]

    async def test_access_share_link_max_views_exceeded(
        self, client_with_db: AsyncClient, db: AsyncSession, sample_document: Document
    ):
        share = ShareLink(
            document_id=sample_document.id,
            org_id=ORG_ID,
            created_by=USER_ID,
            share_token=secrets.token_urlsafe(32),
            max_views=1,
            view_count=1,
        )
        db.add(share)
        await db.flush()

        resp = await client_with_db.get(f"/v1/dataroom/share/{share.share_token}")
        assert resp.status_code == 403
        assert "maximum" in resp.json()["detail"]

    async def test_access_password_protected_share_without_password(
        self, client_with_db: AsyncClient, db: AsyncSession, sample_document: Document
    ):
        share = ShareLink(
            document_id=sample_document.id,
            org_id=ORG_ID,
            created_by=USER_ID,
            share_token=secrets.token_urlsafe(32),
            password_hash=hashlib.sha256(b"secret").hexdigest(),
        )
        db.add(share)
        await db.flush()

        resp = await client_with_db.get(f"/v1/dataroom/share/{share.share_token}")
        assert resp.status_code == 403
        assert "Password required" in resp.json()["detail"]

    async def test_access_password_protected_share_wrong_password(
        self, client_with_db: AsyncClient, db: AsyncSession, sample_document: Document
    ):
        share = ShareLink(
            document_id=sample_document.id,
            org_id=ORG_ID,
            created_by=USER_ID,
            share_token=secrets.token_urlsafe(32),
            password_hash=hashlib.sha256(b"secret").hexdigest(),
        )
        db.add(share)
        await db.flush()

        resp = await client_with_db.get(
            f"/v1/dataroom/share/{share.share_token}",
            params={"password": "wrong"},
        )
        assert resp.status_code == 403
        assert "Invalid password" in resp.json()["detail"]

    async def test_access_password_protected_share_correct_password(
        self, client_with_db: AsyncClient, db: AsyncSession, sample_document: Document
    ):
        pw = "correctpassword"
        share = ShareLink(
            document_id=sample_document.id,
            org_id=ORG_ID,
            created_by=USER_ID,
            share_token=secrets.token_urlsafe(32),
            password_hash=hashlib.sha256(pw.encode()).hexdigest(),
        )
        db.add(share)
        await db.flush()

        resp = await client_with_db.get(
            f"/v1/dataroom/share/{share.share_token}",
            params={"password": pw},
        )
        assert resp.status_code == 200

    async def test_revoke_share_link(
        self, client_with_db: AsyncClient, sample_share: ShareLink
    ):
        resp = await client_with_db.delete(f"/v1/dataroom/share/{sample_share.id}")
        assert resp.status_code == 204

        # Verify it's revoked
        resp = await client_with_db.get(f"/v1/dataroom/share/{sample_share.share_token}")
        assert resp.status_code == 404

    async def test_access_nonexistent_share_token(self, client_with_db: AsyncClient):
        resp = await client_with_db.get("/v1/dataroom/share/nonexistent-token")
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# SERVICE UNIT TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestServiceUnit:
    async def test_folder_tree_structure(self, db: AsyncSession, seed_data):
        """Verify folder tree builds correct hierarchy."""
        root = DocumentFolder(org_id=ORG_ID, project_id=PROJECT_ID, name="Root")
        db.add(root)
        await db.flush()

        child = DocumentFolder(
            org_id=ORG_ID,
            project_id=PROJECT_ID,
            name="Child",
            parent_folder_id=root.id,
        )
        db.add(child)
        await db.flush()

        tree = await service.get_folder_tree(db, ORG_ID, PROJECT_ID)
        assert len(tree) == 1
        assert tree[0].name == "Root"
        assert len(tree[0].children) == 1
        assert tree[0].children[0].name == "Child"

    async def test_folder_tree_with_document_counts(self, db: AsyncSession, seed_data):
        folder = DocumentFolder(org_id=ORG_ID, project_id=PROJECT_ID, name="Docs")
        db.add(folder)
        await db.flush()

        for i in range(3):
            db.add(Document(
                org_id=ORG_ID,
                project_id=PROJECT_ID,
                folder_id=folder.id,
                name=f"doc-{i}.pdf",
                file_type="pdf",
                mime_type="application/pdf",
                s3_key=f"test/doc-{i}.pdf",
                s3_bucket="scr-documents",
                file_size_bytes=100,
                status=DocumentStatus.READY,
                uploaded_by=USER_ID,
                checksum_sha256=SAMPLE_CHECKSUM,
            ))
        await db.flush()

        tree = await service.get_folder_tree(db, ORG_ID, PROJECT_ID)
        assert tree[0].document_count == 3

    def test_generate_watermark_returns_bytes(self):
        """Test watermark generation returns bytes (may skip if PyPDF2 not installed)."""
        result = service.generate_watermark(b"%PDF-1.4 fake content", "Test User", "2026-02-27")
        assert isinstance(result, bytes)

    async def test_tenant_isolation(self, db: AsyncSession, seed_data):
        """Documents from other orgs are not visible."""
        # Create a user in the other org for FK constraint
        other_user = User(
            id=uuid.uuid4(),
            org_id=OTHER_ORG_ID,
            email="other@example.com",
            full_name="Other User",
            role=UserRole.ADMIN,
            external_auth_id="user_other_org",
            is_active=True,
        )
        db.add(other_user)
        await db.flush()

        other_doc = Document(
            org_id=OTHER_ORG_ID,
            project_id=None,
            name="other-org-doc.pdf",
            file_type="pdf",
            mime_type="application/pdf",
            s3_key="other/doc.pdf",
            s3_bucket="scr-documents",
            file_size_bytes=100,
            status=DocumentStatus.READY,
            uploaded_by=other_user.id,
            checksum_sha256=SAMPLE_CHECKSUM,
        )
        db.add(other_doc)
        await db.flush()

        items, total = await service.list_documents(db, ORG_ID, project_id=PROJECT_ID)
        for doc in items:
            assert doc.org_id == ORG_ID

    async def test_soft_delete_hides_document(self, db: AsyncSession, seed_data):
        doc = Document(
            org_id=ORG_ID,
            project_id=PROJECT_ID,
            name="to-delete.pdf",
            file_type="pdf",
            mime_type="application/pdf",
            s3_key="test/delete.pdf",
            s3_bucket="scr-documents",
            file_size_bytes=100,
            status=DocumentStatus.READY,
            uploaded_by=USER_ID,
            checksum_sha256=SAMPLE_CHECKSUM,
        )
        db.add(doc)
        await db.flush()

        await service.soft_delete_document(db, doc.id, ORG_ID)

        with pytest.raises(LookupError):
            await service._get_document_or_raise(db, doc.id, ORG_ID)


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMA VALIDATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestSchemaValidation:
    def test_presigned_upload_valid(self):
        from app.modules.dataroom.schemas import PresignedUploadRequest

        req = PresignedUploadRequest(
            file_name="report.pdf",
            file_type="pdf",
            file_size_bytes=5000,
            project_id=PROJECT_ID,
            checksum_sha256=SAMPLE_CHECKSUM,
        )
        assert req.file_type == "pdf"

    def test_presigned_upload_normalizes_file_type(self):
        from app.modules.dataroom.schemas import PresignedUploadRequest

        req = PresignedUploadRequest(
            file_name="report.pdf",
            file_type=".PDF",
            file_size_bytes=5000,
            project_id=PROJECT_ID,
            checksum_sha256=SAMPLE_CHECKSUM,
        )
        assert req.file_type == "pdf"

    def test_presigned_upload_rejects_invalid_type(self):
        from pydantic import ValidationError

        from app.modules.dataroom.schemas import PresignedUploadRequest

        with pytest.raises(ValidationError):
            PresignedUploadRequest(
                file_name="malware.exe",
                file_type="exe",
                file_size_bytes=5000,
                project_id=PROJECT_ID,
                checksum_sha256=SAMPLE_CHECKSUM,
            )

    def test_presigned_upload_rejects_oversize(self):
        from pydantic import ValidationError

        from app.modules.dataroom.schemas import PresignedUploadRequest

        with pytest.raises(ValidationError):
            PresignedUploadRequest(
                file_name="huge.pdf",
                file_type="pdf",
                file_size_bytes=MAX_FILE_SIZE_BYTES + 1,
                project_id=PROJECT_ID,
                checksum_sha256=SAMPLE_CHECKSUM,
            )

    def test_bulk_upload_max_50_files(self):
        from pydantic import ValidationError

        from app.modules.dataroom.schemas import BulkUploadRequest, BulkUploadFileItem

        with pytest.raises(ValidationError):
            BulkUploadRequest(
                files=[
                    BulkUploadFileItem(
                        file_name=f"doc-{i}.pdf",
                        file_type="pdf",
                        file_size_bytes=100,
                        checksum_sha256=SAMPLE_CHECKSUM,
                    )
                    for i in range(51)
                ],
                project_id=PROJECT_ID,
            )

    def test_share_password_min_length(self):
        from pydantic import ValidationError

        from app.modules.dataroom.schemas import ShareCreateRequest

        with pytest.raises(ValidationError):
            ShareCreateRequest(
                document_id=uuid.uuid4(),
                password="ab",  # too short, min 4
            )


# ═══════════════════════════════════════════════════════════════════════════════
# TASK TESTS (Unit, no Celery broker needed)
# ═══════════════════════════════════════════════════════════════════════════════


class TestTasks:
    def test_classify_document_financial(self):
        from app.modules.dataroom.tasks import _classify_document

        doc = MagicMock()
        doc.name = "Q4 Financial Statement 2025.pdf"
        result = _classify_document(doc, "")
        assert result == "financial_statement"

    def test_classify_document_legal(self):
        from app.modules.dataroom.tasks import _classify_document

        doc = MagicMock()
        doc.name = "NDA - Project Alpha.pdf"
        result = _classify_document(doc, "")
        assert result == "legal_agreement"

    def test_classify_document_environmental(self):
        from app.modules.dataroom.tasks import _classify_document

        doc = MagicMock()
        doc.name = "Environmental Impact Assessment.pdf"
        result = _classify_document(doc, "")
        assert result == "environmental_report"

    def test_classify_document_by_content(self):
        from app.modules.dataroom.tasks import _classify_document

        doc = MagicMock()
        doc.name = "report.pdf"
        result = _classify_document(doc, "The revenue for Q4 was $1M and net income was $200K")
        assert result == "financial_statement"

    def test_classify_document_other(self):
        from app.modules.dataroom.tasks import _classify_document

        doc = MagicMock()
        doc.name = "random-file.pdf"
        result = _classify_document(doc, "some random content")
        assert result == "other"

    def test_classify_document_permit(self):
        from app.modules.dataroom.tasks import _classify_document

        doc = MagicMock()
        doc.name = "Building Permit - Site A.pdf"
        result = _classify_document(doc, "")
        assert result == "permit"

    def test_classify_document_business_plan(self):
        from app.modules.dataroom.tasks import _classify_document

        doc = MagicMock()
        doc.name = "Business Plan 2026.pdf"
        result = _classify_document(doc, "")
        assert result == "business_plan"
