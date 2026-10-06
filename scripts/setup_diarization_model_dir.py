from __future__ import annotations

import sys
from pathlib import Path

def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    config = _load_app_config(project_root)
    model_path = _resolve_path(project_root, config.models.diarization.path)

    model_path.mkdir(parents=True, exist_ok=True)
    print(f"[OK] 모델 폴더 준비 완료: {model_path}")
    return 0


def _load_app_config(project_root: Path):
    src_path = project_root / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
    from app.config import AppConfig

    return AppConfig.load()


def _resolve_path(project_root: Path, raw_path: str) -> Path:
    model_path = Path(raw_path).expanduser()
    if model_path.is_absolute():
        return model_path
    return (project_root / model_path).resolve()


if __name__ == "__main__":
    raise SystemExit(main())
