from __future__ import annotations

import flet

from client.api.http_client import APIClient, AuthError, ValidationError
from client.state import AppState


def profile_view(page: flet.Page, state: AppState) -> None:
    user = state.current_user

    display_name_field = flet.TextField(
        label="Display name",
        value=user.display_name or "" if user else "",
        expand=True,
    )
    display_name_error = flet.Text("", color=flet.Colors.RED_400, visible=False, size=12)

    async def _save_display_name(e: flet.ControlEvent) -> None:
        display_name_error.visible = False
        page.update()
        client = APIClient(base_url="http://localhost:8000", state=state)
        try:
            updated = await client.update_profile(display_name=display_name_field.value or "")
            if state.current_user is not None:
                state.current_user.display_name = updated.get("display_name")
            page.snack_bar = flet.SnackBar(flet.Text("Display name updated"), open=True)
            page.update()
        except ValidationError:
            display_name_error.value = "Display name must be 1\u201364 characters"
            display_name_error.visible = True
            page.update()
        except AuthError:
            state.token = None
            page.snack_bar = flet.SnackBar(flet.Text("Session expired"), open=True)
            page.update()
            from client.views.login_view import login_view
            login_view(page, state)
        except Exception as exc:
            page.snack_bar = flet.SnackBar(flet.Text(str(exc)), open=True)
            page.update()
        finally:
            await client.aclose()

    current_password_field = flet.TextField(label="Current password", password=True, can_reveal_password=True, expand=True)
    new_password_field = flet.TextField(label="New password", password=True, can_reveal_password=True, expand=True)
    password_error = flet.Text("", color=flet.Colors.RED_400, visible=False, size=12)

    async def _change_password(e: flet.ControlEvent) -> None:
        password_error.visible = False
        page.update()
        client = APIClient(base_url="http://localhost:8000", state=state)
        try:
            await client.change_password(
                current_password=current_password_field.value or "",
                new_password=new_password_field.value or "",
            )
            current_password_field.value = ""
            new_password_field.value = ""
            page.snack_bar = flet.SnackBar(flet.Text("Password changed successfully"), open=True)
            page.update()
        except AuthError:
            password_error.value = "Current password is incorrect"
            password_error.visible = True
            page.update()
        except ValidationError:
            password_error.value = "New password must be at least 8 characters"
            password_error.visible = True
            page.update()
        except Exception as exc:
            page.snack_bar = flet.SnackBar(flet.Text(str(exc)), open=True)
            page.update()
        finally:
            await client.aclose()

    def _go_back(e: flet.ControlEvent) -> None:
        from client.views.room_list_view import room_list_view
        room_list_view(page, state)

    username_text = user.username if user else ""
    email_text = user.email if user else ""
    display_name_text = user.display_name or "(not set)" if user else ""

    page.controls.clear()
    page.add(
        flet.Column(
            controls=[
                flet.Row(
                    controls=[
                        flet.IconButton(icon=flet.Icons.ARROW_BACK, on_click=_go_back, tooltip="Back"),
                        flet.Text("Profile", size=22, weight=flet.FontWeight.BOLD),
                    ],
                    vertical_alignment=flet.CrossAxisAlignment.CENTER,
                ),
                flet.Divider(height=8),
                flet.Text("Account Info", size=16, weight=flet.FontWeight.W_600),
                flet.Text(f"Username: {username_text}", size=14),
                flet.Text(f"Email: {email_text}", size=14),
                flet.Text(f"Display name: {display_name_text}", size=14),
                flet.Divider(height=12),
                flet.Text("Update Display Name", size=16, weight=flet.FontWeight.W_600),
                flet.Row(controls=[display_name_field]),
                display_name_error,
                flet.ElevatedButton("Save", on_click=_save_display_name),
                flet.Divider(height=12),
                flet.Text("Change Password", size=16, weight=flet.FontWeight.W_600),
                flet.Row(controls=[current_password_field]),
                flet.Row(controls=[new_password_field]),
                password_error,
                flet.ElevatedButton("Change Password", on_click=_change_password),
            ],
            expand=True,
            spacing=8,
            scroll=flet.ScrollMode.AUTO,
        )
    )
    page.update()
