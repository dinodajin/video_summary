from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from faster_whisper import WhisperModel

from app.config import AppConfig
from app.constants import (
    STT_PROGRESS_TRANSCRIBE_DONE,
    STT_PROGRESS_TRANSCRIBING,
    STT_PROGRESS_UPDATE_EVERY_SEGMENTS,
)
from app.utils.errors import SttError

ProgressFn = Callable[[int, str], None]


@dataclass(slots=True)
class SttResult:
    transcript: str
    detected_language: str
    segments: list["SttSegment"]


@dataclass(slots=True)
class SttWord:
    start: float
    end: float
    word: str


@dataclass(slots=True)
class SttSegment:
    start: float
    end: float
    text: str
    words: list[SttWord] | None = None


class SttService:
    def __init__(self, config: AppConfig):
        self._config = config
        self._model: WhisperModel | None = None

    def _get_model(self) -> WhisperModel:
        if self._model is None:
            device, compute_type = self._resolve_whisper_runtime()
            self._model = WhisperModel(
                self._config.models.whisper.name,
                device=device,
                compute_type=compute_type,
            )
        return self._model

    def _resolve_whisper_runtime(self) -> tuple[str, str]:
        configured_device = (self._config.models.whisper.device or "auto").strip().lower()
        configured_compute = (
            self._config.models.whisper.compute_type or "auto"
        ).strip().lower()

        if configured_device not in {"auto", "cpu", "cuda"}:
            raise SttError(
                "AI_WHISPER_DEVICE는 auto/cpu/cuda 중 하나여야 합니다."
            )

        if configured_device == "cuda":
            runtime_device = "cuda"
        elif configured_device == "cpu":
            runtime_device = "cpu"
        else:
            runtime_device = "cuda" if _cuda_available() else "cpu"

        if configured_compute != "auto":
            return runtime_device, configured_compute

        if runtime_device == "cuda":
            return runtime_device, "int8_float16"
        return runtime_device, "int8"

    def transcribe(
        self,
        audio_path: Path,
        lang_mode: str,
        manual_language: str | None,
        progress: ProgressFn | None = None,
        word_timestamps: bool = False,
    ) -> SttResult:
        try:
            model = self._get_model()
            language = None
            if lang_mode == "manual" and manual_language:
                language = manual_language
            elif lang_mode == "default":
                language = self._config.default_lang

            segments, info = model.transcribe(
                str(audio_path),
                language=language,
                vad_filter=True,
                word_timestamps=word_timestamps,
            )
            lines: list[str] = []
            parsed_segments: list[SttSegment] = []
            count = 0
            for seg in segments:
                text = seg.text.strip()
                if text:
                    lines.append(text)
                    words_list: list[SttWord] | None = None
                    if word_timestamps and getattr(seg, "words", None):
                        words_list = [
                            SttWord(start=float(w.start), end=float(w.end), word=w.word)
                            for w in (seg.words or [])
                        ]
                    parsed_segments.append(
                        SttSegment(
                            start=float(seg.start or 0.0),
                            end=float(seg.end or 0.0),
                            text=text,
                            words=words_list,
                        )
                    )
                count += 1
                if progress and count % STT_PROGRESS_UPDATE_EVERY_SEGMENTS == 0:
                    progress(STT_PROGRESS_TRANSCRIBING, "전사 중...")

            if progress:
                progress(STT_PROGRESS_TRANSCRIBE_DONE, "전사 완료")

            return SttResult(
                transcript=" ".join(lines).strip(),
                detected_language=info.language or self._config.default_lang,
                segments=parsed_segments,
            )
        except Exception as exc:
            raise SttError(str(exc)) from exc


def rebuild_stt_result_with_segments(
    result: SttResult,
    segments: list[SttSegment],
) -> SttResult:
    lines = [s.text.strip() for s in segments if s.text.strip()]
    return SttResult(
        transcript=" ".join(lines).strip(),
        detected_language=result.detected_language,
        segments=segments,
    )


def _cuda_available() -> bool:
    try:
        import torch
    except Exception:
        return False
    return bool(torch.cuda.is_available())
