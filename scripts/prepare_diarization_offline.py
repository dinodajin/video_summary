from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    config = _load_app_config(project_root)
    diarization_models = config.models.diarization
    main_model_path = _resolve_path(project_root, diarization_models.path)
    pyannote_root = main_model_path.parent
    seg_model_path = pyannote_root / _repo_dir_name(diarization_models.segmentation_repo)
    emb_model_path = pyannote_root / _repo_dir_name(diarization_models.embedding_repo)
    community_model_path = pyannote_root / _repo_dir_name(diarization_models.community_repo)
    plda_model_path = community_model_path / "plda"

    hf = _resolve_hf_cli(project_root)
    if not hf:
        print("[ERROR] hf CLI를 찾지 못했습니다. 가상환경 활성화 후 다시 실행하세요.")
        return 1

    if not _is_hf_authenticated(hf):
        print("[ERROR] Hugging Face 인증이 필요합니다. 먼저 `hf auth login`을 실행하세요.")
        return 1

    main_model_path.mkdir(parents=True, exist_ok=True)
    seg_model_path.mkdir(parents=True, exist_ok=True)
    emb_model_path.mkdir(parents=True, exist_ok=True)
    community_model_path.mkdir(parents=True, exist_ok=True)

    downloads = [
        (diarization_models.main_repo, main_model_path),
        (diarization_models.segmentation_repo, seg_model_path),
        (diarization_models.embedding_repo, emb_model_path),
        (diarization_models.community_repo, community_model_path),
    ]
    for repo_id, local_dir in downloads:
        print(f"[INFO] downloading: {repo_id} -> {local_dir}")
        try:
            subprocess.run(
                [hf, "download", repo_id, "--local-dir", str(local_dir)],
                check=True,
            )
        except subprocess.CalledProcessError:
            print(
                "[ERROR] 모델 다운로드에 실패했습니다. "
                f"{repo_id} 접근 권한(게이트 승인)과 네트워크 상태를 확인하세요."
            )
            return 1

    config_path = main_model_path / "config.yaml"
    if not config_path.exists():
        print("[ERROR] speaker-diarization-3.1/config.yaml을 찾지 못했습니다.")
        return 1
    content = config_path.read_text(encoding="utf-8")
    content = _replace_model_ref(content, "segmentation", seg_model_path)
    content = _replace_model_ref(content, "embedding", emb_model_path)
    content = _replace_model_ref(content, "plda", plda_model_path)
    config_path.write_text(content, encoding="utf-8")
    print(f"[OK] config.yaml 로컬 경로 치환 완료: {config_path}")

    print("[NEXT] .\\.venv\\Scripts\\python scripts/check_diarization_model.py")
    return 0


def _resolve_path(project_root: Path, raw_path: str) -> Path:
    model_path = Path(raw_path).expanduser()
    if model_path.is_absolute():
        return model_path
    return (project_root / model_path).resolve()


def _repo_dir_name(repo_id: str) -> str:
    return repo_id.rsplit("/", maxsplit=1)[-1]


def _load_app_config(project_root: Path):
    src_path = project_root / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
    from app.config import AppConfig

    return AppConfig.load()


def _is_hf_authenticated(hf: str) -> bool:
    proc = subprocess.run([hf, "auth", "list"], capture_output=True, text=True)
    if proc.returncode != 0:
        return False
    lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    # Header line example: name | token
    token_lines = [line for line in lines if "|" in line and "token" not in line.lower()]
    if not token_lines:
        return False
    # Active token line usually starts with '*'
    return any(line.startswith("*") for line in token_lines) or len(token_lines) > 0


def _resolve_hf_cli(project_root: Path) -> str | None:
    candidates = [
        Path(sys.executable).with_name("hf.exe"),
        Path(sys.executable).with_name("hf"),
        project_root / ".venv" / "Scripts" / "hf.exe",
        project_root / ".venv" / "Scripts" / "hf",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return shutil.which("hf")


def _replace_model_ref(content: str, key: str, model_path: Path) -> str:
    replacement = f"'{model_path.as_posix()}'"
    pattern = rf"^(\s*{re.escape(key)}\s*:\s*).*$"
    updated, count = re.subn(pattern, rf"\1{replacement}", content, count=1, flags=re.M)
    if count == 0:
        # `plda` 항목이 없을 수 있어 pipeline params 섹션에 삽입
        if key == "plda":
            anchor_pattern = r"^(\s*embedding_exclude_overlap:\s*.*)$"
            injected, inserted = re.subn(
                anchor_pattern,
                rf"\1\n    plda: {replacement}",
                content,
                count=1,
                flags=re.M,
            )
            if inserted > 0:
                return injected
        raise RuntimeError(f"config.yaml에서 `{key}` 항목을 찾지 못했습니다.")
    return updated


if __name__ == "__main__":
    raise SystemExit(main())
