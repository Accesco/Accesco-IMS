import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.auth import Role, User

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
