"""Integration tests for the rooms layer (Task 5 checkpoint)."""
import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

async def register_and_login(client: AsyncClient, username: str, email: str, password: str) -> str:
    """Register a user and return the JWT access token."""
    await client.post("/auth/register", json={"username": username, "email": email, "password": password})
    resp = await client.post("/auth/login", json={"username": username, "password": password})
    return resp.json()["access_token"]


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_room_201(client: AsyncClient):
    token = await register_and_login(client, "alice", "alice@example.com", "password123")
    resp = await client.post("/rooms", json={"name": "general"}, headers=auth(token))
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "general"
    assert data["owner_username"] == "alice"
    assert data["member_count"] == 1
    assert "id" in data


@pytest.mark.asyncio
async def test_create_duplicate_room_409(client: AsyncClient):
    token = await register_and_login(client, "bob", "bob@example.com", "password123")
    await client.post("/rooms", json={"name": "unique-room"}, headers=auth(token))
    resp = await client.post("/rooms", json={"name": "unique-room"}, headers=auth(token))
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_create_room_empty_name_422(client: AsyncClient):
    token = await register_and_login(client, "carol", "carol@example.com", "password123")
    resp = await client.post("/rooms", json={"name": ""}, headers=auth(token))
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_room_name_too_long_422(client: AsyncClient):
    token = await register_and_login(client, "dave", "dave@example.com", "password123")
    long_name = "x" * 65
    resp = await client.post("/rooms", json={"name": long_name}, headers=auth(token))
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_public_rooms(client: AsyncClient):
    token = await register_and_login(client, "eve", "eve@example.com", "password123")
    await client.post("/rooms", json={"name": "pub-room", "is_private": False}, headers=auth(token))
    resp = await client.get("/rooms", headers=auth(token))
    assert resp.status_code == 200
    names = [r["name"] for r in resp.json()]
    assert "pub-room" in names


@pytest.mark.asyncio
async def test_private_room_not_in_public_listing(client: AsyncClient):
    token = await register_and_login(client, "frank", "frank@example.com", "password123")
    await client.post("/rooms", json={"name": "secret-room", "is_private": True}, headers=auth(token))
    resp = await client.get("/rooms", headers=auth(token))
    assert resp.status_code == 200
    names = [r["name"] for r in resp.json()]
    assert "secret-room" not in names


@pytest.mark.asyncio
async def test_join_public_room_200(client: AsyncClient):
    owner_token = await register_and_login(client, "grace", "grace@example.com", "password123")
    joiner_token = await register_and_login(client, "henry", "henry@example.com", "password123")

    create_resp = await client.post("/rooms", json={"name": "open-room"}, headers=auth(owner_token))
    room_id = create_resp.json()["id"]

    resp = await client.post(f"/rooms/{room_id}/join", headers=auth(joiner_token))
    assert resp.status_code == 200
    assert resp.json()["member_count"] == 2


@pytest.mark.asyncio
async def test_join_same_room_twice_idempotent(client: AsyncClient):
    owner_token = await register_and_login(client, "iris", "iris@example.com", "password123")
    joiner_token = await register_and_login(client, "jack", "jack@example.com", "password123")

    create_resp = await client.post("/rooms", json={"name": "idempotent-room"}, headers=auth(owner_token))
    room_id = create_resp.json()["id"]

    await client.post(f"/rooms/{room_id}/join", headers=auth(joiner_token))
    resp = await client.post(f"/rooms/{room_id}/join", headers=auth(joiner_token))
    assert resp.status_code == 200
    assert resp.json()["member_count"] == 2


@pytest.mark.asyncio
async def test_join_private_room_without_invite_403(client: AsyncClient):
    owner_token = await register_and_login(client, "kate", "kate@example.com", "password123")
    outsider_token = await register_and_login(client, "leo", "leo@example.com", "password123")

    create_resp = await client.post("/rooms", json={"name": "private-room", "is_private": True}, headers=auth(owner_token))
    room_id = create_resp.json()["id"]

    resp = await client.post(f"/rooms/{room_id}/join", headers=auth(outsider_token))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_owner_cannot_leave_room_400(client: AsyncClient):
    token = await register_and_login(client, "mia", "mia@example.com", "password123")
    create_resp = await client.post("/rooms", json={"name": "mia-room"}, headers=auth(token))
    room_id = create_resp.json()["id"]

    resp = await client.post(f"/rooms/{room_id}/leave", headers=auth(token))
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_non_owner_can_leave_room_200(client: AsyncClient):
    owner_token = await register_and_login(client, "noah", "noah@example.com", "password123")
    member_token = await register_and_login(client, "olivia", "olivia@example.com", "password123")

    create_resp = await client.post("/rooms", json={"name": "noah-room"}, headers=auth(owner_token))
    room_id = create_resp.json()["id"]

    await client.post(f"/rooms/{room_id}/join", headers=auth(member_token))
    resp = await client.post(f"/rooms/{room_id}/leave", headers=auth(member_token))
    assert resp.status_code == 200
    assert resp.json()["member_count"] == 1


