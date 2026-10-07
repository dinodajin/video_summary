from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFontDatabase, QGuiApplication
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class ResultsPanel(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 결과 3개 영역 사이의 구분선을 직접 드래그하여 높이를 조정할 수 있음.
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(8)
        splitter.addWidget(self._make_block("전사 결과", "transcript", read_only=True))
        splitter.addWidget(self._make_block("일일 팀 보고서 - 내용/종합 (수정 가능)", "report", read_only=False))
        splitter.addWidget(self._make_block("주차별 기업연계 멘토링 진행현황 (수정 가능)", "weekly", read_only=False))
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 2)
        splitter.setStretchFactor(2, 3)
        splitter.setSizes([260, 260, 360])
        layout.addWidget(splitter)

    def _make_block(self, title: str, key: str, *, read_only: bool) -> QGroupBox:
        box = QGroupBox(title)
        vbox = QVBoxLayout(box)

        text = QTextEdit()
        text.setObjectName("transcriptView")
        text.setReadOnly(read_only)
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

    def set_report(self, value: str, team_code: str = "") -> None:
        self.report_text.setPlainText(value)
        self.report_info.setText(f"팀: {team_code}" if team_code else "")

    def set_weekly_report(self, value: str, team_code: str = "") -> None:
        self.weekly_text.setPlainText(value)
        self.weekly_info.setText(f"팀: {team_code}" if team_code else "")

    def get_weekly_report(self) -> str:
        return self.weekly_text.toPlainText()

    def get_transcript(self) -> str:
        return self.transcript_text.toPlainText()

    def get_report(self) -> str:
        return self.report_text.toPlainText()

    def clear(self) -> None:
        self.transcript_text.clear()
        self.transcript_info.setText("")
        self.report_text.clear()
        self.report_info.setText("")
        self.weekly_text.clear()
        self.weekly_info.setText("")

    def _copy_text(self, value: str) -> None:
        QGuiApplication.clipboard().setText(value)
