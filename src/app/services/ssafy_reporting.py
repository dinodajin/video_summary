from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Callable

from app.config import AppConfig
from app.services.report_summarizer import ReportSummarizer, TeamReport


TEAM_CODES = tuple(f"A5{i:02d}" for i in range(1, 10))

WEEKLY_FIELDS = (
    ("overall", "프로젝트 전체 진행사항 및 수준"),
    ("basic_requirements", "기본요구사항"),
    ("basic_progress", "기본요구사항에 대한 개발진척도"),
    ("additional_requirements", "추가개발사항"),
    ("additional_progress", "추가개발사항에 대한 개발진척도"),
    ("issues", "이슈사항"),
)


@dataclass(slots=True)
class WeeklyReport:
    overall: str
    basic_requirements: str
    basic_progress: str
    additional_requirements: str
    additional_progress: str
    issues: str

    def render(self) -> str:
        return "\n\n".join(
            f"[{label}]\n{getattr(self, field)}" for field, label in WEEKLY_FIELDS
        )


@dataclass(slots=True)
class CombinedReport:
    daily: TeamReport
    weekly: WeeklyReport


def parse_daily_text(text: str, team_code: str) -> TeamReport:
    """UI에서 사용자가 수정한 보고서를 다시 구조화한다."""
    match = re.search(r"\[종합\]", text)
    if not match:
        raise ValueError("일일 보고서에서 [종합] 구분을 찾지 못했습니다.")
    content_part = text[: match.start()].replace("[내용]", "").strip()
    summary_part = text[match.end() :].strip()
    content = [
        re.sub(r"^\s*[•\-*]\s*", "", line).strip()
        for line in content_part.splitlines()
        if line.strip()
    ]
    summary = re.sub(r"^\s*[•\-*]\s*", "", summary_part).strip()
    if not content or not summary:
        raise ValueError("일일 보고서의 내용 또는 종합이 비어 있습니다.")
    return TeamReport(team_code=team_code, content=content, summary=summary)


def parse_weekly_text(text: str) -> WeeklyReport:
    values: dict[str, str] = {}
    for index, (field, label) in enumerate(WEEKLY_FIELDS):
        marker = f"[{label}]"
        pos = text.find(marker)
        if pos < 0:
            raise ValueError(f"주간 보고서에서 {marker} 구분을 찾지 못했습니다.")
        start = pos + len(marker)
        next_label = WEEKLY_FIELDS[index + 1][1] if index + 1 < len(WEEKLY_FIELDS) else None
        end = text.find(f"[{next_label}]", start) if next_label else len(text)
        value = text[start:end].strip()
        values[field] = value or "전사에서 확인되지 않음."
    return WeeklyReport(**values)


def normalize_report_style(text: str) -> str:
    """AI가 혼용한 일부 존댓말 종결형을 보고서용 '~함/~임/~음'으로 통일함.

    문장 끝의 대표적인 종결형만 바꿔 원래 사실·수치·기술명을 훼손하지 않음.
    """
    replacements = (
        (r"(할\s+예정입니다)(?=[.!?\s]|$)", "할 예정임"),
        (r"(해야\s+합니다)(?=[.!?\s]|$)", "해야 함"),
        (r"(하고\s+있습니다)(?=[.!?\s]|$)", "하고 있음"),
        (r"(할\s+계획입니다)(?=[.!?\s]|$)", "할 계획임"),
        (r"(되지\s+않았습니다)(?=[.!?\s]|$)", "되지 않았음"),
        (r"(하지\s+않았습니다)(?=[.!?\s]|$)", "하지 않았음"),
        (r"(하였습니다)(?=[.!?\s]|$)", "함"),
        (r"(했습니다)(?=[.!?\s]|$)", "함"),
        (r"(되었습니다)(?=[.!?\s]|$)", "됨"),
        (r"(됐습니다)(?=[.!?\s]|$)", "됨"),
        (r"(있었습니다)(?=[.!?\s]|$)", "있었음"),
        (r"(없었습니다)(?=[.!?\s]|$)", "없었음"),
        (r"(않습니다)(?=[.!?\s]|$)", "않음"),
        (r"(있습니다)(?=[.!?\s]|$)", "있음"),
        (r"(없습니다)(?=[.!?\s]|$)", "없음"),
        (r"(필요합니다)(?=[.!?\s]|$)", "필요함"),
        (r"(가능합니다)(?=[.!?\s]|$)", "가능함"),
        (r"(예정입니다)(?=[.!?\s]|$)", "예정임"),
        (r"(계획입니다)(?=[.!?\s]|$)", "계획임"),
        (r"(합니다)(?=[.!?\s]|$)", "함"),
        (r"(됩니다)(?=[.!?\s]|$)", "됨"),
        (r"(입니다)(?=[.!?\s]|$)", "임"),
    )
    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text)
    return text.strip()


