from __future__ import annotations

from app.config import DEFAULT_WHISPER_MODEL
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QWidget,
)

from app.ui.theme import apply_theme, load_theme, save_theme


class SettingsPanel(QGroupBox):
    def __init__(self) -> None:
        super().__init__("고급 설정")
        self.theme_combo = QComboBox()
        self.theme_combo.addItem("밝은 모드", "light")
        self.theme_combo.addItem("다크 모드", "dark")
        self._init_theme_selection()

        self.lang_mode_combo = QComboBox()
        self.lang_mode_combo.addItem("기본 한국어", "default")
        self.lang_mode_combo.addItem("자동 감지", "auto")
        self.lang_mode_combo.addItem("수동 선택", "manual")
        self.lang_mode_combo.currentIndexChanged.connect(self._sync_lang_ui)

        self.lang_combo = QComboBox()
        self.lang_combo.addItem("한국어 (ko)", "ko")
        self.lang_combo.addItem("영어 (en)", "en")
        self.lang_combo.addItem("일본어 (ja)", "ja")
        self.lang_combo.addItem("중국어 (zh)", "zh")

        self.whisper_model_edit = QLineEdit(DEFAULT_WHISPER_MODEL)

        self.diarization_check = QCheckBox("화자 구분 사용 (권장)")
        self.diarization_check.setChecked(True)

        self.theme_combo.currentIndexChanged.connect(self._on_ui_theme_changed)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)  # type: ignore[attr-defined]
        form.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)  # type: ignore[attr-defined]
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(8)
        form.addRow("화면 테마", self.theme_combo)
        form.addRow("전사 언어 모드", self.lang_mode_combo)

        lang_row = QWidget()
        lang_layout = QHBoxLayout(lang_row)
        lang_layout.setContentsMargins(0, 0, 0, 0)
        lang_layout.addWidget(QLabel("수동 언어"))
        lang_layout.addWidget(self.lang_combo)
        form.addRow(lang_row)

        form.addRow("Whisper 모델", self.whisper_model_edit)
        form.addRow(self.diarization_check)
        self.setLayout(form)
        self._sync_lang_ui()

    def _init_theme_selection(self) -> None:
        initial = load_theme()
        self.theme_combo.blockSignals(True)
        idx = self.theme_combo.findData(initial)
        if idx >= 0:
            self.theme_combo.setCurrentIndex(idx)
        self.theme_combo.blockSignals(False)

    def _on_ui_theme_changed(self) -> None:
        app = QApplication.instance()
        if not app:
            return
        theme = str(self.theme_combo.currentData())
        apply_theme(app, theme)
        save_theme(theme)

    def _sync_lang_ui(self) -> None:
        is_manual = self.get_lang_mode() == "manual"
        self.lang_combo.setEnabled(is_manual)

    def get_lang_mode(self) -> str:
        return str(self.lang_mode_combo.currentData())

    def get_manual_language(self) -> str:
        return str(self.lang_combo.currentData())

    def diarization_enabled(self) -> bool:
        return self.diarization_check.isChecked()

    def get_whisper_model(self) -> str:
        return self.whisper_model_edit.text().strip() or DEFAULT_WHISPER_MODEL
