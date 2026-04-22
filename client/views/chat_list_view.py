from __future__ import annotations

import flet

from client.api.http_client import APIClient
from client.api.ws_client import NotificationClient
from client.config import API_URL
from client.state import AppState, RoomDTO


def chat_list_view(page: flet.Page, state: AppState) -> None:
    page.bgcolor = "#f0f2f5"
    
    # Состояние
    personal_chats: list[dict] = []
    group_chats: list[dict] = []
    public_rooms: list[dict] = []
    
    # UI элементы для каждой вкладки
    personal_column = flet.Column(scroll=flet.ScrollMode.AUTO, expand=True, spacing=8)
    group_column = flet.Column(scroll=flet.ScrollMode.AUTO, expand=True, spacing=8)
    public_column = flet.Column(scroll=flet.ScrollMode.AUTO, expand=True, spacing=8)
    
    search_field = flet.TextField(
        label="Поиск чатов",
        prefix_icon=flet.Icons.SEARCH,
        expand=True,
        on_change=lambda e: _filter_chats(e.control.value),
        bgcolor="#ffffff",
        border_color=flet.Colors.TRANSPARENT,
        filled=True,
    )
    
    status_text = flet.Text("", color="#667781", size=12)

    # Создание вкладок
    tabs = flet.Tabs(
        selected_index=0,
        length=3,
        expand=True,
        content=flet.Column(
            expand=True,
            controls=[
                flet.TabBar(
                    tabs=[
                        flet.Tab(label=flet.Text("Личные"), icon=flet.Icons.PERSON),
                        flet.Tab(label=flet.Text("Группы"), icon=flet.Icons.GROUP),
                        flet.Tab(label=flet.Text("Публичные"), icon=flet.Icons.PUBLIC),
                    ]
                ),
                flet.TabBarView(
                    expand=True,
                    controls=[
                        personal_column,
                        group_column,
                        public_column,
                    ]
                ),
            ]
        )
    )

    # Диалог создания личного чата
    username_field = flet.TextField(label="Имя пользователя", autofocus=True)
    personal_error = flet.Text("", color="#ea4335", visible=False, size=12)

    async def _create_personal_chat(e: flet.ControlEvent) -> None:
        personal_error.visible = False
        page.update()
        client = APIClient(base_url=API_URL, state=state)
        try:
            room_data = await client.create_personal_chat(username_field.value or "")
            state.active_room = RoomDTO(
                **{k: room_data[k] for k in RoomDTO.__dataclass_fields__}
            )
            personal_dialog.open = False
            page.update()
            _stop_refresh()
            from client.views.room_view import room_view
            room_view(page, state)
        except Exception as exc:
            personal_error.value = str(exc)
            personal_error.visible = True
            page.update()
        finally:
            await client.aclose()

    personal_dialog = flet.AlertDialog(
        title=flet.Text("Новый личный чат", weight=flet.FontWeight.BOLD, color="#111b21"),
        content=flet.Column(
            controls=[username_field, personal_error], tight=True, spacing=8
        ),
        actions=[
            flet.TextButton("Отмена", on_click=lambda e: _close_personal_dialog(), style=flet.ButtonStyle(color="#008069")),
            flet.ElevatedButton(
                "Создать",
                on_click=_create_personal_chat,
                style=flet.ButtonStyle(bgcolor="#008069", color="#ffffff"),
            ),
        ],
    )

    # Диалог создания группового чата
    group_name_field = flet.TextField(label="Название группы", autofocus=True)
    private_toggle = flet.Switch(label="Приватная группа", value=False)
    group_error = flet.Text("", color="#ea4335", visible=False, size=12)

    async def _create_group_chat(e: flet.ControlEvent) -> None:
        group_error.visible = False
        page.update()
        client = APIClient(base_url=API_URL, state=state)
        try:
            room_data = await client.create_room(
                name=group_name_field.value or "",
                room_type="group",
                is_private=private_toggle.value or False,
            )
            state.active_room = RoomDTO(
                **{k: room_data[k] for k in RoomDTO.__dataclass_fields__}
            )
            group_dialog.open = False
            page.update()
            _stop_refresh()
            from client.views.room_view import room_view
            room_view(page, state)
        except Exception as exc:
            group_error.value = str(exc)
            group_error.visible = True
            page.update()
        finally:
            await client.aclose()

    group_dialog = flet.AlertDialog(
        title=flet.Text("Новая группа", weight=flet.FontWeight.BOLD, color="#111b21"),
        content=flet.Column(
            controls=[group_name_field, private_toggle, group_error], tight=True, spacing=8
        ),
        actions=[
            flet.TextButton("Отмена", on_click=lambda e: _close_group_dialog(), style=flet.ButtonStyle(color="#008069")),
            flet.ElevatedButton(
                "Создать",
                on_click=_create_group_chat,
                style=flet.ButtonStyle(bgcolor="#008069", color="#ffffff"),
            ),
        ],
    )

    def _close_personal_dialog() -> None:
        personal_dialog.open = False
        page.update()

    def _close_group_dialog() -> None:
        group_dialog.open = False
        page.update()

    def _open_personal_dialog(e: flet.ControlEvent) -> None:
        username_field.value = ""
        personal_error.visible = False
        personal_dialog.open = True
        page.update()

    def _open_group_dialog(e: flet.ControlEvent) -> None:
        group_name_field.value = ""
        private_toggle.value = False
        group_error.visible = False
        group_dialog.open = True
        page.update()

    page.overlay.extend([personal_dialog, group_dialog])

    # Обработчик изменения вкладки
    def _on_tab_change(e: flet.ControlEvent) -> None:
        # Обновляем кнопки создания в зависимости от вкладки
        _update_create_buttons()

    def _update_create_buttons():
        """Обновить кнопки создания в зависимости от активной вкладки"""
        create_buttons.controls.clear()
        
        if tabs.selected_index == 0:  # Личные
            create_buttons.controls.append(
                flet.ElevatedButton(
                    "Новый чат",
                    icon=flet.Icons.PERSON_ADD,
                    on_click=_open_personal_dialog,
                    style=flet.ButtonStyle(
                        bgcolor="#25d366",
                        color="#ffffff",
                        shape=flet.RoundedRectangleBorder(radius=20),
                    ),
                )
            )
        elif tabs.selected_index == 1:  # Группы
            create_buttons.controls.append(
                flet.ElevatedButton(
                    "Новая группа",
                    icon=flet.Icons.GROUP_ADD,
                    on_click=_open_group_dialog,
                    style=flet.ButtonStyle(
                        bgcolor="#008069",
                        color="#ffffff",
                        shape=flet.RoundedRectangleBorder(radius=20),
                    ),
                )
            )
        
        page.update()

    # Контейнер для кнопок создания
    create_buttons = flet.Row(
        alignment=flet.MainAxisAlignment.CENTER,
        controls=[]
    )

    def _get_chat_display_name(room: dict) -> str:
        """Получить отображаемое имя чата."""
        if room.get("room_type") == "personal":
            # Для личных чатов показываем имя собеседника
            name = room.get("name", "")
            if state.current_user and state.current_user.username in name:
                parts = name.split(", ")
                return next((p for p in parts if p != state.current_user.username), name)
            return name
        return room.get("name", "")

    def _build_chat_tile(room: dict) -> flet.Control:
        display_name = _get_chat_display_name(room)
        name_initial = display_name[0].upper() if display_name else "?"
        room_type = room.get("room_type", "public")
        
        # Иконка в зависимости от типа
        if room_type == "personal":
            icon = flet.Icons.PERSON
            icon_color = "#25d366"
        elif room_type == "group":
            icon = flet.Icons.GROUP
            icon_color = "#008069"
        else:
            icon = flet.Icons.PUBLIC
            icon_color = "#667781"

        async def on_open(e: flet.ControlEvent, r: dict = room) -> None:
            state.active_room = RoomDTO(
                **{k: r[k] for k in RoomDTO.__dataclass_fields__}
            )
            _stop_refresh()
            from client.views.room_view import room_view
            room_view(page, state)

        subtitle_parts = []
        if room_type != "personal":
            subtitle_parts.append(f"{room['member_count']} участников")
        if room.get("is_private"):
            subtitle_parts.append("Приватный")
        
        subtitle = " • ".join(subtitle_parts) if subtitle_parts else "Чат"

        return flet.Card(
            content=flet.Container(
                content=flet.Row(
                    controls=[
                        flet.Stack(
                            controls=[
                                flet.CircleAvatar(
                                    content=flet.Text(
                                        name_initial,
                                        color="#ffffff",
                                        weight=flet.FontWeight.BOLD,
                                        size=16,
                                    ),
                                    bgcolor="#008069",
                                ),
                                flet.Container(
                                    content=flet.Icon(icon, size=12, color="#ffffff"),
                                    bgcolor=icon_color,
                                    border_radius=10,
                                    padding=2,
                                    right=0,
                                    bottom=0,
                                ),
                            ],
                            width=40,
                            height=40,
                        ),
                        flet.Column(
                            controls=[
                                flet.Text(
                                    display_name,
                                    weight=flet.FontWeight.BOLD,
                                    size=15,
                                    color="#111b21",
                                ),
                                flet.Text(
                                    subtitle,
                                    size=12,
                                    color="#667781",
                                ),
                            ],
                            expand=True,
                            spacing=2,
                        ),
                        flet.IconButton(
                            icon=flet.Icons.ARROW_FORWARD_IOS,
                            icon_size=16,
                            icon_color="#667781",
                            on_click=on_open,
                        ),
                    ],
                    alignment=flet.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=flet.CrossAxisAlignment.CENTER,
                ),
                padding=flet.padding.symmetric(horizontal=16, vertical=12),
                on_click=on_open,
            ),
            bgcolor="#ffffff",
            elevation=1,
        )

    def _filter_chats(query: str) -> None:
        q = (query or "").lower()
        
        # Фильтрация личных чатов
        filtered_personal = [
            r for r in personal_chats 
            if q in _get_chat_display_name(r).lower()
        ] if q else personal_chats
        
        # Фильтрация групповых чатов
        filtered_groups = [
            r for r in group_chats 
            if q in r["name"].lower()
        ] if q else group_chats
        
        # Фильтрация публичных комнат
        filtered_public = [
            r for r in public_rooms 
            if q in r["name"].lower()
        ] if q else public_rooms
        
        # Обновление UI
        personal_column.controls.clear()
        for r in filtered_personal:
            personal_column.controls.append(_build_chat_tile(r))
        if not filtered_personal:
            personal_column.controls.append(
                flet.Text("Нет личных чатов.", color="#667781", text_align=flet.TextAlign.CENTER)
            )
        
        group_column.controls.clear()
        for r in filtered_groups:
            group_column.controls.append(_build_chat_tile(r))
        if not filtered_groups:
            group_column.controls.append(
                flet.Text("Нет групповых чатов.", color="#667781", text_align=flet.TextAlign.CENTER)
            )
        
        public_column.controls.clear()
        for r in filtered_public:
            public_column.controls.append(_build_chat_tile(r))
        if not filtered_public:
            public_column.controls.append(
                flet.Text("Нет публичных комнат.", color="#667781", text_align=flet.TextAlign.CENTER)
            )
        
        page.update()

    async def _load_chats() -> None:
        nonlocal personal_chats, group_chats, public_rooms
        status_text.value = "Загрузка чатов…"
        page.update()
        
        client = APIClient(base_url=API_URL, state=state)
        try:
            # Загрузить мои чаты (личные и групповые)
            my_chats = await client.get_my_rooms()
            personal_chats = [r for r in my_chats if r.get("room_type") == "personal"]
            group_chats = [r for r in my_chats if r.get("room_type") == "group"]
            
            # Загрузить публичные комнаты
            public_rooms = await client.list_rooms()
            
            _filter_chats(search_field.value or "")
            
            total = len(personal_chats) + len(group_chats) + len(public_rooms)
            status_text.value = f"Загружено {total} чатов"
        except Exception as exc:
            status_text.value = f"Ошибка загрузки: {exc}"
        finally:
            page.update()
            await client.aclose()

    async def do_logout(e: flet.ControlEvent) -> None:
        _stop_refresh()
        client = APIClient(base_url=API_URL, state=state)
        await client.logout()
        await client.aclose()
        from client.views.login_view import login_view
        login_view(page, state)

    def _go_profile(e: flet.ControlEvent) -> None:
        _stop_refresh()
        from client.views.profile_view import profile_view
        profile_view(page, state)

    # Auto-refresh и уведомления
    _active = {"running": True}

    # Stop any previous notification WS before starting a new one
    state.close_notif_ws()

    async def _auto_refresh() -> None:
        import asyncio
        while _active["running"]:
            await asyncio.sleep(10)
            if not _active["running"]:
                break
            await _load_chats()

    def _on_notification(payload: dict) -> None:
        if payload.get("type") == "invite":
            room_data = payload.get("payload", {})
            room_name = room_data.get("name", "чат")
            page.snack_bar = flet.SnackBar(
                flet.Text(f'Вас пригласили в "{room_name}"!', color="#ffffff"), 
                open=True, 
                bgcolor="#008069"
            )
            page.update()
            page.run_task(_load_chats)

    async def _start_notifications() -> None:
        # Close any existing notification client first
        state.close_notif_ws()
        
        nc = NotificationClient(
            token=state.token or "", on_notification=_on_notification
        )
        state.notif_ws = nc
        await nc.connect()

    def _stop_refresh() -> None:
        _active["running"] = False
        state.close_notif_ws()

    # Обработчик изменения вкладки
    def _on_tab_change(e: flet.ControlEvent) -> None:
        # Обновляем кнопки создания в зависимости от вкладки
        _update_create_buttons()

    def _update_create_buttons():
        """Обновить кнопки создания в зависимости от активной вкладки"""
        create_buttons.controls.clear()
        
        if tabs.selected_index == 0:  # Личные
            create_buttons.controls.append(
                flet.ElevatedButton(
                    "Новый чат",
                    icon=flet.Icons.PERSON_ADD,
                    on_click=_open_personal_dialog,
                    style=flet.ButtonStyle(
                        bgcolor="#25d366",
                        color="#ffffff",
                        shape=flet.RoundedRectangleBorder(radius=20),
                    ),
                )
            )
        elif tabs.selected_index == 1:  # Группы
            create_buttons.controls.append(
                flet.ElevatedButton(
                    "Новая группа",
                    icon=flet.Icons.GROUP_ADD,
                    on_click=_open_group_dialog,
                    style=flet.ButtonStyle(
                        bgcolor="#008069",
                        color="#ffffff",
                        shape=flet.RoundedRectangleBorder(radius=20),
                    ),
                )
            )
        
        page.update()

    # Контейнер для кнопок создания
    create_buttons = flet.Row(
        alignment=flet.MainAxisAlignment.CENTER,
        controls=[]
    )

    tabs.on_change = _on_tab_change

    # Верхняя панель
    top_bar = flet.Container(
        content=flet.Row(
            controls=[
                flet.Text(
                    "Чаты",
                    size=22,
                    weight=flet.FontWeight.BOLD,
                    color="#ffffff",
                    expand=True,
                ),
                flet.IconButton(
                    icon=flet.Icons.REFRESH,
                    on_click=lambda e: page.run_task(_load_chats),
                    tooltip="Обновить",
                    icon_color="#ffffff",
                ),
                flet.IconButton(
                    icon=flet.Icons.PERSON,
                    on_click=_go_profile,
                    tooltip="Профиль",
                    icon_color="#ffffff",
                ),
                flet.TextButton(
                    "Выйти",
                    on_click=do_logout,
                    style=flet.ButtonStyle(color="#ffffff"),
                ),
            ],
            alignment=flet.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=flet.CrossAxisAlignment.CENTER,
        ),
        bgcolor="#008069",
        padding=flet.padding.symmetric(horizontal=16, vertical=12),
    )

    page.controls.clear()
    page.add(
        flet.Column(
            controls=[
                top_bar,
                flet.Container(
                    content=flet.Row(controls=[search_field]),
                    padding=flet.padding.symmetric(horizontal=16, vertical=8),
                ),
                flet.Container(
                    content=status_text, 
                    padding=flet.padding.symmetric(horizontal=16)
                ),
                flet.Container(
                    content=create_buttons,
                    padding=flet.padding.symmetric(horizontal=16, vertical=8),
                ),
                tabs,
            ],
            expand=True,
            spacing=0,
        )
    )
    
    # Установить начальные кнопки создания
    _update_create_buttons()
    page.update()
    page.run_task(_load_chats)
    page.run_task(_auto_refresh)
    page.run_task(_start_notifications)