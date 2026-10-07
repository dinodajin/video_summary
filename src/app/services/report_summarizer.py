from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any
from urllib import error, request

from app.config import AppConfig


@dataclass(slots=True)
class TeamReport:
    team_code: str
    content: list[str]
    summary: str

    def render(self) -> str:
        lines = ["[내용]"]
        lines.extend(f"• {item}" for item in self.content)
        lines.append("")
        lines.append("[종합]")
        lines.append(f"• {self.summary}")
        return "\n".join(lines)


class ReportSummarizer:
    """전사본을 SSAFY 일일 프로젝트 보고서의 `내용/종합` 형태로 요약한다."""

    def __init__(self, config: AppConfig):
        self._config = config

    def summarize(self, transcript: str, team_code: str = "") -> TeamReport:
        transcript = transcript.strip()
        if not transcript:
            raise RuntimeError("요약할 전사 내용이 없습니다.")

        # 긴 회의는 먼저 사실만 압축하고, 최종 보고서를 다시 생성한다.
        chunk_size = max(8_000, int(self._config.summary_chunk_chars))
        if len(transcript) <= chunk_size:
            payload = self._request_report(transcript, team_code)
        else:
            facts: list[str] = []
            chunks = [
                transcript[i : i + chunk_size]
                for i in range(0, len(transcript), chunk_size)
            ]
            for idx, chunk in enumerate(chunks, start=1):
                facts.extend(self._request_facts(chunk, idx, len(chunks)))
            compact = "\n".join(f"- {fact}" for fact in facts)
            payload = self._request_report(compact, team_code, facts_only=True)

        content = payload.get("content")
        summary = str(payload.get("summary", "")).strip()
        if not isinstance(content, list):
            raise RuntimeError("요약 모델 응답에서 content 목록을 찾지 못했습니다.")
        content = [str(item).strip() for item in content if str(item).strip()]
        if not content or not summary:
            raise RuntimeError("요약 모델이 비어 있는 보고서를 반환했습니다.")

        return TeamReport(
            team_code=team_code.strip(),
            content=content[:5],
            summary=summary,
        )

    def _request_report(
        self,
        source: str,
        team_code: str,
        *,
        facts_only: bool = False,
    ) -> dict[str, Any]:
        source_label = "전사본에서 추출한 사실 목록" if facts_only else "프로젝트 코칭 대화 전사본"
        team_line = f"팀 코드: {team_code.strip()}\n" if team_code.strip() else ""
        system = (
            "당신은 SSAFY 실습코치의 일일 프로젝트 진행 보고서를 작성하는 보조자다. "
            "입력에 실제로 존재하는 사실만 사용하고, 추측·과장·새로운 기술명·성과를 만들지 않는다. "
            "자기소개, 인사, 감사 표현, 잡담은 프로젝트 진행상황과 직접 관련이 없으면 제외한다."
        )
        user = f"""{team_line}아래 {source_label}을 바탕으로 팀 보고서를 작성하라.

[작성 기준]
- content: 현재 진행 상황, 완료 작업, 요구사항/설계 논의, 문제·리스크, 멘토 피드백, 결정사항, 다음 액션 중 의미 있는 내용 2~5개
- summary: 팀의 현재 상태와 핵심 진행 방향을 한 문장으로 정리
- 반복 내용은 합친다.
- 불확실한 내용은 단정하지 말고 제외한다.
- 보고서 문체를 사용한다. 가능하면 '~함', '~중', '~예정' 형태로 간결하게 쓴다.
- 사람 이름과 사적인 대화는 핵심 진행 내용이 아니면 넣지 않는다.
- 숫자/일정/목표치는 입력에 명시된 경우에만 사용한다.

반드시 아래 JSON 형식만 반환하라.
{{
  "content": ["내용 1", "내용 2"],
  "summary": "한 문장 종합"
}}

[{source_label}]
{source}
"""
        return self._chat_json(system, user)

    def _request_facts(self, chunk: str, index: int, total: int) -> list[str]:
        system = (
            "프로젝트 코칭 대화에서 보고서 작성에 필요한 사실만 추출한다. "
            "추측하지 말고 실제 대화에 나온 내용만 사용한다."
        )
        user = f"""전체 전사 {total}개 조각 중 {index}번째다.
자기소개·인사·잡담은 제외하고 다음에 해당하는 사실만 추출하라:
진행상황, 요구사항, 구현/설계 방향, 기술적 제약, 멘토 피드백, 결정사항, 수치 목표, 일정, 다음 액션.

반드시 JSON만 반환하라.
{{"facts": ["사실 1", "사실 2"]}}

[전사]
{chunk}
"""
        payload = self._chat_json(system, user)
        facts = payload.get("facts", [])
        if not isinstance(facts, list):
            return []
        return [str(f).strip() for f in facts if str(f).strip()]

    def _chat_json(self, system: str, user: str) -> dict[str, Any]:
        provider = self._config.summary_provider.strip().lower()
        if provider == "ollama":
            return self._ollama_chat(system, user)
        if provider in {"openai", "openai_compatible"}:
            return self._openai_compatible_chat(system, user)
        raise RuntimeError("요약 엔진은 ollama 또는 openai 중 하나여야 합니다.")

    def _ollama_chat(self, system: str, user: str) -> dict[str, Any]:
        model = self._config.summary_model.strip()
        if not model:
            raise RuntimeError("Ollama 요약 모델명이 비어 있습니다.")
        base = self._config.summary_base_url.rstrip("/")
        url = f"{base}/api/chat"
        body = {
            "model": model,
            "stream": False,
            "format": "json",
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "options": {"temperature": 0.1, "num_ctx": 8192, "num_predict": 3072},
        }
        payload = self._post_json(url, body, headers={})
        try:
            content = payload["message"]["content"]
        except Exception as exc:
            raise RuntimeError("Ollama 응답 형식을 해석하지 못했습니다.") from exc
        return _parse_json_object(str(content))

    def _openai_compatible_chat(self, system: str, user: str) -> dict[str, Any]:
        model = self._config.summary_model.strip()
        if not model:
            raise RuntimeError("요약 모델명이 비어 있습니다.")
        api_key = self._config.summary_api_key.strip()
        if not api_key:
            raise RuntimeError("OpenAI 호환 API 사용 시 API Key가 필요합니다.")
        base = self._config.summary_base_url.rstrip("/")
        url = f"{base}/chat/completions"
        body = {
            "model": model,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        headers = {"Authorization": f"Bearer {api_key}"}
        payload = self._post_json(url, body, headers=headers)
        try:
            content = payload["choices"][0]["message"]["content"]
        except Exception as exc:
            raise RuntimeError("OpenAI 호환 API 응답 형식을 해석하지 못했습니다.") from exc
        return _parse_json_object(str(content))

    def _post_json(self, url: str, body: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
        raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
        req = request.Request(
            url,
            data=raw,
            method="POST",
            headers={"Content-Type": "application/json", **headers},
        )
        try:
            with request.urlopen(req, timeout=float(self._config.summary_timeout_sec)) as resp:
                text = resp.read().decode("utf-8")
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"요약 API 요청 실패 ({exc.code}): {detail[:500]}") from exc
        except error.URLError as exc:
            raise RuntimeError(
                "요약 엔진에 연결할 수 없습니다. Ollama를 실행했는지 또는 API 주소를 확인해 주세요."
            ) from exc
        except TimeoutError as exc:
            raise RuntimeError("요약 요청 시간이 초과되었습니다.") from exc

        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise RuntimeError("요약 엔진이 JSON이 아닌 응답을 반환했습니다.") from exc
        if not isinstance(payload, dict):
            raise RuntimeError("요약 엔진 응답 형식이 올바르지 않습니다.")
        return payload


def _parse_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            raise RuntimeError("요약 모델 응답에서 JSON을 찾지 못했습니다.")
        try:
            payload = json.loads(text[start : end + 1])
        except json.JSONDecodeError as exc:
            raise RuntimeError("요약 모델의 JSON 응답을 해석하지 못했습니다.") from exc

    if not isinstance(payload, dict):
        raise RuntimeError("요약 모델 응답은 JSON 객체여야 합니다.")
    return payload
