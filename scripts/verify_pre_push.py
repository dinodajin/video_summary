"""
Push 전 로컬 검증: 추적 대상 .env/캐시/venv 경로 여부, 선택적 pytest.
저장소 루트에서: python scripts/verify_pre_push.py [--pytest]
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _run_git(*args: str) -> tuple[int, str]:
    p = subprocess.run(
        ["git", *args],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    out = p.stdout
    if p.stderr:
        out += f"\n{p.stderr}\n"
    return p.returncode, out.rstrip() or ""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--pytest",
        action="store_true",
        help="tests/ 에 대해 pytest 실행",
    )
    parser.add_argument(
        "--write-report",
        type=Path,
        metavar="PATH",
        help="검사 요약을 UTF-8 텍스트로 기록(에이전트/CI용)",
    )
    args = parser.parse_args()

    log_lines: list[str] = []
    bad = 0
    def out(s: str) -> None:
        print(s)
        log_lines.append(s)

    out("=== git status -sb ===")
    c, t = _run_git("status", "-sb")
    out(t)
    if c != 0:
        bad = 1

    out("=== git ls-files .env .env.local (must be empty) ===")
    c, t = _run_git("ls-files", ".env", ".env.local")
    out(t or "(no output)")
    if t.strip():
        out("ERROR: .env or .env.local is tracked. Run: git rm --cached <file>")
        print("ERROR: .env or .env.local is tracked. Run: git rm --cached <file>", file=sys.stderr)
        bad = 1

    out("=== suspicious paths in index (must be none) ===")
    c, full = _run_git("ls-files")
    pats = (
        ".venv/",
        "__pycache__/",
        ".pytest_cache/",
        ".models/",
        ".cache/",
        ".cursor/",
    )
    found = [line for line in full.splitlines() if any(p in line for p in pats)]
    if found:
        for line in found:
            out(line)
        out("ERROR: untrack with git rm -r --cached <path>")
        print("ERROR: untrack with git rm -r --cached <path>", file=sys.stderr)
        bad = 1
    else:
        out("(none)")

    out("=== git check-ignore -v .env ===")
    c, t = _run_git("check-ignore", "-v", ".env")
    if not t and REPO.joinpath(".env").is_file():
        out("WARN: .env exists but is not ignored")
        print("WARN: .env exists but is not ignored", file=sys.stderr)
        bad = 1
    else:
        out(t or "(not ignored or .env missing — check)")

    out("=== main vs origin/main (git fetch origin) ===")
    _run_git("fetch", "origin")
    c, t = _run_git("rev-list", "--left-right", "--count", "main...origin/main")
    if c == 0:
        out(t)
    else:
        out(
            f"WARN: main...origin/main 비교 생략 (git exit {c}; "
            "최초 푸시·원격 없음일 수 있음)"
        )

    if args.pytest:
        out("=== pytest ===")
        venv = REPO / ".venv" / "Scripts" / "python.exe"
        py = str(venv) if venv.is_file() else sys.executable
        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO / "src")
        p = subprocess.run(
            [py, "-m", "pytest", "tests", "-q", "--tb=short"],
            cwd=REPO,
            capture_output=True,
            text=True,
            env=env,
        )
        out(p.stdout)
        if p.stderr:
            out(p.stderr)
        if p.returncode != 0:
            bad = 1
            print("pytest failed", file=sys.stderr)

    if args.write_report:
        args.write_report.write_text(
            f"exit={bad}\n" + "\n".join(log_lines) + "\n", encoding="utf-8"
        )

    return bad


if __name__ == "__main__":
    raise SystemExit(main())
