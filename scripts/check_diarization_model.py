from __future__ import annotations

import json
import re
import sys
from pathlib import Path

def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    config = _load_app_config(project_root)
    model_path = _resolve_path(project_root, config.models.diarization.path)

    print(f"[INFO] model_path: {model_path}")
    if not model_path.exists():
        print("[ERROR] 모델 경로가 존재하지 않습니다.")
        return 1
    if not model_path.is_dir():
        print("[ERROR] 모델 경로가 폴더가 아닙니다.")
        return 1

    yaml_candidates = ["config.yaml", "pipeline.yaml"]
    yaml_found = [name for name in yaml_candidates if (model_path / name).exists()]
    if not yaml_found:
        print("[WARN] config.yaml 또는 pipeline.yaml 을 찾지 못했습니다.")
    else:
        print(f"[OK] pipeline config 파일 확인: {', '.join(yaml_found)}")

    bin_files = list(model_path.rglob("*.bin"))
    safetensors_files = list(model_path.rglob("*.safetensors"))
    pt_files = list(model_path.rglob("*.pt"))
    ckpt_files = list(model_path.rglob("*.ckpt"))
    model_files = bin_files + safetensors_files + pt_files + ckpt_files

    remote_refs = _find_remote_model_refs(model_path)
    if not model_files:
        print("[WARN] 가중치 파일(.bin/.safetensors/.pt/.ckpt)을 찾지 못했습니다.")
    else:
        print(f"[OK] 가중치 파일 {len(model_files)}개 확인")

    local_refs = _find_local_model_refs(model_path)
    if local_refs:
        missing_local_refs = [p for p in local_refs if not p.exists()]
        if missing_local_refs:
            print("[WARN] config.yaml의 로컬 하위 모델 경로 중 일부가 없습니다.")
            for item in missing_local_refs:
                print(f"  - {item}")
        else:
            print("[OK] config.yaml의 로컬 하위 모델 경로 확인 완료")
    else:
        missing_local_refs = []

    report = {
        "model_path": str(model_path),
        "exists": model_path.exists(),
        "is_dir": model_path.is_dir(),
        "pipeline_config_found": yaml_found,
        "weights_count": len(model_files),
        "remote_model_refs": remote_refs,
        "local_model_refs": [str(p) for p in local_refs],
    }
    print("[INFO] check_result:")
    print(json.dumps(report, ensure_ascii=False, indent=2))

    if not yaml_found:
        print("[RESULT] 모델 구조가 불완전할 수 있습니다. 경로/파일 구성을 다시 확인하세요.")
        return 2
    if remote_refs:
        print("[RESULT] 허브 원격 참조가 남아 있습니다. scripts/prepare_diarization_offline.py를 실행하세요.")
        return 2
    if missing_local_refs:
        print("[RESULT] 로컬 하위 모델 경로가 누락되었습니다. scripts/prepare_diarization_offline.py를 다시 실행하세요.")
        return 2
    if not model_files and not local_refs:
        print("[RESULT] 모델 구조가 불완전할 수 있습니다. 경로/파일 구성을 다시 확인하세요.")
        return 2

    print("[RESULT] 모델 경로 점검 통과")
    return 0


def _find_remote_model_refs(model_path: Path) -> list[str]:
    config_file = model_path / "config.yaml"
    if not config_file.exists():
        return []
    content = config_file.read_text(encoding="utf-8", errors="ignore")
    refs = re.findall(r":\s*([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)\s*$", content, flags=re.M)
    out: list[str] = []
    for ref in refs:
        if ref not in out:
            out.append(ref)
    return out


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


def _find_local_model_refs(model_path: Path) -> list[Path]:
    config_file = model_path / "config.yaml"
    if not config_file.exists():
        return []
    content = config_file.read_text(encoding="utf-8", errors="ignore")
    candidates = re.findall(
        r"^\s*(embedding|segmentation|plda)\s*:\s*['\"]?([^'\"\n]+)['\"]?\s*$",
        content,
        flags=re.M,
    )
    paths: list[Path] = []
    for _, raw in candidates:
        value = raw.strip()
        if "/" not in value and "\\" not in value:
            continue
        if re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", value):
            # Hugging Face repo id (remote ref)
            continue
        ref_path = Path(value).expanduser()
        if not ref_path.is_absolute():
            project_root = Path(__file__).resolve().parents[1]
            ref_path = (project_root / ref_path).resolve()
        paths.append(ref_path)
    return paths


if __name__ == "__main__":
    raise SystemExit(main())
