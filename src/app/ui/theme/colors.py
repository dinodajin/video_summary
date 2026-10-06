from __future__ import annotations

from typing import Literal

ThemeId = Literal["light", "dark"]

# Keys match placeholders in styles/app.qss: __KEY__
THEME: dict[ThemeId, dict[str, str]] = {
    "light": {
        "BG_WINDOW": "#e8e9ec",
        "BG_WIDGET": "#f4f5f7",
        "BG_ELEVATED": "#ffffff",
        "TEXT_PRIMARY": "#1c1c1e",
        "TEXT_MUTED": "#636366",
        "BORDER": "#c7c7cc",
        "BORDER_DASH": "#8e8e93",
        "ACCENT": "#007aff",
        "ACCENT_HOVER": "#0062cc",
        "BG_INPUT": "#ffffff",
        "PROGRESS_TRACK": "#d1d1d6",
        "PROGRESS_CHUNK": "#34c759",
        "SELECTION_BG": "#007aff",
        "SELECTION_TEXT": "#ffffff",
        "PLACEHOLDER": "#8e8e93",
    },
    "dark": {
        "BG_WINDOW": "#1c1c1e",
        "BG_WIDGET": "#2c2c2e",
        "BG_ELEVATED": "#3a3a3c",
        "TEXT_PRIMARY": "#f2f2f7",
        "TEXT_MUTED": "#8e8e93",
        "BORDER": "#48484a",
        "BORDER_DASH": "#636366",
        "ACCENT": "#0a84ff",
        "ACCENT_HOVER": "#409cff",
        "BG_INPUT": "#3a3a3c",
        "PROGRESS_TRACK": "#48484a",
        "PROGRESS_CHUNK": "#30d158",
        "SELECTION_BG": "#0a84ff",
        "SELECTION_TEXT": "#ffffff",
        "PLACEHOLDER": "#8e8e93",
    },
}
