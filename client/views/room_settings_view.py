from __future__ import annotations

import flet

from client.api.http_client import APIClient, ForbiddenError
from client.state import AppState


def room_settings_view(page: flet.Page, state: AppState) -> None:
    room = state.active_room

    def _go_back(e: flet.ControlEvent | None = None) -> None:
        from client.views.room_view import room_view
        room_view(page, state)

    # Guard: non-owner access
    if room is None or state.current_user is None or state.current_user.username != room.owner_username:
        page.snack_bar = flet.SnackBar(flet.Text("Only the room owner can access settings"), open=True)
        page.update()
        _go_back()
        return

    allow_invite_switch = flet.Switch(label="Allow members to invite others", value=room.allow_member_invite)
    read_only_switch = flet.Switch(label="Read-only room", value=room.read_only)

    async def _on_allow_invite_change(e: flet.ControlEvent) -> None:
        new_value: bool = allow_invite_switch.value or False
        client = APIClient(base_url="http://localhost:8000", state=state)
        try:
            updated = await client.update_permissions(room.id, allow_member_invite=new_value)
            room.allow_member_invite = updated.get("allow_member_invite", new_value)
            room.read_only = updated.get("read_only", room.read_only)
            page.snack_bar = flet.SnackBar(flet.Text("Permissions updated"), open=True)
            page.update()
        except ForbiddenError:
            page.snack_bar = flet.SnackBar(flet.Text("Only the room owner can change permissions"), open=True)
            allow_invite_switch.value = not new_value
            page.update()
        except Exception as exc:
            page.snack_bar = flet.SnackBar(flet.Text(str(exc)), open=True)
            allow_invite_switch.value = not new_value
            page.update()
        finally:
            await client.aclose()

    async def _on_read_only_change(e: flet.ControlEvent) -> None:
        new_value: bool = read_only_switch.value or False
        client = APIClient(base_url="http://localhost:8000", state=state)
        try:
            updated = await client.update_permissions(room.id, read_only=new_value)
            room.allow_member_invite = updated.get("allow_member_invite", room.allow_member_invite)
            room.read_only = updated.get("read_only", new_value)
            page.snack_bar = flet.SnackBar(flet.Text("Permissions updated"), open=True)
            page.update()
        except ForbiddenError:
            page.snack_bar = flet.SnackBar(flet.Text("Only the room owner can change permissions"), open=True)
            read_only_switch.value = not new_value
            page.update()
        except Exception as exc:
            page.snack_bar = flet.SnackBar(flet.Text(str(exc)), open=True)
            read_only_switch.value = not new_value
            page.update()
        finally:
            await client.aclose()

    allow_invite_switch.on_change = _on_allow_invite_change
    read_only_switch.on_change = _on_read_only_change

    page.controls.clear()
    page.add(
        flet.Column(
            controls=[
                flet.Row(
                    controls=[
                        flet.IconButton(icon=flet.Icons.ARROW_BACK, on_click=_go_back, tooltip="Back"),
                        flet.Text(f"Room Settings \u2014 {room.name}", size=20, weight=flet.FontWeight.BOLD),
                    ],
                    vertical_alignment=flet.CrossAxisAlignment.CENTER,
                ),
                flet.Divider(height=8),
                flet.Text("Permissions", size=16, weight=flet.FontWeight.W_600),
                allow_invite_switch,
                read_only_switch,
            ],
            expand=True,
            spacing=10,
        )
    )
    page.update()
