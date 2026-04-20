"""Integration tests for the auth layer."""
import pytest
from httpx import AsyncClient

from app.services.auth_service import create_access_token


# ---------------------------------------------------------------------------
# Registration tests
# ---------------------------------------------------------------------------

async def test_register_new_user(client: AsyncClient):
    """Register a new user → 201 with id and username."""
    response = await client.post("/auth/register", json={
        "username": "alice",
        "email": "alice@example.com",
        "password": "securepass",
    })
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["username"] == "alice"


async def test_register_duplicate_username(client: AsyncClient):
    """Register duplicate username → 409."""
    payload = {"username": "bob", "email": "bob@example.com", "password": "securepass"}
    await client.post("/auth/register", json=payload)

    response = await client.post("/auth/register", json={
        "username": "bob",
        "email": "bob2@example.com",
        "password": "securepass",
    })
    assert response.status_code == 409


async def test_register_duplicate_email(client: AsyncClient):
    """Register duplicate email → 409."""
    await client.post("/auth/register", json={
        "username": "carol",
        "email": "carol@example.com",
        "password": "securepass",
    })

    response = await client.post("/auth/register", json={
        "username": "carol2",
        "email": "carol@example.com",
        "password": "securepass",
    })
    assert response.status_code == 409


async def test_register_short_password(client: AsyncClient):
    """Register with password < 8 chars → 422."""
    response = await client.post("/auth/register", json={
        "username": "dave",
        "email": "dave@example.com",
        "password": "short",
    })
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Login tests
# ---------------------------------------------------------------------------

async def test_login_valid_credentials(client: AsyncClient):
    """Login with valid credentials → 200 with access_token."""
    await client.post("/auth/register", json={
        "username": "eve",
        "email": "eve@example.com",
        "password": "securepass",
    })

    response = await client.post("/auth/login", json={
        "username": "eve",
        "password": "securepass",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


async def test_login_wrong_password(client: AsyncClient):
    """Login with wrong password → 401."""
    await client.post("/auth/register", json={
        "username": "frank",
        "email": "frank@example.com",
        "password": "securepass",
    })

    response = await client.post("/auth/login", json={
        "username": "frank",
        "password": "wrongpassword",
    })
    assert response.status_code == 401


async def test_login_unknown_username(client: AsyncClient):
    """Login with unknown username → 401."""
    response = await client.post("/auth/login", json={
        "username": "nobody",
        "password": "securepass",
    })
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Protected endpoint tests
# ---------------------------------------------------------------------------

async def test_protected_endpoint_no_token(client: AsyncClient):
    """Access protected endpoint without token → 401."""
    response = await client.get("/auth/me")
    assert response.status_code == 401


async def test_protected_endpoint_expired_token(client: AsyncClient):
    """Access protected endpoint with expired token → 401."""
    # Register a user first so the user exists in DB
    reg = await client.post("/auth/register", json={
        "username": "grace",
        "email": "grace@example.com",
        "password": "securepass",
    })
    user_id = reg.json()["id"]

    # Create a token that is already expired (expire_hours=0 means immediate expiry)
    expired_token = create_access_token(user_id, "grace", expire_hours=-1)

    response = await client.get("/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert response.status_code == 401