class SsafyReportBuilder:
    """단일 전사본에서 서울 5반 일일/기업연계 주간 양식을 동시에 생성."""

    def __init__(self, config: AppConfig):
        self._config = config
        self._llm = ReportSummarizer(config)

    def summarize(
        self, transcript: str, team_code: str, progress: Callable[[str], None] | None = None
    ) -> CombinedReport:
        team_code = team_code.strip().upper()
        if team_code not in TEAM_CODES:
            raise ValueError("서울 5반 팀 코드(A501~A509)를 선택해 주세요.")
        transcript = transcript.strip()
        if not transcript:
            raise ValueError("요약할 전사본이 비어 있습니다.")

        size = max(4_000, int(self._config.summary_chunk_chars))
        source = transcript
        if len(transcript) > size:
            chunks = [transcript[i:i + size] for i in range(0, len(transcript), size)]
            facts: list[str] = []
            for idx, chunk in enumerate(chunks, 1):
                if progress:
                    progress(f"멘토링 핵심 내용 추출 중... ({idx}/{len(chunks)})")
                facts.extend(self._llm._request_facts(chunk, idx, len(chunks)))
            if not facts:
                raise RuntimeError("긴 전사본에서 프로젝트 관련 정보를 추출하지 못했습니다.")
            source = "\n".join(f"- {fact}" for fact in facts)

        system = (
            "너는 SSAFY 기업연계 프로젝트 서울 5반의 일일·주차별 멘토링 보고서를 작성하는 실습코치다. "
            "두 보고서의 모든 문장을 반드시 '~함.', '~임.', '~음.', '~중임.', '~예정임.', '~필요함.', '~확인되지 않음.' "
            "같은 간결한 보고체(음슴체)로 끝내라. '~습니다.', '~입니다.', '~합니다.', '~하였습니다.' 등의 존댓말을 사용하지 마라. "
            "입력 전사본에 근거한 사실만 작성하고 인사·자기소개·잡담은 제외하라. "
            "불분명한 인명·기술명·수치·날짜를 만들어내지 마라. "
            "성과와 목표, 계획과 구현 완료, 멘토 권고와 확정된 사항을 구분하라. "
            "요구사항 발표나 토론을 개발 완료로 오인하지 마라. "
            "멘토링 횟수·시간과 진척률을 임의 계산하지 마라. "
            "확인되지 않은 주간 항목은 '전사에서 확인되지 않음.'으로 적어라."
        )
        user = f"""팀 코드: {team_code}
아래 전사본을 바탕으로 두 보고서를 동시에 작성하라.

[공통 문체 - 반드시 준수]
- 모든 항목을 '~함.', '~임.', '~음.', '~중임.', '~예정임.', '~필요함.'으로 끝나는 음슴체로 작성.
- 금지: '~했습니다.', '~합니다.', '~입니다.', '~하였습니다.', '~할 것입니다.'
- 예: '멘토와 기본 요구사항을 검토함.', '문서 파싱 기능을 설계 중임.', '다음 주에 검증할 예정임.'
- 보고서에 없는 사실을 유추하여 채우지 말 것. 같은 내용 반복 금지.

[1. 일일 프로젝트 진행 보고서 - 간결하게]
- daily.content: 진행 상황, 핵심 요구사항, 멘토 Q&A, 피드백, 결정 사항, 향후 작업 중 핵심 2~5개.
  항목당 1문장, 너무 많은 세부사항은 넣지 말 것. 전부 음슴체.
- daily.summary: 현재 팀의 진행 단계·핵심 과제를 1문장으로 요약. 음슴체.

[2. 주차별 기업연계 멘토링 진행현황 - 일일보다 구체적으로]
- weekly.overall(프로젝트 전체 진행사항 및 수준): 프로젝트 목적, 이번 주 확인·진행한 일,
  현재 단계(요구사항 이해/설계/개발/검증 등), 다음 진행 방향을 구체적으로 2~4문장으로 작성.
- weekly.basic_requirements(기본요구사항): 멘토가 명시한 필수 기능·데이터 형식·기술 조건·평가 기준을
  구체적인 명칭과 수치(실제 언급된 경우만)까지 포함하여 2~5문장으로 작성.
- weekly.basic_progress(기본요구사항에 대한 개발진척도): 이번 주 실제 완료한 작업, 검토 중인 설계,
  아직 미구현인 작업을 구별하여 2~4문장으로 기술. 개발 완료 근거가 없으면 '요구사항 분석·설계 단계임.' 등으로 명확히 기재.
- weekly.additional_requirements(추가개발사항): 멘토가 선택 사항으로 제시했거나 팀이 제안한 부가 기능,
  개선 아이디어 및 논의된 적용 조건을 확인된 범위에서 1~3문장으로 구체화.
  단, 기본 요구사항을 추가개발로 옮기지 말 것. 언급 없으면 '전사에서 확인되지 않음.'
- weekly.additional_progress(추가개발사항에 대한 개발진척도): 추가 기능의 기획·논의·설계·구현 상태를
  1~3문장으로 구별하여 기술. 구현 근거 없으면 '추가 기능 구현 여부는 전사에서 확인되지 않음.'
- weekly.issues(이슈사항): 실제 확인된 기술적 제약, 사내 정책, 데이터/권한 제한,
  미확정 의사결정 및 후속 확인 사항을 원인·영향·대응 방향 중심으로 1~4문장 기술.
  단, 일반적인 가능성만으로 문제를 만들어내지 말 것. 언급 없으면 '전사에서 확인되지 않음.'

[주차별 상세 작성 규칙]
- 주간 항목은 일일보다 맥락을 충분히 남길 것. '논의함.' 같은 모호한 표현만 쓰지 말고 무엇을 어떻게 논의했는지 적을 것.
- 구체성이 부족한 전사라면 근거가 있는 사실만 1문장 기재. 분량을 채우기 위해 내용을 만들지 말 것.
- 실제로 발언된 기술명, 기능, 지표와 목표치만 사용. 목표치와 달성치를 혼동하지 말 것.
- 팀원이 질문한 사항과 멘토가 확답한 사항을 명확히 구분할 것.
- 6개 weekly 값은 문자열이며, 여러 문장을 쓸 경우 한 셀 안에서 '문장1. 문장2.' 형태로 작성.

반드시 다음 JSON 형식만 반환하라:
{{
  "daily": {{"content": ["핵심 내용 1", "핵심 내용 2"], "summary": "종합 한 문장"}},
  "weekly": {{
    "overall": "...", "basic_requirements": "...", "basic_progress": "...",
    "additional_requirements": "...", "additional_progress": "...", "issues": "..."
  }}
}}

[입력 전사]
{source} """
        if progress:
            progress("일일/주간 보고서 문장 작성 중...")
        result: dict[str, Any] = self._llm._chat_json(system, user)
        daily = result.get("daily")
        weekly = result.get("weekly")
        if not isinstance(daily, dict) or not isinstance(weekly, dict):
            raise RuntimeError("요약 모델이 일일/주간 보고서 JSON을 반환하지 않았습니다.")
        content = daily.get("content")
        summary = daily.get("summary")
        if not isinstance(content, list) or not isinstance(summary, str):
            raise RuntimeError("일일 보고서 형식이 올바르지 않습니다.")
        clean_content = [normalize_report_style(str(x)) for x in content if str(x).strip()]
        if not clean_content or not summary.strip():
            raise RuntimeError("일일 보고서가 비어 있습니다.")
        weekly_values = {}
        for field, _ in WEEKLY_FIELDS:
            value = weekly.get(field, "")
            weekly_values[field] = normalize_report_style(str(value)) or "전사에서 확인되지 않음."
        return CombinedReport(
            daily=TeamReport(team_code=team_code, content=clean_content[:5], summary=normalize_report_style(summary)),
            weekly=WeeklyReport(**weekly_values),
        )
