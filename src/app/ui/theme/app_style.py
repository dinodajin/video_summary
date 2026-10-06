from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QApplication

from app.ui.theme.colors import THEME, ThemeId

_STYLES_DIR = Path(__file__).resolve().parent / "styles"


def _app_qss_template() -> str:
    path = _STYLES_DIR / "app.qss"
    return path.read_text(encoding="utf-8")


def build_stylesheet(theme: str) -> str:
    key: ThemeId = theme if theme in THEME else "light"
    raw = _app_qss_template()
    for name, value in THEME[key].items():
        raw = raw.replace(f"__{name}__", value)
    return raw


def apply_theme(app: QApplication, theme: str) -> ThemeId:
    t: ThemeId = theme if theme in THEME else "light"
    app.setStyleSheet(build_stylesheet(t))
    return t
