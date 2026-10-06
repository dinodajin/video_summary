from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Callable

from app.config import AppConfig

ProgressFn = Callable[[int, str], None]


@dataclass(slots=True)
class DiarizationSegment:
    start: float
    end: float
    speaker: str


class DiarizationService:
    def __init__(self, config: AppConfig):
        self._config = config
        self._pipeline = None

    def diarize(self, audio_path: Path, progress: ProgressFn | None = None) -> list[DiarizationSegment]:
        pipeline = self._get_pipeline()
        kwargs: dict[str, int] = {}
        if self._config.diarization_min_speakers is not None:
            kwargs["min_speakers"] = self._config.diarization_min_speakers
        if self._config.diarization_max_speakers is not None:
            kwargs["max_speakers"] = self._config.diarization_max_speakers

        if progress:
            progress(52, "화자 구분 처리 중...")
        try:
            diarization = pipeline(self._build_audio_input(audio_path), **kwargs)
        except NameError as exc:
            raise self._to_user_friendly_error(exc) from exc

        annotation = self._select_annotation(diarization)
        out: list[DiarizationSegment] = []
        for turn, _, speaker in annotation.itertracks(yield_label=True):
            out.append(
                DiarizationSegment(
                    start=float(turn.start),
                    end=float(turn.end),
                    speaker=str(speaker),
                )
            )
        out.sort(key=lambda item: item.start)
        return out

    def _get_pipeline(self):
        if self._pipeline is not None:
            return self._pipeline
        try:
            import torch
            from pyannote.audio import Pipeline
        except Exception as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "pyannote.audio가 설치되어 있지 않습니다. requirements 또는 README를 확인해 주세요."
            ) from exc

        model_path = self._config.resolve_diarization_model_path()
        model_repo = self._config.models.diarization.main_repo
        source = self._config.diarization_source.strip().lower()
        token = self._resolve_hf_token()

        try:
            if source == "local":
                if not model_path.exists():
                    raise RuntimeError(
                        "DIARIZATION_SOURCE=local 이지만 로컬 모델 경로가 없습니다. "
                        "DIARIZATION_MODEL_PATH를 확인해 주세요."
                    )
                self._pipeline = Pipeline.from_pretrained(str(model_path))
            elif source == "huggingface":
                if not token:
                    raise RuntimeError(
                        "DIARIZATION_SOURCE=huggingface 사용 시 HF 토큰이 필요합니다. "
                        "DIARIZATION_HF_TOKEN 또는 HF_TOKEN을 설정해 주세요."
                    )
                self._pipeline = self._load_pipeline_from_hf(Pipeline, model_repo, token)
            elif source == "auto":
                if model_path.exists():
                    self._pipeline = Pipeline.from_pretrained(str(model_path))
                elif token:
                    self._pipeline = self._load_pipeline_from_hf(Pipeline, model_repo, token)
                else:
                    raise RuntimeError(
                        "화자 구분 모델을 찾을 수 없습니다. "
                        "로컬 모델 경로를 준비하거나 HF_TOKEN(또는 DIARIZATION_HF_TOKEN)을 설정해 주세요."
                    )
            else:
                raise RuntimeError(
                    "DIARIZATION_SOURCE는 auto/local/huggingface 중 하나여야 합니다."
                )
        except NameError as exc:
            raise self._to_user_friendly_error(exc) from exc

        device = self._config.diarization_device.lower()
        if device == "cuda" or (device == "auto" and torch.cuda.is_available()):
            self._pipeline.to(torch.device("cuda"))

        threshold = getattr(self._config, "diarization_clustering_threshold", None)
        if threshold is not None:
            try:
                self._pipeline.instantiate({"clustering": {"threshold": float(threshold)}})
            except Exception:
                pass
        return self._pipeline

    def _resolve_hf_token(self) -> str:
        token = self._config.diarization_hf_token.strip()
        if token:
            return token
        # load_dotenv 이후를 가정하지만, 런타임에서 환경변수가 바뀌는 경우도 허용한다.
        return os.getenv("HF_TOKEN", "").strip()

    @staticmethod
    def _select_annotation(diarization_result):
        # pyannote.audio 구버전: Annotation을 직접 반환
        if hasattr(diarization_result, "itertracks"):
            return diarization_result

        # pyannote.audio 4.x: DiarizeOutput 반환
        exclusive = getattr(diarization_result, "exclusive_speaker_diarization", None)
        if exclusive is not None and hasattr(exclusive, "itertracks"):
            return exclusive

        regular = getattr(diarization_result, "speaker_diarization", None)
        if regular is not None and hasattr(regular, "itertracks"):
            return regular

        raise RuntimeError(
            "지원되지 않는 화자 구분 출력 형식입니다. pyannote 버전 호환을 확인해 주세요."
        )

    @staticmethod
    def _load_pipeline_from_hf(pipeline_cls, model_repo: str, token: str):
        # pyannote.audio 4.x uses `token`; older versions may use `use_auth_token`.
        try:
            return pipeline_cls.from_pretrained(model_repo, token=token)
        except TypeError as exc:
            if "unexpected keyword argument 'token'" not in str(exc):
                raise
            return pipeline_cls.from_pretrained(model_repo, use_auth_token=token)

    @staticmethod
    def _build_audio_input(audio_path: Path) -> dict[str, object]:
        try:
            import soundfile as sf
            import torch
        except Exception as exc:
            raise RuntimeError(
                "화자 구분 오디오 로딩에 필요한 패키지가 없습니다. "
                "가상환경에서 `pip install soundfile` 실행 후 다시 시도해 주세요."
            ) from exc

        waveform_np, sample_rate = sf.read(str(audio_path), dtype="float32", always_2d=True)
        waveform = torch.from_numpy(waveform_np.T)
        return {"waveform": waveform, "sample_rate": int(sample_rate)}

    @staticmethod
    def _to_user_friendly_error(exc: NameError) -> RuntimeError:
        message = str(exc)
        if "AudioDecoder" in message:
            return RuntimeError(
                "pyannote 오디오 디코더 의존성 문제입니다. "
                "가상환경에서 `pip install soundfile torchcodec` 실행 후 다시 시도해 주세요."
            )
        return RuntimeError(message)
