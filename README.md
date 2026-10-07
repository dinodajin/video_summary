# YOYAK 설치 및 사용 가이드

> 멘토링 영상을 **로컬에서 STT로 전사**하고, 전사 내용을 **로컬 LLM(Ollama)으로 요약**하여 SSAFY 일일/주차별 보고서 형식으로 정리하는 Windows용 프로그램

---

## 0. 이 프로그램으로 할 수 있는 것

```text
멘토링 영상
   ↓
FFmpeg로 음성 추출
   ↓
faster-whisper로 STT 전사
   ↓
Ollama + Qwen3로 보고서 요약
   ↓
일일 프로젝트 보고서 + 주차별 기업연계 멘토링 보고서
   ↓
DOCX / XLSX 양식에 반영
```

현재 권장 사용 방식은 **화자 구분을 사용하지 않고** `STT → 보고서 요약`만 사용하는 방식입니다.

### 생성되는 보고서

#### 일일 프로젝트 진행 보고서
- `내용`: 핵심 진행사항 2~5개
- `종합`: 현재 진행 상태를 한 문장으로 요약

#### 주차별 기업연계 멘토링 진행현황
- 프로젝트 전체 진행사항 및 수준
- 기본요구사항
- 기본요구사항에 대한 개발진척도
- 추가개발사항
- 추가개발사항에 대한 개발진척도
- 이슈사항

두 보고서 모두 `~함.`, `~임.`, `~중임.`, `~예정임.` 형태의 보고체로 작성됩니다.

> [!IMPORTANT]
> 현재 보고서 자동 반영 기능은 **서울 5반 A501~A509** 기준으로 구현되어 있습니다.  
> 다른 반에서 사용할 경우 팀 코드와 보고서 양식 매핑 부분을 수정해야 합니다.

---

# 1. 준비물

## 필수 환경

- Windows 10 또는 Windows 11
- Python **3.11 권장**
- FFmpeg
- Ollama
- 인터넷 연결
  - 최초 Python 패키지 설치
  - 최초 Whisper 모델 다운로드
  - 최초 Qwen 모델 다운로드 시 필요

처음 설치할 때는 AI 모델과 Python 패키지를 내려받기 때문에 시간이 걸릴 수 있습니다.

---

# 2. Python 3.11 설치

PowerShell을 열고 먼저 설치된 Python 버전을 확인합니다.

```powershell
py -0p
```

Python 3.11이 없다면 다음 중 하나의 방법으로 설치합니다.

### 방법 A. Python Launcher 사용

```powershell
py install 3.11
```

### 방법 B. winget 사용

```powershell
winget install Python.Python.3.11
```

설치 후 확인합니다.

```powershell
py -3.11 --version
```

정상 예시:

```text
Python 3.11.x
```

> Python 3.14처럼 너무 최신 버전은 일부 AI 패키지와 호환 문제가 발생할 수 있으므로 Python 3.11 사용을 권장합니다.

---

# 3. FFmpeg 설치

YOYAK은 동영상에서 음성을 추출할 때 FFmpeg를 사용합니다.

PowerShell에서 실행합니다.

```powershell
winget install Gyan.FFmpeg
```

설치가 끝나면 **VS Code와 PowerShell을 완전히 종료한 뒤 다시 실행**하는 것을 권장합니다.

설치 확인:

```powershell
ffmpeg -version
ffprobe -version
```

두 명령 모두 버전 정보가 출력되면 정상입니다.

---

# 4. Ollama 설치

Ollama는 전사된 멘토링 내용을 로컬 AI로 요약하는 데 사용합니다.

```powershell
winget install Ollama.Ollama
```

설치 후 VS Code 또는 PowerShell을 다시 실행하고 확인합니다.

```powershell
ollama --version
```

정상 예시:

```text
ollama version is 0.xx.x
```

---

# 5. 보고서 요약 모델 설치

현재 권장 모델은 `qwen3:4b-instruct`입니다.

```powershell
ollama pull qwen3:4b-instruct
```

다운로드가 끝나면 확인합니다.

```powershell
ollama list
```

아래와 같이 모델이 표시되면 정상입니다.

```text
NAME                 SIZE
qwen3:4b-instruct    약 2.5 GB
```

간단한 실행 테스트도 가능합니다.

```powershell
ollama run qwen3:4b-instruct "안녕하세요. 정상 작동하는지 확인해 주세요."
```

답변이 생성되면 Ollama 준비가 끝난 것입니다.

---

