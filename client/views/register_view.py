from __future__ import annotations

import flet

from client.api.http_client import APIClient, ConflictError, ValidationError
from client.state import AppState, UserDTO


def register_view(page: flet.Page, state: AppState) -> None:
    username_field = flet.TextField(label="Username", autofocus=True)
    email_field = flet.TextField(label="Email")
    password_field = flet.TextField(label="Password", password=True, can_reveal_password=True)

    username_error = flet.Text("", color=flet.Colors.RED_400, visible=False, size=12)
    email_error = flet.Text("", color=flet.Colors.RED_400, visible=False, size=12)
    password_error = flet.Text("", color=flet.Colors.RED_400, visible=False, size=12)
    general_error = flet.Text("", color=flet.Colors.RED_400, visible=False)

    submit_btn = flet.ElevatedButton("Register", width=300)
    loading = flet.ProgressRing(visible=False, width=20, height=20)

    def _clear_errors() -> None:
        for t in (username_error, email_error, password_error, general_error):
            t.value = ""
            t.visible = False

    async def do_register(e: flet.ControlEvent) -> None:
        _clear_errors()
        submit_btn.disabled = True
        loading.visible = True
        page.update()

        client = APIClient(base_url="http://localhost:8000", state=state)
        try:
            await client.register(
                username=username_field.value or "",
                email=email_field.value or "",
                password=password_field.value or "",
            )
            token_data = await client.login(
                username=username_field.value or "",
                password=password_field.value or "",
            )
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
        except ConflictError as exc:
            msg = exc.message.lower()
            if "username" in msg:
                username_error.value = exc.message
                username_error.visible = True
            elif "email" in msg:
                email_error.value = exc.message
                email_error.visible = True
            else:
                general_error.value = exc.message
                general_error.visible = True
            submit_btn.disabled = False
            loading.visible = False
            page.update()
        except ValidationError as exc:
            msg = exc.message.lower()
            if "password" in msg:
                password_error.value = exc.message
                password_error.visible = True
            elif "email" in msg:
                email_error.value = exc.message
                email_error.visible = True
            elif "username" in msg:
                username_error.value = exc.message
                username_error.visible = True
            else:
                general_error.value = exc.message
                general_error.visible = True
            submit_btn.disabled = False
            loading.visible = False
            page.update()
        except Exception as exc:
            general_error.value = f"Server error: {exc}"
            general_error.visible = True
            submit_btn.disabled = False
            loading.visible = False
            page.update()
        finally:
            await client.aclose()

    submit_btn.on_click = do_register
    password_field.on_submit = do_register

    def go_login(e: flet.ControlEvent) -> None:
        from client.views.login_view import login_view
        login_view(page, state)

    page.controls.clear()
    page.add(
        flet.Column(
            controls=[
                flet.Text("Python Messenger", size=28, weight=flet.FontWeight.BOLD),
                flet.Text("Create a new account", size=14, color=flet.Colors.GREY_600),
                flet.Divider(height=10, color=flet.Colors.TRANSPARENT),
                username_field,
                username_error,
                email_field,
                email_error,
                password_field,
                password_error,
                general_error,
                flet.Row(
                    controls=[submit_btn, loading],
                    alignment=flet.MainAxisAlignment.START,
                    vertical_alignment=flet.CrossAxisAlignment.CENTER,
                ),
                flet.TextButton("Already have an account? Login", on_click=go_login),
            ],
            alignment=flet.MainAxisAlignment.CENTER,
            horizontal_alignment=flet.CrossAxisAlignment.CENTER,
            width=400,
            spacing=10,
        )
    )
    page.update()
