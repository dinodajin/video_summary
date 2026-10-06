# 삭제/초기화 가이드

목적에 따라 필요한 범위만 수행하세요.

## A) 앱만 중지하고 프로젝트 유지

1. 실행 중인 앱 창 종료
2. 프로젝트 파일은 유지

## B) Python 가상환경/패키지만 삭제

```powershell
deactivate
Remove-Item -Recurse -Force ".\.venv"
```

복구:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## C) 화자 구분 관련 리소스만 삭제

`.env` 비활성:

```env
DIARIZATION_ENABLED=false
AI_DIARIZATION_MODEL_PATH=
```

패키지 제거(선택):

```powershell
.\.venv\Scripts\Activate.ps1
pip uninstall -y pyannote.audio
```

모델 캐시 삭제(선택):

```powershell
Remove-Item -Recurse -Force "$env:USERPROFILE\.cache\huggingface\hub\models--pyannote--speaker-diarization-3.1"
```

## D) Hugging Face 캐시 전체 삭제

주의: 모든 HF 모델/데이터셋 캐시가 삭제됩니다.

```powershell
Remove-Item -Recurse -Force "$env:USERPROFILE\.cache\huggingface"
```

## E) 프로젝트 완전 삭제

중요 파일 백업 후 실행:

```powershell
cd "<내 프로젝트 상위 폴더 경로>"
Remove-Item -Recurse -Force ".\yoyak"
```

관련 문서:
- 설치 가이드: [`installation.md`](installation.md)
- 공유용 빠른 시작: [`quickstart-share.md`](quickstart-share.md)