@pytest.mark.asyncio
async def test_owner_invite_to_private_room_200(client: AsyncClient):
    owner_token = await register_and_login(client, "peter", "peter@example.com", "password123")
    await register_and_login(client, "quinn", "quinn@example.com", "password123")

    create_resp = await client.post("/rooms", json={"name": "peter-private", "is_private": True}, headers=auth(owner_token))
    room_id = create_resp.json()["id"]

    resp = await client.post(f"/rooms/{room_id}/invite/quinn", headers=auth(owner_token))
    assert resp.status_code == 200
    assert resp.json()["member_count"] == 2


@pytest.mark.asyncio
async def test_non_owner_invite_when_not_allowed_403(client: AsyncClient):
    owner_token = await register_and_login(client, "rachel", "rachel@example.com", "password123")
    member_token = await register_and_login(client, "sam", "sam@example.com", "password123")
    await register_and_login(client, "tina", "tina@example.com", "password123")

    create_resp = await client.post("/rooms", json={"name": "rachel-room"}, headers=auth(owner_token))
    room_id = create_resp.json()["id"]

    # Ensure allow_member_invite is False (default)
    await client.patch(f"/rooms/{room_id}/permissions", json={"allow_member_invite": False}, headers=auth(owner_token))

    # sam joins
    await client.post(f"/rooms/{room_id}/join", headers=auth(member_token))

    # sam tries to invite tina — should be 403
    resp = await client.post(f"/rooms/{room_id}/invite/tina", headers=auth(member_token))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_owner_remove_member_200(client: AsyncClient):
    owner_token = await register_and_login(client, "uma", "uma@example.com", "password123")
    member_token = await register_and_login(client, "victor", "victor@example.com", "password123")

    create_resp = await client.post("/rooms", json={"name": "uma-room"}, headers=auth(owner_token))
    room_id = create_resp.json()["id"]

    await client.post(f"/rooms/{room_id}/join", headers=auth(member_token))
    resp = await client.delete(f"/rooms/{room_id}/members/victor", headers=auth(owner_token))
    assert resp.status_code == 200
    assert resp.json()["member_count"] == 1


@pytest.mark.asyncio
async def test_owner_cannot_remove_themselves_400(client: AsyncClient):
    token = await register_and_login(client, "wendy", "wendy@example.com", "password123")
    create_resp = await client.post("/rooms", json={"name": "wendy-room"}, headers=auth(token))
    room_id = create_resp.json()["id"]

    resp = await client.delete(f"/rooms/{room_id}/members/wendy", headers=auth(token))
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_non_owner_cannot_update_permissions_403(client: AsyncClient):
    owner_token = await register_and_login(client, "xander", "xander@example.com", "password123")
    member_token = await register_and_login(client, "yara", "yara@example.com", "password123")

    create_resp = await client.post("/rooms", json={"name": "xander-room"}, headers=auth(owner_token))
    room_id = create_resp.json()["id"]

    await client.post(f"/rooms/{room_id}/join", headers=auth(member_token))
    resp = await client.patch(f"/rooms/{room_id}/permissions", json={"read_only": True}, headers=auth(member_token))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_owner_can_update_permissions_200(client: AsyncClient):
    token = await register_and_login(client, "zoe", "zoe@example.com", "password123")
    create_resp = await client.post("/rooms", json={"name": "zoe-room"}, headers=auth(token))
    room_id = create_resp.json()["id"]

    resp = await client.patch(f"/rooms/{room_id}/permissions", json={"read_only": True, "allow_member_invite": True}, headers=auth(token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["read_only"] is True
    assert data["allow_member_invite"] is True
