from __future__ import annotations

import flet

from client.api.http_client import APIClient, AuthError
from client.state import AppState, UserDTO


def login_view(page: flet.Page, state: AppState) -> None:
    username_field = flet.TextField(label="Username", autofocus=True)
    password_field = flet.TextField(label="Password", password=True, can_reveal_password=True)
    error_text = flet.Text("", color=flet.Colors.RED_400, visible=False)
    submit_btn = flet.ElevatedButton("Login", width=300)
    loading = flet.ProgressRing(visible=False, width=20, height=20)

    async def do_login(e: flet.ControlEvent) -> None:
        error_text.visible = False
        submit_btn.disabled = True
        loading.visible = True
        page.update()

        client = APIClient(base_url="http://localhost:8000", state=state)
        try:
            token_data = await client.login(username_field.value or "", password_field.value or "")
            state.token = token_data["access_token"]
            me = await client.get_me()
            state.current_user = UserDTO(
                id=me["id"],
                username=me["username"],
                email=me["email"],
                display_name=me.get("display_name"),
            )
            from client.views.room_list_view import room_list_view
            room_list_view(page, state)
        except AuthError:
            error_text.value = "Invalid username or password"
            error_text.visible = True
            submit_btn.disabled = False
            loading.visible = False
            page.update()
        except Exception as exc:
            error_text.value = f"Server error: {exc}"
            error_text.visible = True
            submit_btn.disabled = False
            loading.visible = False
            page.update()
        finally:
            await client.aclose()

    submit_btn.on_click = do_login
    password_field.on_submit = do_login

    def go_register(e: flet.ControlEvent) -> None:
        from client.views.register_view import register_view
        register_view(page, state)

    async def do_logout(e: flet.ControlEvent) -> None:
        client = APIClient(base_url="http://localhost:8000", state=state)
        await client.logout()
        await client.aclose()
        login_view(page, state)

    logout_btn = flet.TextButton("Logout", on_click=do_logout, visible=state.token is not None)

    page.controls.clear()
    page.add(
        flet.Column(
            controls=[
                flet.Text("Telecommunicator", size=28, weight=flet.FontWeight.BOLD),
                flet.Text("Sign in to your account", size=14, color=flet.Colors.GREY_600),
                flet.Divider(height=10, color=flet.Colors.TRANSPARENT),
                username_field,
                password_field,
                error_text,
                flet.Row(
                    controls=[submit_btn, loading],
                    alignment=flet.MainAxisAlignment.START,
                    vertical_alignment=flet.CrossAxisAlignment.CENTER,
                ),
                flet.TextButton("Don't have an account? Register", on_click=go_register),
                logout_btn,
            ],
            alignment=flet.MainAxisAlignment.CENTER,
            horizontal_alignment=flet.CrossAxisAlignment.CENTER,
            width=400,
            spacing=10,
        )
    )
    page.update()
