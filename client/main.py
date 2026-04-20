from __future__ import annotations

import sys
import os

# Ensure the project root is on sys.path so `client.*` imports work
# regardless of how this file is launched (e.g. `flet run client/main.py`)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
