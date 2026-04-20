from pydantic import BaseModel, Field


class RoomCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    is_private: bool = False


class RoomResponse(BaseModel):
    id: int
    name: str
    owner_username: str
    member_count: int
    is_private: bool
    allow_member_invite: bool
    read_only: bool


class PermissionUpdate(BaseModel):
    allow_member_invite: bool | None = None
    read_only: bool | None = None
