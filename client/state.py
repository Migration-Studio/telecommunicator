from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from client.api.ws_client import WsClient, NotificationClient


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
    room_type: str
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
    # Active WebSocket connections — closed before creating new ones
    room_ws: "WsClient | None" = field(default=None, repr=False)
    notif_ws: "NotificationClient | None" = field(default=None, repr=False)

    def close_room_ws(self) -> None:
        if self.room_ws is not None:
            self.room_ws.close()
            self.room_ws = None

    def close_notif_ws(self) -> None:
        if self.notif_ws is not None:
            self.notif_ws.close()
            self.notif_ws = None
