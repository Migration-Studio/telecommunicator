from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import Message
from app.models.room import Room
from app.models.room_member import RoomMember
from app.models.user import User
from app.schemas.messages import MessageResponse
from app.ws.connection_manager import manager

_DEFAULT_PAGE_SIZE = 50
_MAX_PAGE_SIZE = 200


async def send_message(
    room_id: int,
    body: str,
    author: User,
    db: AsyncSession,
    *,
    room: Room | None = None,
) -> MessageResponse:
    """Validate, persist, and broadcast a message. Raises HTTPException on failure.

    Pass ``room`` if you already have the Room object to avoid a redundant fetch.
    """
    # Body validation (cheap, do first)
    if not body or len(body) > 2000:
        raise HTTPException(
            status_code=422, detail="Message body must be 1\u20132000 characters"
        )

    # Membership check
    membership = await db.execute(
        select(RoomMember).where(
            RoomMember.room_id == room_id, RoomMember.user_id == author.id
        )
    )
    if membership.scalar_one_or_none() is None:
        raise HTTPException(status_code=403, detail="Not a member of this room")

    # Room fetch (reuse if caller already has it)
    if room is None:
        room = await db.get(Room, room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found")

    if room.read_only and room.owner_id != author.id:
        raise HTTPException(
            status_code=403, detail="Room is read-only; only the owner can send messages"
        )

    # Persist
    msg = Message(room_id=room_id, author_id=author.id, body=body)
    db.add(msg)
    await db.commit()
    await db.refresh(msg)

    response = MessageResponse(
        id=msg.id,
        room_id=msg.room_id,
        author_username=author.username,
        author_display_name=author.display_name,
        body=msg.body,
        created_at=msg.created_at,
    )

    # Broadcast
    await manager.broadcast(
        room_id,
        {
            "type": "message",
            "payload": {
                "id": response.id,
                "room_id": response.room_id,
                "author_username": response.author_username,
                "author_display_name": response.author_display_name,
                "body": response.body,
                "created_at": response.created_at.isoformat(),
            },
        },
    )

    return response


async def get_message_history(
    room_id: int,
    user: User,
    db: AsyncSession,
    before_id: int | None = None,
    limit: int = _DEFAULT_PAGE_SIZE,
) -> list[MessageResponse]:
    """Return paginated message history. Raises 403 if user is not a member."""
    limit = min(limit, _MAX_PAGE_SIZE)

    # Membership check
    membership = await db.execute(
        select(RoomMember).where(
            RoomMember.room_id == room_id, RoomMember.user_id == user.id
        )
    )
    if membership.scalar_one_or_none() is None:
        raise HTTPException(status_code=403, detail="Not a member of this room")

    query = (
        select(Message, User)
        .join(User, Message.author_id == User.id)
        .where(Message.room_id == room_id)
    )
    if before_id is not None:
        query = query.where(Message.id < before_id)

    query = query.order_by(Message.id.desc()).limit(limit)

    result = await db.execute(query)
    rows = result.all()

    return [
        MessageResponse(
            id=msg.id,
            room_id=msg.room_id,
            author_username=author.username,
            author_display_name=author.display_name,
            body=msg.body,
            created_at=msg.created_at,
        )
        for msg, author in rows
    ]
