# 기술 스택

로컬 동영상 전사·선택적 화자 구분에 쓰는 구성 요소입니다. 버전은 `requirements.txt`와 로컬 가상환경을 기준으로 합니다.

| 영역 | 기술 | 비고 |
|------|------|------|
| 런타임 | Python 3.10+ | Windows 10/11 권장 |
| UI | PySide6 | 데스크톱 창 |
| STT | faster-whisper | Whisper 백엔드 |
| 화자 구분(선택) | pyannote.audio, torch | `.env`로 켜고 끔 |
| 설정 | python-dotenv | `.env` 로드 |
| 미디어 | FFmpeg / ffprobe | PATH 또는 `FFMPEG_PATH` 등 |

관련: [설치](installation.md), [개발](development.md), [루트 README](../README.md).
