from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from app.config import AppConfig
from app.ui.main_window import MainWindow
from app.ui.theme import apply_theme, load_theme


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    apply_theme(app, load_theme())
    config = AppConfig.load()
    window = MainWindow(config)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
