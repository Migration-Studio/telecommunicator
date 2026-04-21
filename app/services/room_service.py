from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.room import Room
from app.models.room_member import RoomMember
from app.models.user import User
from app.schemas.rooms import PermissionUpdate, RoomCreate, RoomResponse


def _build_response(room: Room, owner_username: str, member_count: int) -> RoomResponse:
    return RoomResponse(
        id=room.id,
        name=room.name,
        owner_username=owner_username,
        member_count=member_count,
        is_private=room.is_private,
        allow_member_invite=room.allow_member_invite,
        read_only=room.read_only,
    )


async def _room_to_response(room: Room, db: AsyncSession) -> RoomResponse:
    """Single-room response — used after mutations where we already have the room."""
    owner = await db.get(User, room.owner_id)
    count_result = await db.execute(
        select(func.count()).where(RoomMember.room_id == room.id)
    )
    member_count = count_result.scalar_one()
    return _build_response(room, owner.username if owner else "", member_count)


async def _rooms_to_responses(rooms: list[Room], db: AsyncSession) -> list[RoomResponse]:
    """Batch-load owners and member counts for a list of rooms — avoids N+1."""
    if not rooms:
        return []

    room_ids = [r.id for r in rooms]
    owner_ids = list({r.owner_id for r in rooms})

    # Single query for all owners
    owner_rows = await db.execute(select(User).where(User.id.in_(owner_ids)))
    owner_map: dict[int, str] = {u.id: u.username for u in owner_rows.scalars()}

    # Single query for all member counts
    count_rows = await db.execute(
        select(RoomMember.room_id, func.count().label("cnt"))
        .where(RoomMember.room_id.in_(room_ids))
        .group_by(RoomMember.room_id)
    )
    count_map: dict[int, int] = {row.room_id: row.cnt for row in count_rows}

    return [
        _build_response(r, owner_map.get(r.owner_id, ""), count_map.get(r.id, 0))
        for r in rooms
    ]


async def create_room(data: RoomCreate, owner: User, db: AsyncSession) -> RoomResponse:
    existing = await db.execute(select(Room).where(Room.name == data.name))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Room name already exists")

    room = Room(name=data.name, owner_id=owner.id, is_private=data.is_private)
    db.add(room)
    await db.flush()

    member = RoomMember(room_id=room.id, user_id=owner.id)
    db.add(member)
    await db.commit()
    await db.refresh(room)

    return _build_response(room, owner.username, 1)


async def list_public_rooms(db: AsyncSession) -> list[RoomResponse]:
    result = await db.execute(select(Room).where(Room.is_private == False))  # noqa: E712
    rooms = result.scalars().all()
    return await _rooms_to_responses(list(rooms), db)


async def join_room(room_id: int, user: User, db: AsyncSession) -> RoomResponse:
    room = await db.get(Room, room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found")

    # Single membership query covers both the private-room gate and idempotency check
    existing = await db.execute(
        select(RoomMember).where(
            RoomMember.room_id == room_id, RoomMember.user_id == user.id
        )
    )
    is_member = existing.scalar_one_or_none() is not None

    if room.is_private and not is_member:
        raise HTTPException(status_code=403, detail="Cannot join a private room without an invite")

    if not is_member:
        db.add(RoomMember(room_id=room_id, user_id=user.id))
        await db.commit()

    return await _room_to_response(room, db)


async def leave_room(room_id: int, user: User, db: AsyncSession) -> RoomResponse:
    room = await db.get(Room, room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found")

    if room.owner_id == user.id:
        raise HTTPException(
            status_code=400,
            detail="Owner must transfer ownership or delete the room before leaving",
        )

    membership = await db.execute(
        select(RoomMember).where(
            RoomMember.room_id == room_id, RoomMember.user_id == user.id
        )
    )
    member = membership.scalar_one_or_none()
    if member is None:
        raise HTTPException(status_code=404, detail="Not a member of this room")

    await db.delete(member)
    await db.commit()

    return await _room_to_response(room, db)


async def invite_user(room_id: int, username: str, requester: User, db: AsyncSession) -> RoomResponse:
    room = await db.get(Room, room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found")

    # Permission check: owner can always invite; non-owner only if allow_member_invite
    if room.owner_id != requester.id:
        req_membership = await db.execute(
            select(RoomMember).where(
                RoomMember.room_id == room_id, RoomMember.user_id == requester.id
            )
        )
        if req_membership.scalar_one_or_none() is None:
            raise HTTPException(status_code=403, detail="Not a member of this room")
        if not room.allow_member_invite:
            raise HTTPException(status_code=403, detail="Members are not allowed to invite in this room")

    target_result = await db.execute(select(User).where(User.username == username))
    target = target_result.scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")

    existing = await db.execute(
        select(RoomMember).where(
            RoomMember.room_id == room_id, RoomMember.user_id == target.id
        )
    )
    if existing.scalar_one_or_none() is None:
        db.add(RoomMember(room_id=room_id, user_id=target.id))
        await db.commit()

    response = await _room_to_response(room, db)

    # Notify the invited user in real-time if they're connected
    from app.ws.connection_manager import manager as ws_manager
    await ws_manager.send_to_user(target.id, {
        "type": "invite",
        "payload": {
            "id": response.id,
            "name": response.name,
            "owner_username": response.owner_username,
            "member_count": response.member_count,
            "is_private": response.is_private,
            "allow_member_invite": response.allow_member_invite,
            "read_only": response.read_only,
        },
    })

    return response


async def remove_member(room_id: int, username: str, requester: User, db: AsyncSession) -> RoomResponse:
    room = await db.get(Room, room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found")

    if room.owner_id != requester.id:
        raise HTTPException(status_code=403, detail="Only the owner can remove members")

    target_result = await db.execute(select(User).where(User.username == username))
    target = target_result.scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")

    if target.id == room.owner_id:
        raise HTTPException(status_code=400, detail="Owner cannot be removed from the room")

    membership = await db.execute(
        select(RoomMember).where(
            RoomMember.room_id == room_id, RoomMember.user_id == target.id
        )
    )
    member = membership.scalar_one_or_none()
    if member is None:
        raise HTTPException(status_code=404, detail="User is not a member of this room")

    await db.delete(member)
    await db.commit()

    return await _room_to_response(room, db)


async def update_permissions(
    room_id: int, data: PermissionUpdate, requester: User, db: AsyncSession
) -> RoomResponse:
    room = await db.get(Room, room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found")

    if room.owner_id != requester.id:
        raise HTTPException(status_code=403, detail="Only the owner can update permissions")

    if data.allow_member_invite is not None:
        room.allow_member_invite = data.allow_member_invite
    if data.read_only is not None:
        room.read_only = data.read_only

    await db.commit()
    await db.refresh(room)

    return await _room_to_response(room, db)
