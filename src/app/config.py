from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

DEFAULT_WHISPER_MODEL = "turbo"
DEFAULT_WHISPER_DEVICE = "auto"
DEFAULT_WHISPER_COMPUTE_TYPE = "auto"
DEFAULT_DIARIZATION_MODEL_PATH = ".models/pyannote/speaker-diarization-3.1"
DEFAULT_DIARIZATION_REPO_MAIN = "pyannote/speaker-diarization-3.1"
DEFAULT_DIARIZATION_REPO_SEGMENTATION = "pyannote/segmentation-3.0"
DEFAULT_DIARIZATION_REPO_EMBEDDING = "pyannote/wespeaker-voxceleb-resnet34-LM"
DEFAULT_DIARIZATION_REPO_COMMUNITY = "pyannote/speaker-diarization-community-1"
DEFAULT_DIARIZATION_REFINE_WORD_LEVEL = True
DEFAULT_DIARIZATION_SMOOTH_SHORT_SPIKE_SEC = 1.0


@dataclass(slots=True)
class WhisperModelConfig:
    name: str = DEFAULT_WHISPER_MODEL
    device: str = DEFAULT_WHISPER_DEVICE
    compute_type: str = DEFAULT_WHISPER_COMPUTE_TYPE


@dataclass(slots=True)
class DiarizationModelConfig:
    path: str = DEFAULT_DIARIZATION_MODEL_PATH
    main_repo: str = DEFAULT_DIARIZATION_REPO_MAIN
    segmentation_repo: str = DEFAULT_DIARIZATION_REPO_SEGMENTATION
    embedding_repo: str = DEFAULT_DIARIZATION_REPO_EMBEDDING
    community_repo: str = DEFAULT_DIARIZATION_REPO_COMMUNITY


@dataclass(slots=True)
class AIModelsConfig:
    whisper: WhisperModelConfig = field(default_factory=WhisperModelConfig)
    diarization: DiarizationModelConfig = field(default_factory=DiarizationModelConfig)


