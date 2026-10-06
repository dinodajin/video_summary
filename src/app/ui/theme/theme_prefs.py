from __future__ import annotations

import os

from PySide6.QtCore import QSettings

from app.ui.theme.colors import ThemeId, THEME

_ORG = "Yoyak"
_APP = "yoyak"
_KEY = "ui/theme"
_ENV = "UI_THEME"


def _settings() -> QSettings:
    return QSettings(_ORG, _APP)


def load_theme() -> ThemeId:
    s = _settings()
    stored = s.value(_KEY)
    if stored is not None and str(stored) in THEME:
        return str(stored)  # type: ignore[return-value]
    env = (os.environ.get(_ENV) or "").strip().lower()
    if env in THEME:
        return env  # type: ignore[return-value]
    return "light"


def save_theme(theme: str) -> ThemeId:
    t: ThemeId = theme if theme in THEME else "light"
    s = _settings()
    s.setValue(_KEY, t)
    s.sync()
    return t
