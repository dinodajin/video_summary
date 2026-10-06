# 사용법

## 기본 흐름

1. 앱 실행
2. 동영상 파일 드래그(또는 `파일 선택`)
3. `처리 시작` 클릭
4. 결과 확인
   - 전체 전사
   - (필요 시 ON) `[00:01:23] 화자1: ...` 형식 전사
5. `전사 저장` 클릭 후 형식 선택(`txt`/`md`/`json`)

## 저장 파일명

- `{원본파일명}_full_transcript.<확장자>`

## `json` 저장 시 포함 필드

- `content`: 전체 전사 문자열
- `diarization_used`: 화자 구분 사용 여부
- `segments`: `start/end/timestamp/speaker/text` 구조 배열

## 고급 설정(필요할 때만)

- `고급 설정 보기` 버튼으로 언어/Whisper 모델 옵션 변경 가능
- `화자 구분 사용` 체크박스로 ON/OFF 가능 (기본 OFF)

관련 문서:
- 설정 가이드: [`configuration.md`](configuration.md)
- 트러블슈팅: [`troubleshooting.md`](troubleshooting.md)
