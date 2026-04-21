from __future__ import annotations

import sys
import os

# Ensure the project root is on sys.path so `client.*` imports work
# regardless of how this file is launched (e.g. `flet run client/main.py`)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import flet

from client.state import AppState


def main(page: flet.Page) -> None:
    page.title = "Telecommunicator"
    page.theme_mode = flet.ThemeMode.LIGHT
    page.fonts = {"RobotoFlex": "fonts/RobotoFlex.ttf"}
    page.theme = flet.Theme(color_scheme_seed="#008069", font_family="RobotoFlex")
    page.padding = 0

    state = AppState()

    from client.views.login_view import login_view
    login_view(page, state)


if __name__ == "__main__":
    flet.app(
        target=main,
        view=flet.AppView.FLET_APP,
        assets_dir=os.path.join(os.path.dirname(__file__), "assets"),
    )
