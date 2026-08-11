"""Integration tests for the authentication endpoints."""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def _register(client: AsyncClient, email: str = "test@example.com", password: str = "password123"):
    return await client.post(
        "/auth/register",
        json={"email": email, "password": password, "full_name": "Test User"},
    )


async def test_register_creates_user(client: AsyncClient):
    response = await _register(client)

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "test@example.com"
    assert "id" in body
    assert "hashed_password" not in body


async def test_register_duplicate_email_conflicts(client: AsyncClient):
    await _register(client)
    response = await _register(client)

    assert response.status_code == 409


async def test_login_success_returns_tokens(client: AsyncClient):
    await _register(client)
    response = await client.post(
        "/auth/login", json={"email": "test@example.com", "password": "password123"}
    )

    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"


async def test_login_wrong_password_unauthorized(client: AsyncClient):
    await _register(client)
    response = await client.post(
        "/auth/login", json={"email": "test@example.com", "password": "wrong"}
    )

    assert response.status_code == 401


async def test_get_me_requires_auth(client: AsyncClient):
    response = await client.get("/users/me")
    assert response.status_code == 401


async def test_get_me_with_valid_token(client: AsyncClient):
    await _register(client)
    login = await client.post(
        "/auth/login", json={"email": "test@example.com", "password": "password123"}
    )
    access_token = login.json()["access_token"]

    response = await client.get(
        "/users/me", headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"


async def test_refresh_rotates_token(client: AsyncClient):
    await _register(client)
    login = await client.post(
        "/auth/login", json={"email": "test@example.com", "password": "password123"}
    )
    refresh_token = login.json()["refresh_token"]

    response = await client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 200
    new_tokens = response.json()
    assert new_tokens["refresh_token"] != refresh_token

    # old refresh token should now be revoked
    reuse_response = await client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert reuse_response.status_code == 401


async def test_logout_revokes_refresh_token(client: AsyncClient):
    await _register(client)
    login = await client.post(
        "/auth/login", json={"email": "test@example.com", "password": "password123"}
    )
    refresh_token = login.json()["refresh_token"]

    logout_response = await client.post("/auth/logout", json={"refresh_token": refresh_token})
    assert logout_response.status_code == 204

    refresh_response = await client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_response.status_code == 401
