# 트러블슈팅

## 핵심 4가지

1. **FFmpeg 인식 실패**
   - `ffmpeg -version`, `ffprobe -version` 확인
   - 실패 시 `.env`의 `FFMPEG_PATH`, `FFPROBE_PATH` 지정

2. **모델 로딩이 느림**
   - 첫 실행 시 모델 다운로드/초기화로 시간이 걸릴 수 있음
   - 잠시 기다린 뒤 재시도
   - 화자 구분 사용 시 초기 다운로드가 더 큼

3. **오디오 트랙 없음**
   - 음성 트랙이 없는 영상은 전사 불가
   - 음성 트랙이 있는 파일로 재시도

4. **파일 크기 제한 초과**
   - `.env`의 `MAX_FILE_MB`를 늘리거나 파일 크기 축소
   - 제한 해제: `MAX_FILE_MB=0`

## Windows + pyenv 자주 발생하는 오류

- `No global/local python version has been set yet`
  - `pyenv local 3.12.10` 실행 후 재시도

- `'.venv' 모듈을 로드할 수 없습니다`
  - `.\.venv\Scripts\Activate.ps1` 명령으로 활성화
  - 먼저 `python -m venv .venv` 실행 필요

- 스크립트 실행 정책 오류
  - 아래 명령 1회 실행 후 다시 활성화

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## 화자 구분 관련 이슈

- `AI_DIARIZATION_MODEL_PATH`가 없거나 pyannote 미설치면 자동 폴백
- `speaker-diarization-community-1` 미승인 시 403 폴백 가능
- `name 'AudioDecoder' is not defined` 발생 시:

```powershell
.\.venv\Scripts\Activate.ps1
pip install soundfile torchcodec
```

화자 구분 상세 절차는 [`diarization.md`](diarization.md)를 참고하세요.
