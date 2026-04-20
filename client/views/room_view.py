from __future__ import annotations

import flet

from client.api.http_client import APIClient, AuthError
from client.api.ws_client import WsClient
from client.state import AppState


def room_view(page: flet.Page, state: AppState) -> None:
    room = state.active_room
    if room is None:
        return

    messages_list = flet.ListView(
        expand=True,
        spacing=4,
        auto_scroll=True,
    )

    message_input = flet.TextField(
        label="Type a message\u2026",
        expand=True,
        multiline=False,
        on_submit=lambda e: page.run_task(_send_message),
    )

    reconnecting_banner = flet.Container(
        content=flet.Text("Reconnecting\u2026", color=flet.Colors.WHITE, size=13),
        bgcolor=flet.Colors.ORANGE_700,
        padding=flet.padding.symmetric(horizontal=12, vertical=6),
        visible=False,
        border_radius=4,
    )

    _state: dict = {"min_id": None, "loading_older": False, "ws_client": None}

    def _build_message_tile(msg: dict) -> flet.Control:
        author = msg.get("author_username", "?")
        body = msg.get("body", "")
        ts_raw = msg.get("created_at", "")
        ts = ts_raw
        if isinstance(ts_raw, str) and "T" in ts_raw:
            ts = ts_raw.split("T")[1][:5]
        return flet.Container(
            content=flet.Row(
                controls=[
                    flet.Text(f"[{author}]", weight=flet.FontWeight.BOLD, size=13, color=flet.Colors.BLUE_700),
                    flet.Text(body, size=13, expand=True),
                    flet.Text(ts, size=11, color=flet.Colors.GREY_500),
                ],
                spacing=6,
                vertical_alignment=flet.CrossAxisAlignment.START,
            ),
            padding=flet.padding.symmetric(horizontal=8, vertical=4),
        )

    def _on_ws_message(payload: dict) -> None:
        if payload.get("type") == "message":
            msg = payload.get("payload", payload)
            messages_list.controls.append(_build_message_tile(msg))
            reconnecting_banner.visible = False
            page.update()

    def _on_reconnecting(delay: float) -> None:
        reconnecting_banner.visible = True
        page.update()

    async def _load_messages(before_id: int | None = None) -> list[dict]:
        client = APIClient(base_url="http://localhost:8000", state=state)
        try:
            return await client.get_messages(room.id, before_id=before_id, limit=50)
        except AuthError:
            state.token = None
            page.snack_bar = flet.SnackBar(flet.Text("Session expired"), open=True)
            page.update()
            from client.views.login_view import login_view
            login_view(page, state)
            return []
        except Exception as exc:
            page.snack_bar = flet.SnackBar(flet.Text(str(exc)), open=True)
            page.update()
            return []
        finally:
            await client.aclose()

    async def _initial_load() -> None:
        msgs = await _load_messages()
        msgs_sorted = sorted(msgs, key=lambda m: m["id"])
        if msgs_sorted:
            _state["min_id"] = msgs_sorted[0]["id"]
            for m in msgs_sorted:
                messages_list.controls.append(_build_message_tile(m))
        page.update()

    async def _load_older() -> None:
        if _state["loading_older"] or _state["min_id"] is None:
            return
        _state["loading_older"] = True
        msgs = await _load_messages(before_id=_state["min_id"])
        if msgs:
            msgs_sorted = sorted(msgs, key=lambda m: m["id"])
            _state["min_id"] = msgs_sorted[0]["id"]
            new_tiles = [_build_message_tile(m) for m in msgs_sorted]
            messages_list.controls = new_tiles + messages_list.controls
            page.update()
        _state["loading_older"] = False

    async def _send_message() -> None:
        body = (message_input.value or "").strip()
        if not body:
            return
        ws: WsClient | None = _state.get("ws_client")
        if ws is None:
            return
        try:
            await ws.send_message(room.id, body)
            message_input.value = ""
            page.update()
        except Exception as exc:
            page.snack_bar = flet.SnackBar(flet.Text(str(exc)), open=True)
            page.update()

    def _on_scroll(e: flet.OnScrollEvent) -> None:
        if e.pixels is not None and e.pixels <= 50:
            page.run_task(_load_older)

    messages_list.on_scroll = _on_scroll

    async def _start_ws() -> None:
        ws = WsClient(token=state.token or "", room_id=room.id, on_message=_on_ws_message, on_reconnecting=_on_reconnecting)
        _state["ws_client"] = ws
        await ws.connect()

    def _go_back(e: flet.ControlEvent) -> None:
        ws: WsClient | None = _state.get("ws_client")
        if ws is not None:
            ws.close()
        state.active_room = None
        from client.views.room_list_view import room_list_view
        room_list_view(page, state)

    def _go_settings(e: flet.ControlEvent) -> None:
        from client.views.room_settings_view import room_settings_view
        room_settings_view(page, state)

    is_owner = state.current_user is not None and room.owner_username == state.current_user.username

    top_bar_controls: list[flet.Control] = [
        flet.IconButton(icon=flet.Icons.ARROW_BACK, on_click=_go_back, tooltip="Back"),
        flet.Text(room.name, size=20, weight=flet.FontWeight.BOLD, expand=True),
    ]
    if is_owner:
        top_bar_controls.append(flet.IconButton(icon=flet.Icons.SETTINGS, on_click=_go_settings, tooltip="Room settings"))

    page.controls.clear()
    page.add(
        flet.Column(
            controls=[
                flet.Row(controls=top_bar_controls, vertical_alignment=flet.CrossAxisAlignment.CENTER),
                reconnecting_banner,
                flet.Divider(height=4),
                messages_list,
                flet.Divider(height=4),
                flet.Row(
                    controls=[message_input, flet.ElevatedButton("Send", on_click=lambda e: page.run_task(_send_message), icon=flet.Icons.SEND)],
                    vertical_alignment=flet.CrossAxisAlignment.CENTER,
                ),
            ],
            expand=True,
            spacing=6,
        )
    )
    page.update()
    page.run_task(_initial_load)
    page.run_task(_start_ws)
