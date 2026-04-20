from __future__ import annotations

import flet

from client.state import AppState


def main(page: flet.Page) -> None:
    page.title = "Python Messenger"
    page.theme_mode = flet.ThemeMode.SYSTEM
    page.padding = 0

    state = AppState()

    from client.views.login_view import login_view
    login_view(page, state)


if __name__ == "__main__":
    flet.app(target=main, view=flet.AppView.FLET_APP)
