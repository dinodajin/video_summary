from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QAbstractItemView,
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
        initial_mentors: list[str] | None = None,
        initial_map_others: bool = SPEAKER_MAP_OTHERS_TO_TRAINEE_DEFAULT,
        initial_trainee_label: str = SPEAKER_DEFAULT_TRAINEE_LABEL,
    ):
        super().__init__(parent)
        self.setWindowTitle("멘토 화자 지정")
        self.resize(680, 620)

        initial_mentor_set = set(initial_mentors or [])
        self._mentor_list = QListWidget()
        self._mentor_list.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self._mentor_list.setMaximumHeight(130)
        for p in previews:
            item = QListWidgetItem(p.speaker_label)
            item.setData(256, p.speaker_label)  # Qt.UserRole without extra Qt import
            self._mentor_list.addItem(item)
            if p.speaker_label in initial_mentor_set:
                item.setSelected(True)

        self._map_others = QCheckBox("선택하지 않은 화자는 모두 교육생으로 묶기")
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
        scroll.setMinimumHeight(250)
        preview_layout.addWidget(scroll)

        form = QFormLayout()
        form.addRow("멘토 화자(복수 선택 가능):", self._mentor_list)
        form.addRow(self._map_others)
        form.addRow("나머지 라벨:", self._trainee_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        intro = QLabel(
            "pyannote가 먼저 목소리별로 화자를 나눕니다. 여기서는 그중 멘토에 해당하는 화자를 "
            "한 명 이상 선택하면 선택된 화자는 모두 '멘토', 나머지는 '교육생'으로 표시합니다.\n"
            "즉 실제 화자 수가 많아도 최종 보고서에서는 멘토/교육생 두 역할만 남길 수 있습니다."
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

    def mentor_labels(self) -> list[str]:
        labels: list[str] = []
        for item in self._mentor_list.selectedItems():
            label = str(item.data(256) or item.text()).strip()
            if label:
                labels.append(label)
        return labels

    # 이전 코드와의 호환용. 첫 번째 멘토만 반환한다.
    def mentor_label(self) -> str:
        labels = self.mentor_labels()
        return labels[0] if labels else ""

    def map_others_to_trainee(self) -> bool:
        return self._map_others.isChecked()

    def trainee_label(self) -> str:
        t = self._trainee_edit.text().strip()
        return t if t else SPEAKER_DEFAULT_TRAINEE_LABEL
