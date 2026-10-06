# yoyak

![Platform](https://img.shields.io/badge/platform-Windows%2010%2F11-0078D6)
![Python](https://img.shields.io/badge/python-3.10%2B-3776AB)
![UI](https://img.shields.io/badge/UI-PySide6-41CD52)
![STT](https://img.shields.io/badge/STT-faster--whisper-8A2BE2)
![Status](https://img.shields.io/badge/status-local%20first-success)

자율프로젝트 멘토링 내용을 빠르게 텍스트로 옮기기 위해 만든 **로컬 동영상 전사 앱**입니다.  
멘토링 영상 1개를 넣으면 오프라인으로 전사 결과를 만들고, 필요 시 **화자 구분**까지 지원합니다.

## Quick Demo

- 입력: 멘토링 영상 파일 1개
- 처리: 음성 전사 (선택: 화자 구분)
- 출력: `txt` / `md` / `json`

데모 이미지 또는 GIF를 추가하려면 아래 경로를 사용하세요.

```text
docs/assets/demo.gif
```

(`docs/assets/`는 선택 자산용입니다. [`docs/assets/README.md`](docs/assets/README.md) 참고.)

추가 후 README에 다음 형식으로 삽입하면 됩니다.

```md
![YOYAK Demo](docs/assets/demo.gif)
```

## 왜 만들었나

- 긴 멘토링 영상을 텍스트로 빠르게 복기
- 팀원 간 논의 포인트를 텍스트로 공유
- 외부 업로드 없이 로컬 환경에서 안전하게 처리

## 핵심 기능

- 영상 음성에서 **전체 전사** 생성
- 필요 시 **화자 구분 전사** 지원 (기본 OFF)
- 결과를 `txt` / `md` / `json` 형식으로 저장

## 사용 시나리오

1. 멘토링 세션 종료 후 영상 파일을 앱에 입력합니다.
2. 전사 결과로 회고 내용을 빠르게 확인합니다.
3. 저장한 `md` 또는 `txt` 파일을 팀 노션/회의록에 바로 공유합니다.

## 빠른 실행

처음 설치 전이라면 [`docs/installation.md`](docs/installation.md)부터 진행하세요.

```powershell
cd "<내 프로젝트 폴더 경로>"
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH="src"
python -m app.main
```

## 최소 요구사항

- Windows 10/11
- Python 3.10+
- FFmpeg (`ffmpeg`, `ffprobe` 명령 사용 가능)

## 프로젝트 구조

요약: `src/app/`(앱 코드), `docs/`, `scripts/`, `tests/`, `requirements.txt`.  
모듈별 역할·전사 파이프라인은 [`docs/architecture.md`](docs/architecture.md)를 정본으로 합니다.

## 기술 스택

요약 표는 [`docs/tech-stack.md`](docs/tech-stack.md)를 정본으로 합니다.

## 문서

전체 목차·주제별 링크: [`docs/index.md`](docs/index.md)  
소스 구조·처리 흐름: [`docs/architecture.md`](docs/architecture.md)
