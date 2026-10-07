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
    QScrollArea,
    QFrame,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from app.config import AppConfig
from app.core.pipeline import PipelineResult, VideoPipeline
from app.services.ssafy_reporting import (
    SsafyReportBuilder, CombinedReport, TEAM_CODES, parse_daily_text, parse_weekly_text
)
from app.services.ssafy_template_export import (
    export_daily_docx, export_weekly_xlsx, list_week_sheets
)
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


class ReportWorker(QObject):
    progress = Signal(str)
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, config: AppConfig, transcript: str, team_code: str):
        super().__init__()
        self._summarizer = SsafyReportBuilder(config)
        self._transcript = transcript
        self._team_code = team_code

    def run(self) -> None:
        try:
            report = self._summarizer.summarize(
                self._transcript, self._team_code, progress=self.progress.emit
            )
            self.finished.emit(report)
        except Exception as exc:
            self.failed.emit(str(exc))


class MainWindow(QMainWindow):
    def __init__(self, config: AppConfig):
        super().__init__()
        self.config = config
        self.selected_file: str | None = None
        self.imported_transcript_file: str | None = None
        self.worker_thread: QThread | None = None
        self.worker: Worker | None = None
        self.report_thread: QThread | None = None
        self.report_worker: ReportWorker | None = None
        self.last_result: PipelineResult | None = None
        self.last_report: CombinedReport | None = None
        self.team_reports: dict[str, CombinedReport] = {}
        self.report_team_code: str = ""
        self._baseline_result: PipelineResult | None = None
        self._role_mapping: dict[str, str] | None = None

        self.setWindowTitle("멘토링 영상 전사 · 보고서 요약")
        self.resize(1100, 860)

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
        self.settings.apply_config(config)
        self.settings.setVisible(False)

        button_row = QHBoxLayout()
        self.select_btn = QPushButton("파일 선택")
        self.import_btn = QPushButton("전사본 불러오기")
        self.start_btn = QPushButton("전사 시작")
        self.role_btn = QPushButton("멘토 선택…")
        self.summary_btn = QPushButton("보고서 요약 생성")
        self.save_btn = QPushButton("TXT/JSON 저장")
        self.docx_btn = QPushButton("일일 DOCX 반영")
        self.xlsx_btn = QPushButton("주간 XLSX 반영")
        self.advanced_btn = QPushButton("고급 설정 보기")
        self.advanced_btn.setCheckable(True)

        self.select_btn.clicked.connect(self._pick_file)
        self.import_btn.clicked.connect(self._import_transcript)
        self.start_btn.clicked.connect(self._start_pipeline)
        self.role_btn.clicked.connect(self._open_speaker_role_dialog)
        self.summary_btn.clicked.connect(self._start_report_summary)
        self.save_btn.clicked.connect(self._save_outputs)
        self.docx_btn.clicked.connect(self._export_daily_docx)
        self.xlsx_btn.clicked.connect(self._export_weekly_xlsx)
        self.advanced_btn.toggled.connect(self._toggle_advanced_settings)

        self.save_btn.setEnabled(False)
        self.docx_btn.setEnabled(False)
        self.xlsx_btn.setEnabled(False)
        self.role_btn.setEnabled(False)
        self.summary_btn.setEnabled(False)
        self.start_btn.setObjectName("primaryButton")
        self.summary_btn.setObjectName("primaryButton")

        button_row.addWidget(self.select_btn)
        button_row.addWidget(self.import_btn)
        button_row.addWidget(self.start_btn)
        button_row.addWidget(self.role_btn)
        button_row.addWidget(self.summary_btn)
        button_row.addWidget(self.save_btn)
        button_row.addWidget(self.advanced_btn)

        export_row = QHBoxLayout()
        export_row.addWidget(QLabel("서울 5반 누적 보고서 내보내기"))
        self.accumulated_info = QLabel("누적 팀: 없음")
        self.accumulated_info.setObjectName("metaLabel")
        export_row.addWidget(self.accumulated_info)
        export_row.addWidget(self.docx_btn)
        export_row.addWidget(self.xlsx_btn)
        export_row.addStretch(1)

        self.results = ResultsPanel()

        wlay.addWidget(self.drop_label)
        wlay.addWidget(self.file_info)
        wlay.addLayout(button_row)
        wlay.addLayout(export_row)
        wlay.addWidget(self.settings)
        wlay.addWidget(self.progress_text)
        wlay.addWidget(self.progress_bar)

        splitter = QSplitter(Qt.Orientation.Vertical)  # type: ignore[name-defined, attr-defined]
        splitter.addWidget(work)
        splitter.addWidget(self.results)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(8)
        splitter.setSizes([360, 500])

        layout.addWidget(splitter)

        # 작은 화면에서도 상·하단이 잘리지 않도록 전체 창을 스크롤 가능하게 함.
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setWidget(root)
        self.setCentralWidget(scroll)

    def _pick_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "동영상 파일 선택",
            "",
            "Videos (*.mp4 *.mov *.mkv *.avi *.webm *.m4v)",
        )
        if path:
            self._on_file_selected(path)

    def _import_transcript(self) -> None:
        """저장된 STT 결과를 불러와 동영상을 재전사하지 않고 보고서 재생성."""
        if self.worker_thread and self.worker_thread.isRunning():
            QMessageBox.information(self, "알림", "전사 작업이 끝난 뒤 불러올 수 있습니다.")
            return
        if self.report_thread and self.report_thread.isRunning():
            QMessageBox.information(self, "알림", "보고서 작성이 끝난 뒤 불러올 수 있습니다.")
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "저장된 전사본 불러오기",
            "",
            "전사본 (*.txt *.md *.json)",
        )
        if not file_path:
            return
        try:
            source = Path(file_path)
            raw = source.read_text(encoding="utf-8-sig")
            if source.suffix.lower() == ".json":
                payload = json.loads(raw)
                if not isinstance(payload, dict) or not isinstance(payload.get("content"), str):
                    raise ValueError("전사본 JSON에는 문자열 content 필드가 필요합니다.")
                transcript = payload["content"].strip()
            elif source.suffix.lower() == ".md":
                # 내보낸 전사본 MD의 제목만 제거한다.
                transcript = raw.removeprefix("# 전체 전사").strip()
            else:
                transcript = raw.strip()
            if not transcript:
                raise ValueError("전사본 내용이 비어 있습니다.")
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            QMessageBox.warning(self, "전사본 불러오기 실패", str(exc))
            return

        self._remember_edits()
        self.selected_file = None
        self.imported_transcript_file = str(source)
        self.results.clear()
        self._on_finished(PipelineResult(
            transcript=transcript,
            language="ko",
            segments=[],
            diarization_used=False,
            warnings=[],
        ))
        self.file_info.setText(f"불러온 전사본: {source.name}")
        self.progress_text.setText("전사본 불러오기 완료 · 보고서 요약 생성 가능")

    def _on_file_selected(self, file_path: str) -> None:
        self._remember_edits()
        self.selected_file = file_path
        self.imported_transcript_file = None
        self.file_info.setText(f"선택된 파일: {Path(file_path).name}")
        self.results.clear()
        self.last_result = None
        self.last_report = None
        self.report_team_code = ""
        self._baseline_result = None
        self._role_mapping = None
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_text.setText("파일 준비 완료")
        self.save_btn.setEnabled(False)
        self.role_btn.setEnabled(False)
        self.summary_btn.setEnabled(False)

    def _apply_runtime_settings(self) -> None:
        self.config.models.whisper.name = self.settings.get_whisper_model()
        self.config.diarization_enabled = self.settings.diarization_enabled()
        self.config.diarization_hf_token = self.settings.get_hf_token()
        self.config.summary_provider = self.settings.get_summary_provider()
        self.config.summary_model = self.settings.get_summary_model()
        self.config.summary_base_url = self.settings.get_summary_base_url()
        self.config.summary_api_key = self.settings.get_summary_api_key()

    def _validate_diarization_ready(self) -> bool:
        if not self.config.diarization_enabled:
            return True

        source = self.config.diarization_source.strip().lower()
        model_path = self.config.resolve_diarization_model_path()
        local_exists = (
            model_path.exists()
            and model_path.is_dir()
            and ((model_path / "config.yaml").exists() or (model_path / "pipeline.yaml").exists())
        )
        token_exists = bool(self.config.diarization_hf_token.strip())

        if source == "local" and not local_exists:
            QMessageBox.warning(
                self,
                "화자 구분 설정 필요",
                "화자 구분을 켰지만 로컬 pyannote 모델을 찾을 수 없습니다.\n"
                "고급 설정/환경설정의 DIARIZATION_MODEL_PATH를 확인해 주세요.",
            )
            return False

        if source in {"auto", "huggingface"} and not local_exists and not token_exists:
            QMessageBox.warning(
                self,
                "화자 구분 설정 필요",
                "화자 구분을 켰지만 pyannote 모델을 사용할 수 있는 Hugging Face Token이 없습니다.\n\n"
                "고급 설정에서 HF Token(hf_...)을 입력해야 합니다.\n"
                "또한 Hugging Face에서 pyannote 화자 구분 모델 사용 조건에 동의되어 있어야 합니다.\n\n"
                "참고: 실제 사람 수를 2명으로 제한하는 것이 아니라, 먼저 목소리별 화자를 나눈 뒤 "
                "멘토 화자를 선택하고 나머지를 모두 교육생으로 묶습니다.",
            )
            return False
        return True

    def _start_pipeline(self) -> None:
        if not self.selected_file:
            QMessageBox.warning(self, "알림", "먼저 동영상 파일을 선택해 주세요.")
            return
        if self.worker_thread and self.worker_thread.isRunning():
            QMessageBox.information(self, "알림", "이미 처리 중입니다.")
            return

        self._apply_runtime_settings()
        if not self._validate_diarization_ready():
            return

        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_text.setText("처리 시작")
        self.start_btn.setEnabled(False)
        self.role_btn.setEnabled(False)
        self.summary_btn.setEnabled(False)

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
        self.last_report = None
        self.report_team_code = ""
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
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.save_btn.setEnabled(True)
        self.summary_btn.setEnabled(True)
        self.role_btn.setEnabled(
            result.diarization_used and len(result.segments) > 0 and self._baseline_result is not None
        )

        if self.config.diarization_enabled and not result.diarization_used:
            self.progress_text.setText("전사 완료 · 화자 구분 실패")
            detail = "\n".join(result.warnings) if result.warnings else "화자 구분 결과가 생성되지 않았습니다."
            QMessageBox.warning(
                self,
                "화자 구분 실패",
                "전사는 완료됐지만 요청한 화자 구분은 적용되지 않았습니다.\n\n" + detail,
            )
        else:
            self.progress_text.setText("완료")
            if result.warnings:
                QMessageBox.information(self, "안내", "\n".join(result.warnings))

    def _on_failed(self, message: str) -> None:
        self.progress_bar.setRange(0, 100)
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

        initial_mentors: list[str] = []
        if self._role_mapping:
            initial_mentors = [k for k, v in self._role_mapping.items() if v == "멘토"]

        dlg = SpeakerRoleDialog(self, previews, initial_mentors=initial_mentors)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        mentors = dlg.mentor_labels()
        distinct = distinct_speaker_labels_in_order(self._baseline_result.segments)
        mapping = build_speaker_label_mapping(
            mentors,
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
        note = (
            f"역할 라벨 적용됨 · 멘토 {len(mentors)}개 화자 / 나머지 교육생"
            if mapping
            else ""
        )
        self.results.set_transcript(
            transcript,
            self.last_result.language,
            diarization_used=self.last_result.diarization_used,
            segment_count=len(segs),
            role_mapping_note=note,
        )

    def _start_report_summary(self) -> None:
        transcript = self.results.get_transcript().strip()
        if not transcript:
            QMessageBox.information(self, "알림", "먼저 전사를 완료해 주세요.")
            return
        if self.report_thread and self.report_thread.isRunning():
            QMessageBox.information(self, "알림", "이미 보고서를 생성 중입니다.")
            return

        default_code = self.report_team_code
        source_file = self.selected_file or self.imported_transcript_file
        if not default_code and source_file:
            import re
            found = re.search(r"A50[1-9]", Path(source_file).stem.upper())
            if found:
                default_code = found.group(0)
        index = TEAM_CODES.index(default_code) if default_code in TEAM_CODES else 0
        team_code, ok = QInputDialog.getItem(
            self, "서울 5반 팀 선택", "이번 영상이 해당하는 팀을 선택하세요:",
            list(TEAM_CODES), index, False,
        )
        if not ok:
            return

        self._apply_runtime_settings()
        provider = self.config.summary_provider.strip().lower()
        if provider == "ollama" and not self.config.summary_model.strip():
            QMessageBox.warning(self, "요약 설정 필요", "고급 설정에서 Ollama 모델명을 입력해 주세요.")
            return
        if provider in {"openai", "openai_compatible"} and not self.config.summary_api_key.strip():
            QMessageBox.warning(self, "요약 설정 필요", "OpenAI 호환 API를 사용하려면 API Key를 입력해 주세요.")
            return

        self.report_team_code = team_code.strip()
        self.summary_btn.setEnabled(False)
        self.progress_text.setText("보고서 요약 생성 중...")
        self.progress_bar.setRange(0, 0)

        self.report_thread = QThread(self)
        self.report_worker = ReportWorker(self.config, transcript, self.report_team_code)
        self.report_worker.moveToThread(self.report_thread)
        self.report_thread.started.connect(self.report_worker.run)
        self.report_worker.progress.connect(self.progress_text.setText)
        self.report_worker.finished.connect(self._on_report_finished)
        self.report_worker.failed.connect(self._on_report_failed)
        self.report_worker.finished.connect(self.report_thread.quit)
        self.report_worker.failed.connect(self.report_thread.quit)
        self.report_thread.finished.connect(lambda: self.summary_btn.setEnabled(True))
        self.report_thread.start()

    def _on_report_finished(self, report: CombinedReport) -> None:
        self.last_report = report
        self.report_team_code = report.daily.team_code
        self.results.set_report(report.daily.render(), report.daily.team_code)
        self.results.set_weekly_report(report.weekly.render(), report.daily.team_code)
        self.team_reports[report.daily.team_code] = report
        self._update_accumulated_info()
        self.docx_btn.setEnabled(True)
        self.xlsx_btn.setEnabled(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.progress_text.setText("보고서 요약 완료")
        self.save_btn.setEnabled(True)


    def _update_accumulated_info(self) -> None:
        teams = [code for code in TEAM_CODES if code in self.team_reports]
        if teams:
            self.accumulated_info.setText(f"누적 팀 ({len(teams)}): {', '.join(teams)}")
        else:
            self.accumulated_info.setText("누적 팀: 없음")

    def _on_report_failed(self, message: str) -> None:
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.progress_text.setText("보고서 요약 실패")
        QMessageBox.critical(self, "보고서 요약 실패", message)

    def _remember_edits(self) -> None:
        if not self.report_team_code or not self.results.get_report().strip():
            return
        current = self.team_reports.get(self.report_team_code)
        if current is None:
            return
        try:
            current.daily = parse_daily_text(self.results.get_report(), self.report_team_code)
            current.weekly = parse_weekly_text(self.results.get_weekly_report())
        except ValueError:
            # 내용 구분이 수정 중이라 일시적으로 깨진 경우 원본을 유지한다.
            pass

    def _validated_reports(self) -> dict[str, CombinedReport] | None:
        if self.report_team_code and self.report_team_code in self.team_reports:
            try:
                current = self.team_reports[self.report_team_code]
                current.daily = parse_daily_text(self.results.get_report(), self.report_team_code)
                current.weekly = parse_weekly_text(self.results.get_weekly_report())
            except ValueError as exc:
                QMessageBox.warning(self, "보고서 양식 확인", str(exc))
                return None
        if not self.team_reports:
            QMessageBox.information(self, "알림", "먼저 최소 한 팀의 보고서를 생성해 주세요.")
            return None
        return self.team_reports

    def _export_daily_docx(self) -> None:
        reports = self._validated_reports()
        if reports is None:
            return
        src, _ = QFileDialog.getOpenFileName(
            self, "일일 보고서 템플릿 선택 (서울 5반)", "", "Word 문서 (*.docx)"
        )
        if not src:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "작성한 일일 보고서 저장", str(Path(src).with_name(Path(src).stem + "_작성본.docx")),
            "Word 문서 (*.docx)",
        )
        if not path:
            return
        try:
            updated = export_daily_docx(src, path, {k: v.daily for k, v in reports.items()})
        except Exception as exc:
            QMessageBox.critical(self, "DOCX 반영 실패", str(exc))
            return
        QMessageBox.information(self, "DOCX 저장", f"완료: {Path(path).name}\n반영 팀: {', '.join(updated)}")

    def _export_weekly_xlsx(self) -> None:
        reports = self._validated_reports()
        if reports is None:
            return
        src, _ = QFileDialog.getOpenFileName(
            self, "기업연계 멘토링 진행현황 템플릿 선택", "", "Excel 문서 (*.xlsx)"
        )
        if not src:
            return
        try:
            choices = list_week_sheets(src)
            if not choices:
                raise ValueError("'1주차 진행현황'과 같은 주차별 시트를 찾지 못했습니다.")
        except Exception as exc:
            QMessageBox.critical(self, "템플릿 확인 실패", str(exc))
            return
        sheet, ok = QInputDialog.getItem(
            self, "작성할 주차 선택", "반영할 주차별 시트:", choices, 0, False
        )
        if not ok:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "작성한 주간 보고서 저장", str(Path(src).with_name(Path(src).stem + "_작성본.xlsx")),
            "Excel 문서 (*.xlsx)",
        )
        if not path:
            return
        try:
            updated = export_weekly_xlsx(
                src, path, {k: v.weekly for k, v in reports.items()}, sheet_name=sheet
            )
        except Exception as exc:
            QMessageBox.critical(self, "XLSX 반영 실패", str(exc))
            return
        QMessageBox.information(
            self, "XLSX 저장", f"완료: {Path(path).name}\n{sheet}: {', '.join(updated)}\n"
            "※ 멘토링 횟수/시간(G/H열)은 자동 계산하지 않으므로 직접 확인해 주세요."
        )

    def _save_outputs(self) -> None:
        self._remember_edits()
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
            "결과 파일 형식을 선택하세요:",
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

        if self.selected_file:
            base = Path(self.selected_file).stem
        elif self.imported_transcript_file:
            base = Path(self.imported_transcript_file).stem.removesuffix("_full_transcript") + "_재요약"
        else:
            base = "result"
        transcript_path = Path(target_dir) / f"{base}_full_transcript.{fmt}"
        report_text = self.results.get_report().strip()
        report_path: Path | None = None

        if fmt == "txt":
            transcript_path.write_text(transcript, encoding="utf-8")
            if report_text:
                report_path = Path(target_dir) / f"{base}_daily_report.txt"
                report_path.write_text(report_text, encoding="utf-8")
        elif fmt == "md":
            transcript_path.write_text(f"# 전체 전사\n\n{transcript}\n", encoding="utf-8")
            if report_text:
                report_path = Path(target_dir) / f"{base}_daily_report.md"
                report_path.write_text(f"# 팀 진행 보고서\n\n{report_text}\n", encoding="utf-8")
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
            if report_text:
                report_path = Path(target_dir) / f"{base}_daily_report.json"
                report_payload = {
                    "type": "daily_project_report",
                    "team_code": self.report_team_code,
                    "rendered": report_text,
                    "content": self.last_report.daily.content if self.last_report else None,
                    "summary": self.last_report.daily.summary if self.last_report else None,
                }
                report_path.write_text(
                    json.dumps(report_payload, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )

        weekly_text = self.results.get_weekly_report().strip()
        if weekly_text:
            weekly_path = Path(target_dir) / f"{base}_weekly_mentoring.{fmt}"
            if fmt == "json":
                weekly_path.write_text(json.dumps({"team_code": self.report_team_code, "rendered": weekly_text}, ensure_ascii=False, indent=2), encoding="utf-8")
            else:
                weekly_path.write_text(weekly_text, encoding="utf-8")
        detail = f"형식: {fmt}\n전사: {transcript_path.name}"
        if report_path is not None:
            detail += f"\n보고서: {report_path.name}"
        QMessageBox.information(self, "저장 완료", detail)
