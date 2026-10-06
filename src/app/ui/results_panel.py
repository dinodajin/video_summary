from __future__ import annotations

from PySide6.QtGui import QFontDatabase, QGuiApplication
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class ResultsPanel(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(self._make_block("전사 결과", "transcript"))

    def _make_block(self, title: str, key: str) -> QGroupBox:
        box = QGroupBox(title)
        vbox = QVBoxLayout(box)

        text = QTextEdit()
        text.setObjectName("transcriptView")
        text.setReadOnly(True)
        text.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        text.setTabStopDistance(4 * text.fontMetrics().horizontalAdvance(" "))
        text.setPlaceholderText(f"{title}가 여기에 표시됩니다.")

        copy_btn = QPushButton("복사")
        copy_btn.clicked.connect(lambda: self._copy_text(text.toPlainText()))

        info = QLabel("")
        info.setObjectName("metaLabel")

        vbox.addWidget(text)
        h = QHBoxLayout()
        h.addWidget(info)
        h.addStretch(1)
        h.addWidget(copy_btn)
        vbox.addLayout(h)

        setattr(self, f"{key}_text", text)
        setattr(self, f"{key}_info", info)
        return box

    def set_transcript(
        self,
        value: str,
        language: str = "",
        diarization_used: bool = False,
        segment_count: int = 0,
        role_mapping_note: str = "",
    ) -> None:
        self.transcript_text.setPlainText(value)
        details: list[str] = []
        if language:
            details.append(f"감지 언어: {language}")
        if diarization_used:
            details.append(f"화자 구분: ON ({segment_count}개 세그먼트)")
        else:
            details.append("화자 구분: OFF")
        if role_mapping_note:
            details.append(role_mapping_note)
        self.transcript_info.setText(" | ".join(details))

    def get_transcript(self) -> str:
        return self.transcript_text.toPlainText()

    def clear(self) -> None:
        self.transcript_text.clear()
        self.transcript_info.setText("")

    def _copy_text(self, value: str) -> None:
        QGuiApplication.clipboard().setText(value)
