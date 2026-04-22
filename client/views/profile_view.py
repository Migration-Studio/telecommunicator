from __future__ import annotations

import flet

from client.api.http_client import APIClient, AuthError, ValidationError
from client.config import API_URL
from client.state import AppState


def profile_view(page: flet.Page, state: AppState) -> None:
    page.bgcolor = "#f0f2f5"
    user = state.current_user

    # Reactive info labels
    display_name_info = flet.Text(
        f"Display name: {user.display_name or '(not set)' if user else ''}",
        size=14,
        color="#111b21",
    )

    display_name_field = flet.TextField(
        label="New display name",
        value=user.display_name or "" if user else "",
        expand=True,
        bgcolor="#ffffff",
        border_color="#e0e0e0",
    )
    display_name_error = flet.Text("", color="#ea4335", visible=False, size=12)

    async def _save_display_name(e: flet.ControlEvent) -> None:
        display_name_error.visible = False
        page.update()
        client = APIClient(base_url=API_URL, state=state)
        try:
            updated = await client.update_profile(
                display_name=display_name_field.value or ""
            )
            new_dn = updated.get("display_name")
            if state.current_user is not None:
                state.current_user.display_name = new_dn
            display_name_info.value = f"Display name: {new_dn or '(not set)'}"
            page.snack_bar = flet.SnackBar(
                flet.Text("Display name updated", color="#ffffff"), open=True, bgcolor="#008069"
            )
            page.update()
        except ValidationError:
            display_name_error.value = "Display name must be 1–64 characters"
            display_name_error.visible = True
            page.update()
        except AuthError:
            state.token = None
            page.snack_bar = flet.SnackBar(
                flet.Text("Session expired", color="#ffffff"), open=True, bgcolor="#ea4335"
            )
            page.update()
            from client.views.login_view import login_view

            login_view(page, state)
        except Exception as exc:
            page.snack_bar = flet.SnackBar(flet.Text(str(exc), color="#ffffff"), open=True, bgcolor="#ea4335")
            page.update()
        finally:
            await client.aclose()

    current_password_field = flet.TextField(
        label="Current password",
        password=True,
        can_reveal_password=True,
        expand=True,
        bgcolor="#ffffff",
        border_color="#e0e0e0",
    )
    new_password_field = flet.TextField(
        label="New password",
        password=True,
        can_reveal_password=True,
        expand=True,
        bgcolor="#ffffff",
        border_color="#e0e0e0",
    )
    password_error = flet.Text("", color="#ea4335", visible=False, size=12)

    async def _change_password(e: flet.ControlEvent) -> None:
        password_error.visible = False
        page.update()
        client = APIClient(base_url=API_URL, state=state)
        try:
            await client.change_password(
                current_password=current_password_field.value or "",
                new_password=new_password_field.value or "",
            )
            current_password_field.value = ""
            new_password_field.value = ""
            page.snack_bar = flet.SnackBar(
                flet.Text("Password changed successfully", color="#ffffff"), open=True, bgcolor="#008069"
            )
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
            page.snack_bar = flet.SnackBar(flet.Text(str(exc), color="#ffffff"), open=True, bgcolor="#ea4335")
            page.update()
        finally:
            await client.aclose()

    def _go_back(e: flet.ControlEvent) -> None:
        from client.views.chat_list_view import chat_list_view

        chat_list_view(page, state)

    # --- Message alignment setting ---
    _alignment_options = [
        ("По умолчанию (мои справа, чужие слева)", "default"),
        ("Все слева", "left"),
        ("Все справа", "right"),
    ]
    alignment_dropdown = flet.Dropdown(
        value=state.message_alignment,
        options=[flet.dropdown.Option(key=v, text=label) for label, v in _alignment_options],
        expand=True,
        bgcolor="#ffffff",
        border_color="#e0e0e0",
    )

    def _on_alignment_change(e: flet.ControlEvent) -> None:
        import logging
        log = logging.getLogger(__name__)
        new_val = alignment_dropdown.value or "default"
        log.info("[profile_view] Dropdown changed to %r", new_val)
        state.message_alignment = new_val
        log.info("[profile_view] state.message_alignment is now %r", state.message_alignment)
        if state.secure_storage is not None:
            state.secure_storage.set("settings.message_alignment", state.message_alignment)
            log.info("[profile_view] Saved to secure_storage")
        else:
            log.warning("[profile_view] secure_storage is None — not saved!")
        page.snack_bar = flet.SnackBar(
            flet.Text("Настройка сохранена", color="#ffffff"), open=True, bgcolor="#008069"
        )
        page.update()

    alignment_dropdown.on_change = _on_alignment_change

    def _save_alignment(e: flet.ControlEvent) -> None:
        """Explicit save button — fallback if on_change doesn't fire."""
        import logging
        log = logging.getLogger(__name__)
        new_val = alignment_dropdown.value or "default"
        log.info("[profile_view] Save button clicked, value=%r", new_val)
        state.message_alignment = new_val
        if state.secure_storage is not None:
            state.secure_storage.set("settings.message_alignment", new_val)
            log.info("[profile_view] Saved via button to secure_storage")
        page.snack_bar = flet.SnackBar(
            flet.Text("Настройка сохранена", color="#ffffff"), open=True, bgcolor="#008069"
        )
        page.update()

    page.controls.clear()
    page.add(
        flet.Column(
            controls=[
                flet.Container(
                    content=flet.Row(
                        controls=[
                            flet.IconButton(
                                icon=flet.Icons.ARROW_BACK,
                                on_click=_go_back,
                                tooltip="Back",
                                icon_color="#ffffff",
                            ),
                            flet.Text(
                                "Profile",
                                size=22,
                                weight=flet.FontWeight.BOLD,
                                color="#ffffff",
                            ),
                        ],
                        vertical_alignment=flet.CrossAxisAlignment.CENTER,
                    ),
                    bgcolor="#008069",
                    padding=flet.padding.symmetric(horizontal=8, vertical=8),
                ),
                flet.Container(
                    content=flet.Column(
                        controls=[
                            flet.Card(
                                content=flet.Container(
                                    content=flet.Column(
                                        controls=[
                                            flet.Text(
                                                "Account Info",
                                                size=16,
                                                weight=flet.FontWeight.W_600,
                                                color="#111b21",
                                            ),
                                            flet.Divider(height=8),
                                            flet.Row(
                                                controls=[
                                                    flet.Icon(
                                                        flet.Icons.BADGE,
                                                        color="#667781",
                                                    ),
                                                    flet.Text(
                                                        f"Username: {user.username if user else ''}",
                                                        size=14,
                                                        color="#111b21",
                                                    ),
                                                ],
                                                spacing=12,
                                            ),
                                            flet.Row(
                                                controls=[
                                                    flet.Icon(
                                                        flet.Icons.EMAIL,
                                                        color="#667781",
                                                    ),
                                                    flet.Text(
                                                        f"Email: {user.email if user else ''}",
                                                        size=14,
                                                        color="#111b21",
                                                    ),
                                                ],
                                                spacing=12,
                                            ),
                                            flet.Row(
                                                controls=[
                                                    flet.Icon(
                                                        flet.Icons.LABEL,
                                                        color="#667781",
                                                    ),
                                                    display_name_info,
                                                ],
                                                spacing=12,
                                            ),
                                        ],
                                        spacing=12,
                                    ),
                                    padding=20,
                                ),
                                bgcolor="#ffffff",
                                elevation=1,
                            ),
                            flet.Card(
                                content=flet.Container(
                                    content=flet.Column(
                                        controls=[
                                            flet.Text(
                                                "Update Display Name",
                                                size=16,
                                                weight=flet.FontWeight.W_600,
                                                color="#111b21",
                                            ),
                                            flet.Divider(height=8),
                                            flet.Row(
                                                controls=[display_name_field]
                                            ),
                                            display_name_error,
                                            flet.ElevatedButton(
                                                "Save",
                                                on_click=_save_display_name,
                                                style=flet.ButtonStyle(
                                                    bgcolor="#008069",
                                                    color="#ffffff",
                                                    shape=flet.RoundedRectangleBorder(
                                                        radius=8
                                                    ),
                                                    padding=flet.padding.symmetric(
                                                        vertical=12, horizontal=24
                                                    ),
                                                ),
                                            ),
                                        ],
                                        spacing=12,
                                    ),
                                    padding=20,
                                ),
                                bgcolor="#ffffff",
                                elevation=1,
                            ),
                            flet.Card(
                                content=flet.Container(
                                    content=flet.Column(
                                        controls=[
                                            flet.Text(
                                                "Change Password",
                                                size=16,
                                                weight=flet.FontWeight.W_600,
                                                color="#111b21",
                                            ),
                                            flet.Divider(height=8),
                                            flet.Row(
                                                controls=[current_password_field]
                                            ),
                                            flet.Row(
                                                controls=[new_password_field]
                                            ),
                                            password_error,
                                            flet.ElevatedButton(
                                                "Change Password",
                                                on_click=_change_password,
                                                style=flet.ButtonStyle(
                                                    bgcolor="#008069",
                                                    color="#ffffff",
                                                    shape=flet.RoundedRectangleBorder(
                                                        radius=8
                                                    ),
                                                    padding=flet.padding.symmetric(
                                                        vertical=12, horizontal=24
                                                    ),
                                                ),
                                            ),
                                        ],
                                        spacing=12,
                                    ),
                                    padding=20,
                                ),
                                bgcolor="#ffffff",
                                elevation=1,
                            ),
                            flet.Card(
                                content=flet.Container(
                                    content=flet.Column(
                                        controls=[
                                            flet.Text(
                                                "Выравнивание сообщений",
                                                size=16,
                                                weight=flet.FontWeight.W_600,
                                                color="#111b21",
                                            ),
                                            flet.Divider(height=8),
                                            flet.Row(controls=[alignment_dropdown]),
                                            flet.ElevatedButton(
                                                "Сохранить",
                                                on_click=_save_alignment,
                                                style=flet.ButtonStyle(
                                                    bgcolor="#008069",
                                                    color="#ffffff",
                                                    shape=flet.RoundedRectangleBorder(radius=8),
                                                    padding=flet.padding.symmetric(vertical=12, horizontal=24),
                                                ),
                                            ),
                                        ],
                                        spacing=12,
                                    ),
                                    padding=20,
                                ),
                                bgcolor="#ffffff",
                                elevation=1,
                            ),
                        ],
                        spacing=12,
                        scroll=flet.ScrollMode.AUTO,
                    ),
                    padding=16,
                    expand=True,
                ),
            ],
            expand=True,
            spacing=0,
        )
    )
    page.update()