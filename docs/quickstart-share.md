# YOYAK 공유용 빠른 시작 가이드 (Windows)

이 문서는 프로젝트 소유자가 팀원/지인에게 `YOYAK`를 공유할 때 사용하는 최소 가이드입니다.

## 1) 공유하는 사람(소유자) 체크리스트

- 저장소에는 `.env` 대신 `.env.example`만 포함하세요.
- `.venv`, `.models`는 업로드하지 마세요.
- 커밋 전 `git status`로 민감/대용량 파일 포함 여부를 확인하세요.

권장 공유 대상:
- 소스 코드 (`src/`, `scripts/`)
- 문서 (`README.md`, `docs/*`)
- 의존성 파일 (`requirements.txt`)
- 설정 템플릿 (`.env.example`)

## 2) 받는 사람(사용자) 설치 방법

프로젝트 폴더에서 아래 순서대로 실행:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

FFmpeg 확인:

```powershell
ffmpeg -version
ffprobe -version
```

앱 실행:

```powershell
$env:PYTHONPATH="src"
python -m app.main
```

## 3) 자주 발생하는 문제

FFmpeg 인식, PowerShell 실행 정책, 화자 구분 등 전체 대응은 [`troubleshooting.md`](troubleshooting.md)를 참고하세요.
