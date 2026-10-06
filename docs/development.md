# 개발자 가이드

로컬에서 소스 실행·테스트할 때 쓰는 절차입니다. 스택 개요는 [`tech-stack.md`](tech-stack.md)를 참고하세요.

## 개발 환경

- OS: Windows 10/11
- Python: 3.10+

## 개발 실행

```powershell
$env:PYTHONPATH="src"
python -m app.main
```

## 테스트

```powershell
$env:PYTHONPATH="src"
python -m pytest tests
```

## 배포(선택)

```powershell
pip install pyinstaller
pyinstaller --noconsole --name yoyak src/app/main.py
```

관련 문서:
- 설치 가이드: [`installation.md`](installation.md)
- 설정 가이드: [`configuration.md`](configuration.md)
