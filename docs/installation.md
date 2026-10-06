# 설치 가이드 (Windows)

## 권장 실행 순서

1. 프로젝트 폴더 이동
2. Python 버전 확인/지정 (`pyenv` 사용자만)
3. 가상환경 생성/활성화
4. 패키지 설치 + `.env` 생성
5. FFmpeg 확인
6. 앱 실행

## 0) PowerShell 위치 확인

프로젝트 폴더에서 PowerShell을 열고 확인합니다.

```powershell
pwd
```

경로가 다르면 이동하세요.

```powershell
cd "<내 프로젝트 폴더 경로>\yoyak"
```

## 1) Python/가상환경/패키지 설치

`pyenv` 사용자라면:

```powershell
pyenv versions
pyenv local 3.12.10
python --version
```

`pyenv`를 쓰지 않으면 `python --version`만 확인 후 진행하면 됩니다.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

정상 활성화되면 프롬프트 앞에 `(.venv)`가 표시됩니다.

## 2) FFmpeg 설정

FFmpeg 설치 후 아래 명령이 동작해야 합니다.

```powershell
ffmpeg -version
ffprobe -version
```

PATH에서 인식되면 `.env`의 `FFMPEG_PATH`, `FFPROBE_PATH`는 비워 두는 것을 권장합니다.

필요 시 직접 지정:

```env
FFMPEG_PATH=C:\\tools\\ffmpeg\\bin\\ffmpeg.exe
FFPROBE_PATH=C:\\tools\\ffmpeg\\bin\\ffprobe.exe
```

## 3) 앱 실행

```powershell
cd "<내 프로젝트 폴더 경로>\yoyak"
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH="src"
python -m app.main
```

반복 실행은 위 4줄만 사용하면 됩니다.

다음 문서:
- 사용법: [`usage.md`](usage.md)
- 설정 가이드: [`configuration.md`](configuration.md)
