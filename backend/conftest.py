"""Global pytest configuration and fixtures."""

import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from motor.motor_asyncio import AsyncIOMotorClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.database import Base, get_postgres_session
from app.main import app


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_db_engine():
    """Create test database engine."""
    test_db_url = settings.POSTGRES_URL.replace("/veracity", "/test_veracity")
    engine = create_async_engine(test_db_url, echo=False, future=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def db_session(test_db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create database session for tests."""
    async_session_maker = sessionmaker(
        test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def mongodb_client() -> AsyncGenerator[AsyncIOMotorClient, None]:
    """Create MongoDB client for tests."""
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    test_db = client.test_veracity

    yield test_db

    # Cleanup test collections
    await client.drop_database("test_veracity")
    client.close()


@pytest.fixture
def client(db_session) -> Generator[TestClient, None, None]:
    """Create FastAPI test client with database override."""

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_postgres_session] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
async def async_client(db_session) -> AsyncGenerator[AsyncClient, None]:
    """Create async FastAPI test client."""

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_postgres_session] = override_get_db

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    redis_mock = MagicMock()
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.set = AsyncMock(return_value=True)
    redis_mock.delete = AsyncMock(return_value=1)
    redis_mock.exists = AsyncMock(return_value=0)
    redis_mock.expire = AsyncMock(return_value=True)
    redis_mock.lpush = AsyncMock(return_value=1)
    redis_mock.rpop = AsyncMock(return_value=None)
    return redis_mock


@pytest.fixture
def mock_kafka_producer():
    """Mock Kafka producer for testing."""
    producer_mock = MagicMock()
    producer_mock.send = AsyncMock()
    producer_mock.flush = AsyncMock()
    return producer_mock


@pytest.fixture
def sample_social_post():
    """Sample social media post for testing."""
    return {
        "platform": "reddit",
        "post_id": "test123",
        "content": "This is a test post about technology and AI",
        "author": "test_user",
        "created_at": "2025-01-22T12:00:00Z",
        "engagement": {"upvotes": 100, "comments": 50, "shares": 10},
        "metadata": {"subreddit": "technology", "flair": "News"},
    }


@pytest.fixture
def sample_news_article():
    """Sample news article for testing."""
    return {
        "title": "Breaking: New AI Technology Announced",
        "content": "A revolutionary new AI technology has been announced...",
        "url": "https://example.com/news/ai-technology",
        "source": "TechNews",
        "published_at": "2025-01-22T10:00:00Z",
        "author": "John Doe",
        "categories": ["technology", "ai", "innovation"],
        "summary": "A brief summary of the article content",
    }


@pytest.fixture
def auth_headers():
    """Create authorization headers for testing."""
    return {"Authorization": "Bearer test-token"}


@pytest.fixture
def mock_ml_model():
    """Mock ML model for testing."""
    model_mock = MagicMock()
    model_mock.predict = MagicMock(return_value=[0.8])
    model_mock.predict_proba = MagicMock(return_value=[[0.2, 0.8]])
    return model_mock


@pytest.fixture
async def seed_test_data(db_session, mongodb_client):
    """Seed database with test data."""
    # Add test data creation logic here as needed
