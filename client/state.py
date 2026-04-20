from __future__ import annotations

from dataclasses import dataclass


@dataclass
class UserDTO:
    id: int
    username: str
    email: str
    display_name: str | None = None


@dataclass
class RoomDTO:
    id: int
    name: str
    owner_username: str
    member_count: int
    is_private: bool
    allow_member_invite: bool
    read_only: bool


@dataclass
class AppState:
    token: str | None = None
    current_user: UserDTO | None = None
    active_room: RoomDTO | None = None
