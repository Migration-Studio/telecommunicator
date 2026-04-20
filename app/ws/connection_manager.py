from collections import defaultdict

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self._rooms: dict[int, set[WebSocket]] = defaultdict(set)

    async def connect(self, room_id: int, ws: WebSocket) -> None:
        """Register an already-accepted WebSocket for a room."""
        self._rooms[room_id].add(ws)

    async def disconnect(self, room_id: int, ws: WebSocket) -> None:
        self._rooms[room_id].discard(ws)

    async def broadcast(self, room_id: int, payload: dict) -> None:
        sockets = list(self._rooms.get(room_id, set()))
        for ws in sockets:
            try:
                await ws.send_json(payload)
            except Exception:
                self._rooms[room_id].discard(ws)


manager = ConnectionManager()