# 6. YOYAK 프로젝트 설치

프로젝트를 Git으로 받은 경우 저장소를 clone하고 해당 폴더로 이동합니다.

```powershell
git clone <저장소 주소>
cd <YOYAK 프로젝트 폴더>
```

ZIP으로 받은 경우 압축을 푼 뒤, VS Code에서 해당 프로젝트 폴더를 열면 됩니다.

## 6-1. 가상환경 생성

프로젝트 최상위 폴더에서 실행합니다.

```powershell
py -3.11 -m venv .venv
```

## 6-2. 가상환경 활성화

```powershell
.\.venv\Scripts\Activate.ps1
```

정상적으로 활성화되면 터미널 앞에 `(.venv)`가 표시됩니다.

```text
(.venv) PS C:\...\video_summary>
```

### `이 시스템에서 스크립트를 실행할 수 없습니다` 오류가 발생하는 경우

현재 PowerShell 창에서만 실행 정책을 임시로 허용합니다.

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

이 설정은 현재 PowerShell 프로세스에만 적용됩니다.

## 6-3. Python 패키지 설치

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

처음 설치할 때는 AI 관련 패키지 때문에 시간이 걸릴 수 있습니다.

> 현재 `requirements.txt`에는 기존 화자 구분 관련 패키지도 포함되어 있어 설치 용량과 시간이 다소 클 수 있습니다. 실제 권장 사용에서는 화자 구분을 OFF로 사용합니다.

---

# 7. 프로그램 실행

가상환경이 활성화된 상태에서 실행합니다.

```powershell
$env:PYTHONPATH="src"
python -m app.main
```

YOYAK GUI 창이 나타나면 정상입니다.

---

# 8. 권장 설정

처음 실행한 경우 아래 설정을 권장합니다.

| 항목 | 권장값 |
|---|---|
| 전사 언어 | 한국어 |
| Whisper 모델 | `small` |
| 화자 구분 사용 | **OFF** |
| 요약 엔진 | Ollama |
| 요약 모델 | `qwen3:4b-instruct` |
| 요약 API 주소 | `http://localhost:11434` |
| API Key | 비워둠 |

### 왜 화자 구분은 OFF인가요?

화자 구분은 처리 시간이 크게 늘어나며, 현재 보고서 작성 목적에는 필수적이지 않습니다.  
따라서 기본 사용 흐름에서는 **STT 전체 전사본을 바로 보고서 요약에 사용**합니다.

이 경우 Hugging Face Token도 필요하지 않습니다.

---

# 9. 기본 사용 방법

## 9-1. 영상 전사하기

1. `파일 선택` 클릭
2. 멘토링 영상 선택
3. `처리 시작` 클릭
4. STT 전사가 완료될 때까지 기다림
5. 전사 결과 확인

처음 Whisper 모델을 사용하는 경우 모델 파일을 자동으로 다운로드하기 때문에 평소보다 오래 걸릴 수 있습니다.

### 진행률이 55%에서 오래 멈춰 보이는 경우

현재 진행률은 영상 전체의 정확한 퍼센트가 아니라 **처리 단계 표시**에 가깝습니다.

따라서 `전사 중... 55%` 상태에서 Whisper가 실제 음성을 계속 처리하고 있을 수 있습니다.

---

# 10. 보고서 요약 생성

전사가 완료되면:

1. `보고서 요약 생성` 클릭
2. 해당 팀 코드 선택
   - A501
   - A502
   - ...
   - A509
3. Ollama가 전사 내용을 분석함
4. 아래 두 결과를 확인함
   - 일일 팀 보고서
   - 주차별 기업연계 멘토링 진행현황
5. 필요한 경우 GUI에서 문장을 직접 수정함

AI가 생성한 결과는 반드시 한 번 확인하는 것을 권장합니다.

특히 아래 항목을 확인합니다.

- 실제 멘토링에서 언급되지 않은 내용이 추가되지 않았는지
- 목표 수치와 실제 달성 수치가 혼동되지 않았는지
- `논의함`과 `구현 완료함`이 잘못 구분되지 않았는지
- 기업 멘토의 요구사항과 교육생의 제안이 혼동되지 않았는지

---

# 11. 여러 팀을 한 번에 보고서에 반영하기

YOYAK은 같은 실행 세션에서 팀별 보고서를 누적할 수 있습니다.

예시:

