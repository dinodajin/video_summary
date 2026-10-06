# 설정 가이드 (`.env`)

## 권장 `.env` 예시

루트의 [`.env.example`](../.env.example)과 동일한 키를 사용합니다.

## 핵심 항목 설명

- `MAX_FILE_MB`: 입력 파일 크기 제한(MB). 1시간 영상 기준 `8192`~`16384` 권장, 제한 해제는 `0`.
- `AI_WHISPER_DEVICE`: STT 디바이스 선택 (`auto`/`cpu`/`cuda`).
- `AI_WHISPER_COMPUTE_TYPE`: faster-whisper 계산 타입 (`auto`, `int8`, `float16` 등).
- `DIARIZATION_ENABLED`: 화자 구분 ON/OFF (`false` 권장 기본값).
- `DIARIZATION_SOURCE`: `auto`(기본) / `local` / `huggingface`.
- `DIARIZATION_HF_TOKEN`: Hugging Face 토큰. 비워두면 `HF_TOKEN` 환경변수를 사용.
- `AI_DIARIZATION_MODEL_PATH`: 오프라인 pyannote 모델 경로(`DIARIZATION_SOURCE=local`에서 사용).
- `DIARIZATION_REFINE_WORD_LEVEL`: `true`(기본)이면 화자 구분이 **성공한 경우에만** faster-whisper **단어 타임스탬프**를 켜고, 다이어리제이션과 맞춰 **한 STT 구간 안의 화자 교차**를 나눕니다.
- `DIARIZATION_SMOOTH_SHORT_SPIKE_SEC`: `build_transcript` 단계에서 아주 짧은 화자 전환(A-B-A)을 한 화자로 합칠 때의 **최대 길이(초)**. 기본 `1.0`. **짧은 끼어들기까지 살리려면** `0`에 가깝게 두세요.
- `DIARIZATION_CLUSTERING_THRESHOLD`: pyannote **클러스터링 threshold**를 직접 지정(예: `0.65`). 비우면 모델 `config.yaml` 기본값을 씁니다.

## FFmpeg 경로 설정 원칙

- 기본: PATH에 `ffmpeg`, `ffprobe`가 있으면 `FFMPEG_PATH`, `FFPROBE_PATH`는 빈 값 유지.
- 예외: PATH 인식 문제 시에만 절대 경로 지정.

## 화자 구분 관련 빠른 메모

- 일반 사용은 `DIARIZATION_ENABLED=false` 유지.
- Hugging Face로 바로 쓰려면 `DIARIZATION_SOURCE=huggingface` + `HF_TOKEN` 설정.
- 화자 구분 운영 절차는 [`diarization.md`](diarization.md) 참고.

### 데스크톱 앱: 멘토 화자 지정(텍스트만)

- 화자 구분으로 처리한 뒤 **멘토 지정…**을 누르면 화자별 **짧은 인용 샘플**과 통계가 표시되고, 멘토에 해당하는 `화자N`을 고를 수 있습니다. 나머지는 기본 `교육생` 라벨로 묶는 옵션을 끄면 원래 `화자N` 표기를 유지합니다.
- 샘플 길이·개수 등은 코드 상수 [`SPEAKER_PREVIEW_MIN_CHARS`](../src/app/constants.py), [`SPEAKER_PREVIEW_MAX_QUOTES`](../src/app/constants.py) 등을 참고하세요(환경 변수 없음). 인용은 시간축을 고르게 뽑도록 여러 개를 보여 주며, 화자별 **한 줄 요약**은 글자 비중·질문 비율 등 **통계 휴리스틱**입니다(LLM 아님).
- JSON으로 전사를 저장할 때 `speaker_role_mapping` 필드에 원본 화자명→표시 역할 맵이 포함될 수 있습니다.

관련: [기술 스택](tech-stack.md) · 다음: [트러블슈팅](troubleshooting.md)
