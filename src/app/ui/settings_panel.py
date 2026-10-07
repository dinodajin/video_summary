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

        self.diarization_check = QCheckBox("화자 구분 사용")
        self.diarization_check.setChecked(True)
        self.hf_token_edit = QLineEdit()
        self.hf_token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.hf_token_edit.setPlaceholderText("hf_...  (pyannote 화자 구분 모델 접근용)")

        self.summary_provider_combo = QComboBox()
        self.summary_provider_combo.addItem("Ollama (로컬 권장)", "ollama")
        self.summary_provider_combo.addItem("OpenAI 호환 API", "openai")
        self.summary_provider_combo.currentIndexChanged.connect(self._sync_summary_ui)
        self.summary_model_edit = QLineEdit("qwen3:8b")
        self.summary_base_url_edit = QLineEdit("http://localhost:11434")
        self.summary_api_key_edit = QLineEdit()
        self.summary_api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.summary_api_key_edit.setPlaceholderText("외부 API 사용 시에만 입력")

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
        form.addRow("Hugging Face Token", self.hf_token_edit)
        form.addRow("요약 엔진", self.summary_provider_combo)
        form.addRow("요약 모델", self.summary_model_edit)
        form.addRow("요약 API 주소", self.summary_base_url_edit)
        form.addRow("요약 API Key", self.summary_api_key_edit)
        self.setLayout(form)
        self._sync_lang_ui()
        self._sync_summary_ui()

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

    def _sync_summary_ui(self) -> None:
        is_ollama = self.get_summary_provider() == "ollama"
        self.summary_api_key_edit.setEnabled(not is_ollama)

    def apply_config(self, config) -> None:
        self.whisper_model_edit.setText(config.models.whisper.name)
        self.diarization_check.setChecked(config.diarization_enabled)
        self.hf_token_edit.setText(config.diarization_hf_token)

        idx = self.summary_provider_combo.findData(config.summary_provider)
        if idx >= 0:
            self.summary_provider_combo.setCurrentIndex(idx)
        self.summary_model_edit.setText(config.summary_model)
        self.summary_base_url_edit.setText(config.summary_base_url)
        self.summary_api_key_edit.setText(config.summary_api_key)
        self._sync_summary_ui()

    def get_lang_mode(self) -> str:
        return str(self.lang_mode_combo.currentData())

    def get_manual_language(self) -> str:
        return str(self.lang_combo.currentData())

    def diarization_enabled(self) -> bool:
        return self.diarization_check.isChecked()

    def get_hf_token(self) -> str:
        return self.hf_token_edit.text().strip()

    def get_whisper_model(self) -> str:
        return self.whisper_model_edit.text().strip() or DEFAULT_WHISPER_MODEL

    def get_summary_provider(self) -> str:
        return str(self.summary_provider_combo.currentData())

    def get_summary_model(self) -> str:
        return self.summary_model_edit.text().strip()

    def get_summary_base_url(self) -> str:
        return self.summary_base_url_edit.text().strip()

    def get_summary_api_key(self) -> str:
        return self.summary_api_key_edit.text().strip()