@dataclass(slots=True)
class AppConfig:
    ffmpeg_path: str = ""
    ffprobe_path: str = ""
    models: AIModelsConfig = field(default_factory=AIModelsConfig)
    max_file_mb: int = 8192
    default_lang: str = "ko"
    lang_mode: str = "default"
    diarization_enabled: bool = False
    diarization_provider: str = "pyannote"
    diarization_source: str = "auto"
    diarization_hf_token: str = ""
    diarization_min_speakers: int | None = None
    diarization_max_speakers: int | None = None
    diarization_device: str = "auto"
    diarization_refine_word_level: bool = DEFAULT_DIARIZATION_REFINE_WORD_LEVEL
    diarization_smooth_short_spike_sec: float = DEFAULT_DIARIZATION_SMOOTH_SHORT_SPIKE_SEC
    diarization_clustering_threshold: float | None = None
    timestamp_in_transcript: bool = True
    speaker_label_style: str = "ko"

    @classmethod
    def load(cls) -> "AppConfig":
        load_dotenv()
        diarization_min_speakers = _get_optional_int("DIARIZATION_MIN_SPEAKERS")
        diarization_max_speakers = _get_optional_int("DIARIZATION_MAX_SPEAKERS")
        diarization_clustering_threshold = _get_optional_float("DIARIZATION_CLUSTERING_THRESHOLD")
        models = AIModelsConfig(
            whisper=WhisperModelConfig(
                name=_get_env(("AI_WHISPER_MODEL", "WHISPER_MODEL"), DEFAULT_WHISPER_MODEL),
                device=_get_env(
                    ("AI_WHISPER_DEVICE", "WHISPER_DEVICE"),
                    DEFAULT_WHISPER_DEVICE,
                ),
                compute_type=_get_env(
                    ("AI_WHISPER_COMPUTE_TYPE", "WHISPER_COMPUTE_TYPE"),
                    DEFAULT_WHISPER_COMPUTE_TYPE,
                ),
            ),
            diarization=DiarizationModelConfig(
                path=_get_env(
                    ("AI_DIARIZATION_MODEL_PATH", "DIARIZATION_MODEL_PATH"),
                    DEFAULT_DIARIZATION_MODEL_PATH,
                ),
                main_repo=_get_env(
                    ("AI_DIARIZATION_REPO_MAIN", "DIARIZATION_REPO_MAIN"),
                    DEFAULT_DIARIZATION_REPO_MAIN,
                ),
                segmentation_repo=_get_env(
                    ("AI_DIARIZATION_REPO_SEGMENTATION", "DIARIZATION_REPO_SEGMENTATION"),
                    DEFAULT_DIARIZATION_REPO_SEGMENTATION,
                ),
                embedding_repo=_get_env(
                    ("AI_DIARIZATION_REPO_EMBEDDING", "DIARIZATION_REPO_EMBEDDING"),
                    DEFAULT_DIARIZATION_REPO_EMBEDDING,
                ),
                community_repo=_get_env(
                    ("AI_DIARIZATION_REPO_COMMUNITY", "DIARIZATION_REPO_COMMUNITY"),
                    DEFAULT_DIARIZATION_REPO_COMMUNITY,
                ),
            ),
        )
        return cls(
            ffmpeg_path=os.getenv("FFMPEG_PATH", ""),
            ffprobe_path=os.getenv("FFPROBE_PATH", ""),
            models=models,
            max_file_mb=int(os.getenv("MAX_FILE_MB", "8192")),
            default_lang=os.getenv("DEFAULT_LANG", "ko"),
            lang_mode=os.getenv("LANG_MODE", "default"),
            diarization_enabled=_get_bool("DIARIZATION_ENABLED", False),
            diarization_provider=os.getenv("DIARIZATION_PROVIDER", "pyannote"),
            diarization_source=os.getenv("DIARIZATION_SOURCE", "auto"),
            diarization_hf_token=_get_env(
                ("DIARIZATION_HF_TOKEN", "HF_TOKEN", "HUGGINGFACE_TOKEN"),
                "",
            ),
            diarization_min_speakers=diarization_min_speakers,
            diarization_max_speakers=diarization_max_speakers,
            diarization_device=os.getenv("DIARIZATION_DEVICE", "auto"),
            diarization_refine_word_level=_get_bool(
                "DIARIZATION_REFINE_WORD_LEVEL",
                DEFAULT_DIARIZATION_REFINE_WORD_LEVEL,
            ),
            diarization_smooth_short_spike_sec=float(
                os.getenv(
                    "DIARIZATION_SMOOTH_SHORT_SPIKE_SEC",
                    str(DEFAULT_DIARIZATION_SMOOTH_SHORT_SPIKE_SEC),
                )
            ),
            diarization_clustering_threshold=diarization_clustering_threshold,
            timestamp_in_transcript=_get_bool("TIMESTAMP_IN_TRANSCRIPT", True),
            speaker_label_style=os.getenv("SPEAKER_LABEL_STYLE", "ko"),
        )

    def resolve_ffmpeg(self) -> str:
        if self.ffmpeg_path:
            return str(Path(self.ffmpeg_path))
        return "ffmpeg"

    def resolve_ffprobe(self) -> str:
        if self.ffprobe_path:
            return str(Path(self.ffprobe_path))
        return "ffprobe"

    def resolve_diarization_model_path(self) -> Path:
        model_path = Path(self.models.diarization.path).expanduser()
        if model_path.is_absolute():
            return model_path
        return (_project_root() / model_path).resolve()

    @property
    def whisper_model(self) -> str:
        return self.models.whisper.name

    @whisper_model.setter
    def whisper_model(self, value: str) -> None:
        self.models.whisper.name = value

    @property
    def diarization_model_path(self) -> str:
        return self.models.diarization.path

    @diarization_model_path.setter
    def diarization_model_path(self, value: str) -> None:
        self.models.diarization.path = value


def _get_bool(key: str, default: bool) -> bool:
    raw = os.getenv(key)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _get_optional_int(key: str) -> int | None:
    raw = os.getenv(key, "").strip()
    if not raw:
        return None
    return int(raw)


def _get_optional_float(key: str) -> float | None:
    raw = os.getenv(key, "").strip()
    if not raw:
        return None
    return float(raw)


def _get_env(keys: tuple[str, ...], default: str) -> str:
    for key in keys:
        value = os.getenv(key)
        if value is not None:
            return value
    return default


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]
