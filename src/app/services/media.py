from __future__ import annotations

import json
import subprocess
from pathlib import Path

from app.config import AppConfig
from app.utils.errors import MediaError


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            check=False,
            text=True,
            capture_output=True,
            encoding="utf-8",
            errors="ignore",
        )
    except FileNotFoundError as exc:
        raise MediaError(
            "FFmpeg 또는 FFprobe 실행 파일을 찾을 수 없습니다. PATH 또는 .env 설정을 확인해 주세요."
        ) from exc


def ensure_audio_stream(video_path: Path, config: AppConfig) -> None:
    cmd = [
        config.resolve_ffprobe(),
        "-v",
        "error",
        "-show_streams",
        "-select_streams",
        "a",
        "-of",
        "json",
        str(video_path),
    ]
    result = _run(cmd)
    if result.returncode != 0:
        raise MediaError("미디어 정보를 읽지 못했습니다. 손상된 파일일 수 있습니다.")

    data = json.loads(result.stdout or "{}")
    if not data.get("streams"):
        raise MediaError("영상에 음성 트랙이 없습니다. 다른 파일을 선택해 주세요.")


def extract_audio_wav(video_path: Path, out_dir: Path, config: AppConfig) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    audio_path = out_dir / f"{video_path.stem}.wav"
    cmd = [
        config.resolve_ffmpeg(),
        "-y",
        "-i",
        str(video_path),
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ac",
        "1",
        "-ar",
        "16000",
        str(audio_path),
    ]
    result = _run(cmd)
    if result.returncode != 0 or not audio_path.exists():
        raise MediaError(
            "오디오 추출에 실패했습니다. 지원하지 않는 코덱이거나 FFmpeg 설정 문제일 수 있습니다."
        )
    return audio_path
