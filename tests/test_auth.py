import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from types import SimpleNamespace

from app.core.redis import get_redis
from app.main import app
from app.models.auth import Role, User


class FakeRateLimitClient:
    def __init__(self):
        self.counts: dict[str, int] = {}

    async def eval(self, _script: str, _numkeys: int, key: str, window_seconds: int):
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key], window_seconds


@pytest.fixture(autouse=True)
def override_rate_limit_redis():
    fake_redis = SimpleNamespace(client=FakeRateLimitClient())

    async def override():
        return fake_redis

    app.dependency_overrides[get_redis] = override
    yield
    app.dependency_overrides.pop(get_redis, None)


@pytest.mark.asyncio
async def test_user_registration(client: TestClient, db_session: AsyncSession):
    # Pre-create Viewer role for user registration
    viewer_role = Role(name="Viewer", description="Viewer Role")
    db_session.add(viewer_role)
    await db_session.commit()

    # Register user
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "testuser",
            "email": "testuser@gmail.com",
            "password": "testpassword"
        }
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "testuser@gmail.com"
    assert "id" in data

    # Verify user exists in the database
    result = await db_session.execute(select(User).where(User.username == "testuser"))
    user = result.scalar_one_or_none()
    assert user is not None
    assert user.email == "testuser@gmail.com"
    assert len(user.roles) == 1
    assert user.roles[0].name == "Viewer"


@pytest.mark.asyncio
async def test_user_registration_rejects_role_assignment(client: TestClient, db_session: AsyncSession):
    viewer_role = Role(name="Viewer", description="Viewer Role")
    db_session.add(viewer_role)
    await db_session.commit()

    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "untrustedadmin",
            "email": "untrustedadmin@example.com",
            "password": "testpassword",
            "roles": ["Admin"],
        },
    )

    assert response.status_code == 422

    result = await db_session.execute(select(User).where(User.username == "untrustedadmin"))
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_user_login(client: TestClient, db_session: AsyncSession):
    # Create role and user manually
    viewer_role = Role(name="Viewer", description="Viewer Role")
    db_session.add(viewer_role)
    await db_session.commit()

    # Register user first via API
    client.post(
        "/api/v1/auth/register",
        json={
            "username": "loginuser",
            "email": "loginuser@gmail.com",
            "password": "loginpassword"
        }
    )

    # Login
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": "loginuser",
            "password": "loginpassword"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == "loginuser"


@pytest.mark.asyncio
async def test_protected_routes_unauthorized(client: TestClient):
    # Try fetching profile without token
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_registration_is_rate_limited(client: TestClient, db_session: AsyncSession):
    db_session.add(Role(name="Viewer", description="Viewer Role"))
    await db_session.commit()

    for index in range(5):
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": f"rateuser{index}",
                "email": f"rateuser{index}@example.com",
                "password": "testpassword",
            },
        )
        assert response.status_code == 201

    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "rateuserblocked",
            "email": "rateuserblocked@example.com",
            "password": "testpassword",
        },
    )
    assert response.status_code == 429
    assert response.headers["Retry-After"] == "60"


@pytest.mark.asyncio
async def test_login_is_rate_limited(client: TestClient):
    for _ in range(5):
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "unknown", "password": "incorrect-password"},
        )
        assert response.status_code == 401

    response = client.post(
        "/api/v1/auth/login",
        json={"username": "unknown", "password": "incorrect-password"},
    )
    assert response.status_code == 429
    assert response.headers["Retry-After"] == "60"
