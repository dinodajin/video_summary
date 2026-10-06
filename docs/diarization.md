# 화자 구분(기본 OFF) 운영 가이드

현재 운영/배포 기본값은 화자 구분 OFF입니다. 필요한 경우에만 활성화하세요.

## A-0) Hugging Face 직접 사용(빠른 시작)

```powershell
.\.venv\Scripts\Activate.ps1
pip install pyannote.audio soundfile
```

`.env` 설정:

```env
DIARIZATION_ENABLED=true
DIARIZATION_PROVIDER=pyannote
DIARIZATION_SOURCE=huggingface
HF_TOKEN=hf_xxx
AI_DIARIZATION_REPO_MAIN=pyannote/speaker-diarization-3.1
```

필수:
- Hugging Face에서 `pyannote/speaker-diarization-3.1` 접근 승인
- 필요하면 `DIARIZATION_MIN_SPEAKERS`, `DIARIZATION_MAX_SPEAKERS`로 화자 수 범위 지정

## A-1) 활성화 최소 절차

```powershell
.\.venv\Scripts\Activate.ps1
pip install pyannote.audio soundfile
.\.venv\Scripts\python scripts/setup_diarization_model_dir.py
.\.venv\Scripts\python scripts/prepare_diarization_offline.py
.\.venv\Scripts\python scripts/check_diarization_model.py
```

`.env` 설정:

```env
DIARIZATION_ENABLED=true
DIARIZATION_PROVIDER=pyannote
AI_DIARIZATION_MODEL_PATH=.models/pyannote/speaker-diarization-3.1
```

## A-2) 403 권한 오류 대응

아래 4개 모델의 게이트 승인을 확인하세요.
- `pyannote/speaker-diarization-3.1`
- `pyannote/segmentation-3.0`
- `pyannote/wespeaker-voxceleb-resnet34-LM`
- `pyannote/speaker-diarization-community-1`

승인 후 재실행:

```powershell
.\.venv\Scripts\python scripts/prepare_diarization_offline.py
.\.venv\Scripts\python scripts/check_diarization_model.py
```

## A-3) 팀 공유(리더)

```powershell
.\.venv\Scripts\python scripts/check_diarization_model.py
Compress-Archive -Path ".models/pyannote/*" -DestinationPath "pyannote-offline-models.zip" -Force
```

공유 파일:
- `pyannote-offline-models.zip`
- 저장소 코드
- `.env.example`

## A-4) 비활성/삭제

비활성:

```env
DIARIZATION_ENABLED=false
AI_DIARIZATION_MODEL_PATH=
```

선택 삭제:

```powershell
.\.venv\Scripts\Activate.ps1
pip uninstall -y pyannote.audio
Remove-Item -Recurse -Force "$env:USERPROFILE\.cache\huggingface\hub\models--pyannote--speaker-diarization-3.1"
```

관련 문서:
- 설정 가이드: [`configuration.md`](configuration.md)
- 트러블슈팅: [`troubleshooting.md`](troubleshooting.md)
