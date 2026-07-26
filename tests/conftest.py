import pytest
import pytest_asyncio
import asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import get_db
from app.models.base import Base  # All models inherit from this Base, not app.core.database.Base

# sqlite:///:memory: gives each connection its own isolated DB.
# The URI form with cache=shared lets all connections share the same named in-memory DB.
TEST_DATABASE_URL = "sqlite+aiosqlite:///file:testdb?mode=memory&cache=shared&uri=true"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    # Create tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    async with TestingSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
            
    # Clean up tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function", autouse=True)
def mock_redis_service(monkeypatch):
    from app.core.redis import RedisService
    from unittest.mock import AsyncMock
    monkeypatch.setattr(RedisService, "acquire_lock", AsyncMock(return_value=True))
    monkeypatch.setattr(RedisService, "release_lock", AsyncMock(return_value=None))

@pytest.fixture(scope="function")
def client(db_session: AsyncSession) -> TestClient:
    from app.core.redis import get_redis
    from unittest.mock import AsyncMock

    # Override get_db dependency to use the test session
    async def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    counter = {}
    async def _override_get_redis():
        mock = AsyncMock()
        async def mock_eval(script, numkeys, key, *args):
            count = counter.get(key, 0) + 1
            counter[key] = count
            return (count, 60)
        mock.client.eval = mock_eval
        yield mock
            
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_redis] = _override_get_redis
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
