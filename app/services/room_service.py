from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.room import Room
from app.models.room_member import RoomMember
from app.models.user import User
from app.schemas.rooms import PermissionUpdate, RoomCreate, RoomResponse


async def _room_to_response(room: Room, db: AsyncSession) -> RoomResponse:
    owner = await db.get(User, room.owner_id)
    count_result = await db.execute(
        select(func.count()).where(RoomMember.room_id == room.id)
    )
    member_count = count_result.scalar_one()
    return RoomResponse(
        id=room.id,
        name=room.name,
        owner_username=owner.username if owner else "",
        member_count=member_count,
        is_private=room.is_private,
        allow_member_invite=room.allow_member_invite,
        read_only=room.read_only,
    )


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

    return await _room_to_response(room, db)


async def list_public_rooms(db: AsyncSession) -> list[RoomResponse]:
    result = await db.execute(select(Room).where(Room.is_private == False))  # noqa: E712
    rooms = result.scalars().all()
    return [await _room_to_response(r, db) for r in rooms]


async def join_room(room_id: int, user: User, db: AsyncSession) -> RoomResponse:
    room = await db.get(Room, room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found")

    if room.is_private:
        # Check if already a member (invited)
        membership = await db.execute(
            select(RoomMember).where(
                RoomMember.room_id == room_id, RoomMember.user_id == user.id
            )
        )
        if membership.scalar_one_or_none() is None:
            raise HTTPException(status_code=403, detail="Cannot join a private room without an invite")

    # Idempotent: add only if not already a member
    existing = await db.execute(
        select(RoomMember).where(
            RoomMember.room_id == room_id, RoomMember.user_id == user.id
        )
    )
    if existing.scalar_one_or_none() is None:
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
        # Check requester is a member
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

    return await _room_to_response(room, db)


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
