from __future__ import annotations

import copy
import json
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from app.config import AppConfig
from app.core.pipeline import PipelineResult, VideoPipeline
from app.services.speaker_roles import (
    apply_speaker_label_map,
    build_speaker_label_mapping,
    build_speaker_preview,
    distinct_speaker_labels_in_order,
)
from app.services.transcript_formatter import segments_to_jsonable
from app.utils.errors import to_user_message
from app.ui.results_panel import ResultsPanel
from app.ui.settings_panel import SettingsPanel
from app.ui.speaker_role_dialog import SpeakerRoleDialog
from app.ui.widgets import DropLabel


class Worker(QObject):
    progress = Signal(int, str)
    finished = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        config: AppConfig,
        file_path: str,
        lang_mode: str,
        manual_language: str,
    ):
        super().__init__()
        self._pipeline = VideoPipeline(config)
        self._file_path = file_path
        self._lang_mode = lang_mode
        self._manual_language = manual_language

    def run(self) -> None:
        try:
            result = self._pipeline.run(
                self._file_path,
                self._lang_mode,
                self._manual_language,
                progress=lambda p, m: self.progress.emit(p, m),
            )
            self.finished.emit(result)
        except Exception as exc:
            self.failed.emit(to_user_message(exc))


class MainWindow(QMainWindow):
    def __init__(self, config: AppConfig):
        super().__init__()
        self.config = config
        self.selected_file: str | None = None
        self.worker_thread: QThread | None = None
        self.worker: Worker | None = None
        self.last_result: PipelineResult | None = None
        self._baseline_result: PipelineResult | None = None
        self._role_mapping: dict[str, str] | None = None

        self.setWindowTitle("로컬 동영상 전사")
        self.resize(1000, 760)

        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(0)

        wlay = QVBoxLayout()
        wlay.setContentsMargins(10, 14, 10, 10)
        wlay.setSpacing(8)
        work = QGroupBox("입력 · 진행")
        work.setLayout(wlay)

        self.drop_label = DropLabel()
        self.drop_label.fileDropped.connect(self._on_file_selected)

        self.file_info = QLabel("선택된 파일 없음")
        self.file_info.setObjectName("metaLabel")
        self.progress_text = QLabel("대기 중")
        self.progress_text.setObjectName("metaLabel")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")

        self.settings = SettingsPanel()
        self.settings.whisper_model_edit.setText(config.models.whisper.name)
        self.settings.diarization_check.setChecked(config.diarization_enabled)
        self.settings.setVisible(False)

        button_row = QHBoxLayout()
        self.select_btn = QPushButton("파일 선택")
        self.start_btn = QPushButton("처리 시작")
        self.save_btn = QPushButton("전사 저장")
        self.role_btn = QPushButton("멘토 지정…")
        self.advanced_btn = QPushButton("고급 설정 보기")
        self.advanced_btn.setCheckable(True)
        self.select_btn.clicked.connect(self._pick_file)
        self.start_btn.clicked.connect(self._start_pipeline)
        self.save_btn.clicked.connect(self._save_outputs)
        self.role_btn.clicked.connect(self._open_speaker_role_dialog)
        self.advanced_btn.toggled.connect(self._toggle_advanced_settings)
        self.save_btn.setEnabled(False)
        self.role_btn.setEnabled(False)
        self.start_btn.setObjectName("primaryButton")
        button_row.addWidget(self.select_btn)
        button_row.addWidget(self.start_btn)
        button_row.addWidget(self.save_btn)
        button_row.addWidget(self.role_btn)
        button_row.addWidget(self.advanced_btn)

        self.results = ResultsPanel()

        wlay.addWidget(self.drop_label)
        wlay.addWidget(self.file_info)
        wlay.addLayout(button_row)
        wlay.addWidget(self.settings)
        wlay.addWidget(self.progress_text)
        wlay.addWidget(self.progress_bar)

        splitter = QSplitter(Qt.Orientation.Vertical)  # type: ignore[name-defined, attr-defined]
        splitter.addWidget(work)
        splitter.addWidget(self.results)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([360, 420])

        layout.addWidget(splitter)
        self.setCentralWidget(root)

    def _pick_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "동영상 파일 선택",
            "",
            "Videos (*.mp4 *.mov *.mkv *.avi *.webm *.m4v)",
        )
        if path:
            self._on_file_selected(path)

    def _on_file_selected(self, file_path: str) -> None:
        self.selected_file = file_path
        self.file_info.setText(f"선택된 파일: {Path(file_path).name}")
        self.results.clear()
        self.last_result = None
        self._baseline_result = None
        self._role_mapping = None
        self.progress_bar.setValue(0)
        self.progress_text.setText("파일 준비 완료")
        self.save_btn.setEnabled(False)
        self.role_btn.setEnabled(False)

    def _start_pipeline(self) -> None:
        if not self.selected_file:
            QMessageBox.warning(self, "알림", "먼저 동영상 파일을 선택해 주세요.")
            return
        if self.worker_thread and self.worker_thread.isRunning():
            QMessageBox.information(self, "알림", "이미 처리 중입니다.")
            return

        self.config.models.whisper.name = self.settings.get_whisper_model()
        self.config.diarization_enabled = self.settings.diarization_enabled()
        self.progress_bar.setValue(0)
        self.progress_text.setText("처리 시작")
        self.start_btn.setEnabled(False)

        self.worker_thread = QThread(self)
        self.worker = Worker(
            self.config,
            self.selected_file,
            self.settings.get_lang_mode(),
            self.settings.get_manual_language(),
        )
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.run)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.failed.connect(self._on_failed)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.failed.connect(self.worker_thread.quit)
        self.worker_thread.finished.connect(lambda: self.start_btn.setEnabled(True))
        self.worker_thread.start()

    def _toggle_advanced_settings(self, checked: bool) -> None:
        self.settings.setVisible(checked)
        self.advanced_btn.setText("고급 설정 숨기기" if checked else "고급 설정 보기")

    def _on_progress(self, value: int, message: str) -> None:
        self.progress_bar.setValue(value)
        self.progress_text.setText(message)

    def _on_finished(self, result: PipelineResult) -> None:
        self.last_result = result
        self._baseline_result = PipelineResult(
            transcript=result.transcript,
            language=result.language,
            segments=copy.deepcopy(result.segments),
            diarization_used=result.diarization_used,
            warnings=list(result.warnings),
        )
        self._role_mapping = None
        self.results.set_transcript(
            result.transcript,
            result.language,
            diarization_used=result.diarization_used,
            segment_count=len(result.segments),
        )
        self.progress_text.setText("완료")
        self.progress_bar.setValue(100)
        self.save_btn.setEnabled(True)
        self.role_btn.setEnabled(
            result.diarization_used and len(result.segments) > 0 and self._baseline_result is not None
        )
        if result.warnings:
            QMessageBox.information(self, "안내", "\n".join(result.warnings))

    def _on_failed(self, message: str) -> None:
        self.progress_text.setText("실패")
        QMessageBox.critical(self, "처리 실패", message)

    def _open_speaker_role_dialog(self) -> None:
        if self.last_result is None or self._baseline_result is None:
            QMessageBox.information(self, "알림", "먼저 처리를 완료해 주세요.")
            return
        if not self._baseline_result.diarization_used or not self._baseline_result.segments:
            QMessageBox.information(self, "알림", "화자 구분이 켜진 전사 결과가 있을 때만 사용할 수 있습니다.")
            return

        previews = build_speaker_preview(self._baseline_result.segments)
        if not previews:
            QMessageBox.information(self, "알림", "표시할 화자 세그먼트가 없습니다.")
            return

        initial_mentor = ""
        if self._role_mapping:
            for k, v in self._role_mapping.items():
                if v == "멘토":
                    initial_mentor = k
                    break

        dlg = SpeakerRoleDialog(self, previews, initial_mentor=initial_mentor)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        mentor = dlg.mentor_label()
        distinct = distinct_speaker_labels_in_order(self._baseline_result.segments)
        mapping = build_speaker_label_mapping(
            mentor if mentor else None,
            distinct,
            map_others_to_trainee=dlg.map_others_to_trainee(),
            trainee_label=dlg.trainee_label(),
        )
        transcript, segs = apply_speaker_label_map(
            self._baseline_result.segments,
            mapping,
            use_timestamps=self.config.timestamp_in_transcript,
        )
        self._role_mapping = mapping if mapping else None
        self.last_result = PipelineResult(
            transcript=transcript,
            language=self._baseline_result.language,
            segments=segs,
            diarization_used=self._baseline_result.diarization_used,
            warnings=list(self._baseline_result.warnings),
        )
        note = "역할 라벨 적용됨" if mapping else ""
        self.results.set_transcript(
            transcript,
            self.last_result.language,
            diarization_used=self.last_result.diarization_used,
            segment_count=len(segs),
            role_mapping_note=note,
        )

    def _save_outputs(self) -> None:
        if self.last_result is None:
            QMessageBox.information(self, "알림", "저장할 결과가 없습니다. 먼저 처리를 완료해 주세요.")
            return
        transcript = self.results.get_transcript().strip()
        if not transcript:
            QMessageBox.information(self, "알림", "저장할 전사가 없습니다. 먼저 처리를 완료해 주세요.")
            return

        fmt, ok = QInputDialog.getItem(
            self,
            "저장 형식 선택",
            "전사 파일 형식을 선택하세요:",
            ["txt", "md", "json"],
            0,
            False,
        )
        if not ok:
            return

        default_dir = str(Path(self.selected_file).parent) if self.selected_file else ""
        target_dir = QFileDialog.getExistingDirectory(self, "결과 저장 폴더 선택", default_dir)
        if not target_dir:
            return

        base = Path(self.selected_file).stem if self.selected_file else "result"
        transcript_path = Path(target_dir) / f"{base}_full_transcript.{fmt}"

        if fmt == "txt":
            transcript_path.write_text(transcript, encoding="utf-8")
        elif fmt == "md":
            transcript_path.write_text(f"# 전체 전사\n\n{transcript}\n", encoding="utf-8")
        else:
            transcript_payload = {
                "type": "full_transcript",
                "source_video": Path(self.selected_file).name if self.selected_file else "",
                "content": transcript,
                "diarization_used": self.last_result.diarization_used,
                "segments": segments_to_jsonable(self.last_result.segments),
                "speaker_role_mapping": self._role_mapping,
            }
            transcript_path.write_text(
                json.dumps(transcript_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        QMessageBox.information(
            self,
            "저장 완료",
            f"형식: {fmt}\n전사: {transcript_path.name}",
        )
