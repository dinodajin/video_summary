from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.constants import (
    SPEAKER_DEFAULT_TRAINEE_LABEL,
    SPEAKER_MAP_OTHERS_TO_TRAINEE_DEFAULT,
)
from app.services.speaker_roles import SpeakerPreview


class SpeakerRoleDialog(QDialog):
    def __init__(
        self,
        parent: QWidget | None,
        previews: list[SpeakerPreview],
        *,
        initial_mentor: str = "",
        initial_map_others: bool = SPEAKER_MAP_OTHERS_TO_TRAINEE_DEFAULT,
        initial_trainee_label: str = SPEAKER_DEFAULT_TRAINEE_LABEL,
    ):
        super().__init__(parent)
        self.setWindowTitle("멘토 화자 지정")
        self.resize(620, 560)

        self._mentor_combo = QComboBox()
        self._mentor_combo.addItem("(지정 안 함)", "")
        for p in previews:
            self._mentor_combo.addItem(p.speaker_label, p.speaker_label)
        if initial_mentor:
            idx = self._mentor_combo.findData(initial_mentor)
            if idx >= 0:
                self._mentor_combo.setCurrentIndex(idx)

        self._map_others = QCheckBox("나머지 화자를 동일 라벨로 묶기")
        self._map_others.setChecked(initial_map_others)
        self._trainee_edit = QLineEdit(initial_trainee_label)
        self._trainee_edit.setPlaceholderText(SPEAKER_DEFAULT_TRAINEE_LABEL)

        preview_box = QGroupBox("화자별 인용·통계 미리보기(전사에서 추출)")
        preview_layout = QVBoxLayout(preview_box)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        inner_layout = QVBoxLayout(inner)
        for p in previews:
            inner_layout.addWidget(self._make_preview_block(p))
        inner_layout.addStretch(1)
        scroll.setWidget(inner)
        scroll.setMinimumHeight(220)
        preview_layout.addWidget(scroll)

        form = QFormLayout()
        form.addRow("멘토:", self._mentor_combo)
        form.addRow(self._map_others)
        form.addRow("나머지 라벨:", self._trainee_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        intro = QLabel(
            "멘토를 고르면 전사 패널의 화자 라벨이 멘토·교육생 등으로 바뀝니다.\n"
            "아래 각 칸의 한 줄 특징·인용은 전사에서 뽑은 통계 미리보기이며 LLM 출력이 아닙니다."
        )
        intro.setObjectName("metaLabel")
        intro.setWordWrap(True)

        root = QVBoxLayout(self)
        root.addWidget(intro)
        root.addWidget(preview_box)
        root.addLayout(form)
        root.addWidget(buttons)

    def _make_preview_block(self, p: SpeakerPreview) -> QGroupBox:
        box = QGroupBox(p.speaker_label)
        v = QVBoxLayout(box)
        sum_te = QTextEdit()
        sum_te.setObjectName("previewSnippet")
        sum_te.setReadOnly(True)
        sum_te.setMaximumHeight(64)
        sum_te.setPlainText(p.summary_line)
        v.addWidget(QLabel("한 줄 특징(통계):"))
        v.addWidget(sum_te)
        stats = (
            f"발화 {p.segment_count}회 · 글자 약 {p.char_count}자 · 글자 비중 약 {p.char_share_ratio:.0%} · "
            f"첫 발화 {p.first_start_sec:.1f}s ~ 마지막 {p.last_end_sec:.1f}s · "
            f"질문형 비율 {p.question_like_ratio:.0%}"
        )
        v.addWidget(QLabel(stats))
        v.addWidget(QLabel("인용 샘플:"))
        if p.quotes:
            for q in p.quotes:
                te = QTextEdit()
                te.setObjectName("previewSnippet")
                te.setReadOnly(True)
                te.setMaximumHeight(64)
                te.setPlainText(q)
                v.addWidget(te)
        else:
            v.addWidget(QLabel("(짧은 발화만 있어 샘플이 없습니다. 목록에서 추정해 선택하세요.)"))
        return box

    def mentor_label(self) -> str:
        return str(self._mentor_combo.currentData() or "").strip()

    def map_others_to_trainee(self) -> bool:
        return self._map_others.isChecked()

    def trainee_label(self) -> str:
        t = self._trainee_edit.text().strip()
        return t if t else SPEAKER_DEFAULT_TRAINEE_LABEL
