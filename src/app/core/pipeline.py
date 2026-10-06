from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from app.config import AppConfig
from app.constants import (
    PIPELINE_PROGRESS_CHECK_AUDIO,
    PIPELINE_PROGRESS_DONE,
    PIPELINE_PROGRESS_EXTRACT_AUDIO,
    PIPELINE_PROGRESS_PREPARE_DIARIZATION,
    PIPELINE_PROGRESS_PREPARE_STT,
    PIPELINE_PROGRESS_VALIDATE_INPUT,
)
from app.services.diarization import DiarizationSegment, DiarizationService
from app.services.ingest import validate_video_file
from app.services.media import ensure_audio_stream, extract_audio_wav
from app.services.stt import (
    SttResult,
    SttSegment,
    SttService,
    rebuild_stt_result_with_segments,
)
from app.services.transcript_formatter import (
    TranscriptSegment,
    build_transcript,
    refine_stt_segments_with_diarization_words,
)

ProgressFn = Callable[[int, str], None]


@dataclass(slots=True)
class PipelineResult:
    transcript: str
    language: str
    segments: list[TranscriptSegment]
    diarization_used: bool
    warnings: list[str]


class VideoPipeline:
    def __init__(self, config: AppConfig):
        self._config = config
        self._stt = SttService(config)
        self._diarization = DiarizationService(config)

    def _format_transcript(
        self,
        stt_segments: list[SttSegment],
        diarization_segments: list[DiarizationSegment],
        *,
        use_timestamps: bool,
    ) -> tuple[str, list[TranscriptSegment]]:
        return build_transcript(
            stt_segments,
            diarization_segments,
            use_timestamps=use_timestamps,
            speaker_label_style=self._config.speaker_label_style,
            smooth_short_spike_sec=self._config.diarization_smooth_short_spike_sec,
        )

    def _resolve_transcript_display(
        self,
        stt_result: SttResult,
        diarization_used: bool,
        diarization_segments: list[DiarizationSegment],
    ) -> tuple[str, list[TranscriptSegment]]:
        if diarization_used:
            return self._format_transcript(
                stt_result.segments,
                diarization_segments,
                use_timestamps=self._config.timestamp_in_transcript,
            )
        return stt_result.transcript, []

    def run(
        self,
        video_path_str: str,
        lang_mode: str,
        manual_language: str | None,
        progress: ProgressFn | None = None,
    ) -> PipelineResult:
        warnings: list[str] = []
        diarization_used = False
        if progress:
            progress(PIPELINE_PROGRESS_VALIDATE_INPUT, "입력 파일 확인 중...")
        video_path = validate_video_file(video_path_str, self._config.max_file_mb)

        if progress:
            progress(PIPELINE_PROGRESS_CHECK_AUDIO, "오디오 트랙 검사 중...")
        ensure_audio_stream(video_path, self._config)

        with tempfile.TemporaryDirectory(prefix="yoyak_") as tmp:
            if progress:
                progress(PIPELINE_PROGRESS_EXTRACT_AUDIO, "오디오 추출 중...")
            audio_path = extract_audio_wav(video_path, Path(tmp), self._config)

            diarization_segments = []
            if self._config.diarization_enabled:
                if progress:
                    progress(PIPELINE_PROGRESS_PREPARE_DIARIZATION, "화자 구분 준비 중...")
                if self._config.diarization_provider.lower() != "pyannote":
                    warnings.append(
                        "지원되지 않는 DIARIZATION_PROVIDER 설정입니다. 일반 전사로 계속합니다."
                    )
                else:
                    try:
                        diarization_segments = self._diarization.diarize(audio_path, progress)
                        diarization_used = bool(diarization_segments)
                    except Exception as exc:
                        warnings.append(f"화자 구분을 사용할 수 없어 일반 전사로 계속합니다: {exc}")

            if progress:
                progress(PIPELINE_PROGRESS_PREPARE_STT, "음성 전사 준비 중...")
            stt_result = self._stt.transcribe(
                audio_path,
                lang_mode,
                manual_language,
                progress,
                word_timestamps=diarization_used and self._config.diarization_refine_word_level,
            )

        if diarization_used and self._config.diarization_refine_word_level:
            refined_segments = refine_stt_segments_with_diarization_words(
                stt_result.segments,
                diarization_segments,
            )
            stt_result = rebuild_stt_result_with_segments(
                stt_result, refined_segments
            )

        transcript_text, transcript_segments = self._resolve_transcript_display(
            stt_result, diarization_used, diarization_segments
        )

        if progress:
            progress(PIPELINE_PROGRESS_DONE, "완료")

        return PipelineResult(
            transcript=transcript_text,
            language=stt_result.detected_language,
            segments=transcript_segments,
            diarization_used=diarization_used,
            warnings=warnings,
        )
