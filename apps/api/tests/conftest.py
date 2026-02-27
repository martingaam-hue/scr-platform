"""Shared test fixtures for the SCR API test suite."""

import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.main import app
from app.models.core import Organization, User
from app.models.enums import OrgType, UserRole
from app.schemas.auth import CurrentUser

# Dedicated engine for test fixtures — NullPool avoids asyncpg cross-task issues
_test_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.APP_DEBUG,
    poolclass=NullPool,
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.fixture
async def db() -> AsyncGenerator[AsyncSession]:
    """Provide a DB session that rolls back after each test."""
    async with _test_engine.connect() as conn:
        trans = await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()
            await trans.rollback()


# ── Sample data fixtures ──────────────────────────────────────────────────

SAMPLE_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
SAMPLE_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
SAMPLE_CLERK_ID = "user_test_clerk_123"


@pytest.fixture
async def sample_org(db: AsyncSession) -> Organization:
    """Create a test organization."""
    org = Organization(
        id=SAMPLE_ORG_ID,
        name="Test Org",
        slug="test-org",
        type=OrgType.ALLY,
    )
    db.add(org)
    await db.flush()
    return org


@pytest.fixture
async def sample_user(db: AsyncSession, sample_org: Organization) -> User:
    """Create a test user linked to the sample org."""
    user = User(
        id=SAMPLE_USER_ID,
        org_id=sample_org.id,
        email="test@example.com",
        full_name="Test User",
        role=UserRole.ADMIN,
        external_auth_id=SAMPLE_CLERK_ID,
        is_active=True,
    )
    db.add(user)
    await db.flush()
    return user


@pytest.fixture
def sample_current_user(sample_org: Organization) -> CurrentUser:
    """Create a CurrentUser pydantic model for dependency injection."""
    return CurrentUser(
        user_id=SAMPLE_USER_ID,
        org_id=SAMPLE_ORG_ID,
        role=UserRole.ADMIN,
        email="test@example.com",
        external_auth_id=SAMPLE_CLERK_ID,
    )


@pytest.fixture
def mock_clerk_jwt():
    """Mock verify_clerk_token to bypass Clerk JWKS verification in tests."""
    mock_payload = {
        "sub": SAMPLE_CLERK_ID,
        "email": "test@example.com",
        "iss": "https://test.clerk.accounts.dev",
        "exp": int(datetime.now(timezone.utc).timestamp()) + 3600,
    }
    with patch(
        "app.auth.clerk_jwt.verify_clerk_token",
        new_callable=AsyncMock,
        return_value=mock_payload,
    ) as mock:
        yield mock


@pytest.fixture
async def authenticated_client(
    client: AsyncClient, mock_clerk_jwt: AsyncMock
) -> AsyncClient:
    """AsyncClient with a mock auth token that bypasses Clerk verification."""
    client.headers["Authorization"] = "Bearer mock-test-token"
    return client
