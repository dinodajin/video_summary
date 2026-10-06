from __future__ import annotations

from pathlib import Path

from app.utils.errors import ValidationError

SUPPORTED_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}


def validate_video_file(file_path: str, max_file_mb: int) -> Path:
    path = Path(file_path)
    if not path.exists() or not path.is_file():
        raise ValidationError("파일을 찾을 수 없습니다. 경로를 확인해 주세요.")

    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValidationError(
            "지원하지 않는 형식입니다. mp4, mov, mkv, avi, webm, m4v를 권장합니다."
        )

    file_size_mb = path.stat().st_size / (1024 * 1024)
    if max_file_mb > 0 and file_size_mb > max_file_mb:
        raise ValidationError(
            f"파일이 너무 큽니다. 현재 제한은 {max_file_mb}MB 입니다."
        )

    return path
