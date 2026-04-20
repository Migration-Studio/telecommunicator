from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.db.deps import get_db
from app.models.room import Room
from app.models.room_member import RoomMember
from app.models.user import User
from app.schemas.rooms import RoomResponse
from app.schemas.users import PasswordChange, ProfileUpdate, UserProfile
from app.services import room_service, user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserProfile)
async def get_me(current_user: User = Depends(get_current_user)):
    return await user_service.get_profile(current_user)


@router.get("/me/rooms", response_model=list[RoomResponse])
async def get_my_rooms(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Room)
        .join(RoomMember, RoomMember.room_id == Room.id)
        .where(RoomMember.user_id == current_user.id)
    )
    rooms = result.scalars().all()
    return [await room_service._room_to_response(r, db) for r in rooms]


@router.patch("/me", response_model=UserProfile)
async def update_me(
    body: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await user_service.update_profile(db, current_user, body.display_name)


@router.post("/me/password", status_code=200)
async def change_password(
    body: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await user_service.change_password(db, current_user, body.current_password, body.new_password)
    return {"detail": "Password updated"}


@router.get("/{username}", response_model=UserProfile)
async def get_user_by_username(
    username: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return public profile of any user by username."""
    result = await db.execute(select(User).where(User.username == username))
    target = result.scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    return target