```text
A501 영상 → 전사 → 보고서 요약
A502 영상 → 전사 → 보고서 요약
A503 영상 → 전사 → 보고서 요약
A504 영상 → 전사 → 보고서 요약
...
A509 영상 → 전사 → 보고서 요약
                 ↓
          마지막에 한 번만 반영
```

화면에 아래처럼 누적 상태가 표시됩니다.

```text
누적 팀 (4): A501, A502, A503, A504
```

모든 팀의 요약이 끝난 뒤:

- `일일 DOCX 반영`
- `주간 XLSX 반영`

버튼을 한 번씩 누르면 누적된 팀을 한꺼번에 반영할 수 있습니다.

### 같은 팀을 다시 요약하면?

같은 팀 코드를 다시 선택해 요약하면 해당 팀의 기존 결과를 최신 결과로 덮어씁니다.

> [!WARNING]
> 누적된 팀 보고서는 현재 **프로그램을 실행 중인 동안만 유지**됩니다.  
> 프로그램을 종료하기 전에 DOCX/XLSX로 반영하거나 결과를 별도로 저장하는 것을 권장합니다.

---

# 12. 전사를 다시 하지 않고 보고서만 재생성하기

보고서 문체나 요약 결과만 다시 만들고 싶은 경우 긴 영상을 다시 전사할 필요가 없습니다.

먼저 전사 완료 후 `TXT/JSON 저장`으로 전사본을 저장합니다.

다음 실행부터는:

1. `전사본 불러오기` 클릭
2. 기존 `.txt`, `.md`, `.json` 전사본 선택
3. `보고서 요약 생성` 클릭
4. 팀 코드 선택

이렇게 하면 STT 단계를 건너뛰고 바로 보고서를 다시 생성할 수 있습니다.

---

# 13. 일일 DOCX 반영 방법

1. 팀별 보고서 요약을 필요한 만큼 누적함
2. `일일 DOCX 반영` 클릭
3. 기존 일일 프로젝트 진행 `.docx` 템플릿 선택
4. 저장할 새 파일 이름 선택
5. 누적된 팀의 `내용` / `종합`이 자동 반영됨

원본 템플릿은 직접 덮어쓰지 않고 새 파일로 저장합니다.

### 현재 지원하는 형식

서울 5반 기준 A501~A509의 각 팀에 아래 항목이 존재해야 합니다.

```text
팀코드
 ├─ 내용
 └─ 종합
```

문서 구조가 다르면 자동 반영되지 않을 수 있습니다.

---

# 14. 주차별 XLSX 반영 방법

1. 팀별 보고서 요약을 필요한 만큼 누적함
2. `주간 XLSX 반영` 클릭
3. `15기_기업연계_멘토링 진행현황.xlsx` 형식의 템플릿 선택
4. 반영할 주차 선택
   - `1주차 진행현황`
   - `2주차 진행현황`
   - ...
5. 새 파일로 저장

현재 서울 5반 팀의 아래 항목을 작성합니다.

```text
프로젝트 전체 진행사항 및 수준
기본요구사항
기본요구사항에 대한 개발진척도
추가개발사항
추가개발사항에 대한 개발진척도
이슈사항
```

주차별 보고서는 일일 보고서보다 구체적으로 작성됩니다.

---

# 15. 결과 저장

`TXT/JSON 저장` 기능을 사용하면 전사본과 보고서 결과를 별도로 보관할 수 있습니다.

전사본을 저장해 두면 이후 AI 요약 결과를 수정하고 싶을 때 영상을 다시 처리하지 않아도 됩니다.

장시간 영상은 전사 비용이 크므로 **전사 완료 후 저장을 권장**합니다.

---

# 16. 자주 발생하는 문제

## 16-1. `Activate.ps1` 실행이 차단됨

오류 예시:

```text
이 시스템에서 스크립트를 실행할 수 없으므로 ... Activate.ps1 파일을 로드할 수 없습니다.
```

해결:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

---

## 16-2. `ffmpeg`를 찾을 수 없음

확인:

```powershell
ffmpeg -version
ffprobe -version
```

명령이 인식되지 않으면:

```powershell
winget install Gyan.FFmpeg
```

설치 후 VS Code를 다시 실행합니다.

---

## 16-3. `ollama` 명령을 찾을 수 없음

설치 직후 기존 VS Code 터미널에서는 PATH가 갱신되지 않을 수 있습니다.

1. VS Code 완전 종료
2. 다시 실행
3. 확인

```powershell
ollama --version
```

그래도 안 되면:

```powershell
& "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" --version
```

---

## 16-4. `qwen3:4b-instruct` 모델이 없음

확인:

```powershell
ollama list
```

목록에 없다면:

```powershell
ollama pull qwen3:4b-instruct
```

---

## 16-5. 보고서 요약 시 Ollama 연결 오류

먼저 Ollama가 정상인지 확인합니다.

```powershell
ollama list
```

필요하면 Ollama 서버를 직접 실행합니다.

```powershell
ollama serve
```

YOYAK의 요약 API 주소가 아래인지 확인합니다.

```text
http://localhost:11434
```

---

## 16-6. STT가 너무 오래 걸림

권장 설정:

```text
Whisper 모델: small
화자 구분: OFF
```

GPU가 있는 PC에서는 아래 명령으로 상태를 확인할 수 있습니다.

```powershell
nvidia-smi
```

영상 길이와 PC 사양에 따라 전사 시간이 크게 달라질 수 있습니다.

---

## 16-7. 처음 실행할 때 특히 오래 걸림

최초 실행 시 Whisper 모델이 다운로드될 수 있습니다.

모델 다운로드가 끝나면 이후 실행에서는 캐시된 모델을 사용하므로 일반적으로 더 빨라집니다.

---

## 16-8. DOCX/XLSX에 일부 팀이 반영되지 않음

다음을 확인합니다.

- 팀 코드가 A501~A509인지
- 해당 팀의 보고서 요약을 먼저 생성했는지
- 화면의 `누적 팀` 목록에 팀이 표시되는지
- DOCX/XLSX 템플릿 구조가 기존 양식과 동일한지
- 주간 XLSX에서 올바른 `n주차 진행현황` 시트를 선택했는지

---

# 17. 개인정보 및 데이터 처리

권장 설정인 `Whisper + Ollama` 조합에서는 영상 전사와 보고서 요약이 로컬 PC에서 수행됩니다.

```text
영상 → 로컬 FFmpeg → 로컬 Whisper → 로컬 Ollama
```

영상이나 전사 내용을 OpenAI 등의 외부 LLM API로 보내지 않습니다.

다만 최초 설치 시 AI 모델 파일 자체는 인터넷에서 다운로드합니다.

> OpenAI 호환 API 설정으로 변경하는 경우에는 전사 내용이 해당 외부 API로 전송될 수 있으므로 내부 자료 사용 시 반드시 보안 정책을 확인해야 합니다.

---

# 18. 프로젝트를 다른 사람에게 공유할 때

Git 저장소 또는 ZIP으로 공유할 때 아래 파일은 함께 공유하는 것을 권장합니다.

```text
src/
requirements.txt
README.md
docs/
.env.example
```

다음 항목은 공유하지 않는 것을 권장합니다.

```text
.venv/          # 개인 PC의 Python 가상환경
.models/        # 로컬 AI 모델
.env            # API Key / Token이 들어갈 수 있음
__pycache__/
개인 영상 파일
실제 교육생 정보가 포함된 결과 보고서
```

`.gitignore`에 위 항목들이 포함되어 있는지 확인한 뒤 push하는 것을 권장합니다.

---

# 19. 처음 설치하는 사람용 초간단 체크리스트

아래 순서대로 진행하면 됩니다.

### ① Python 3.11

```powershell
py install 3.11
```

### ② FFmpeg

```powershell
winget install Gyan.FFmpeg
```

### ③ Ollama

```powershell
winget install Ollama.Ollama
```

### ④ VS Code 재실행 후 Qwen 설치

```powershell
ollama pull qwen3:4b-instruct
```

### ⑤ 프로젝트 가상환경 생성

```powershell
py -3.11 -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### ⑥ 실행

```powershell
$env:PYTHONPATH="src"
python -m app.main
```

### ⑦ 프로그램 설정

```text
Whisper 모델: small
화자 구분: OFF
요약 엔진: Ollama
요약 모델: qwen3:4b-instruct
API 주소: http://localhost:11434
```

### ⑧ 사용

```text
영상 선택
→ 처리 시작
→ 전사 완료
→ 보고서 요약 생성
→ 팀 코드 선택
→ 결과 검토
→ 여러 팀 반복
→ 마지막에 DOCX/XLSX 일괄 반영
```

---

# 20. 한 줄 요약

처음 한 번만 `Python 3.11 + FFmpeg + Ollama + Qwen3`를 설치하면, 이후에는 **영상 선택 → STT 전사 → 보고서 요약 → 여러 팀 누적 → DOCX/XLSX 일괄 반영** 순서로 사용하면 됩니다.
