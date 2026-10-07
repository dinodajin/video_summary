from __future__ import annotations

from dataclasses import dataclass

from app.constants import (
    SPEAKER_DEFAULT_TRAINEE_LABEL,
    SPEAKER_MAP_OTHERS_TO_TRAINEE_DEFAULT,
    SPEAKER_PREVIEW_MAX_QUOTES,
    SPEAKER_PREVIEW_MIN_CHARS,
)
from app.services.transcript_formatter import TranscriptSegment, render_transcript_from_segments


@dataclass(slots=True)
class SpeakerPreview:
    """표시용 화자 라벨(예: 화자1)별 미리보기."""

    speaker_label: str
    quotes: list[str]
    segment_count: int
    char_count: int
    first_start_sec: float
    last_end_sec: float
    question_like_ratio: float
    summary_line: str
    char_share_ratio: float


def _pick_diverse_quotes(
    segs: list[TranscriptSegment],
    min_chars: int,
    max_quotes: int,
) -> list[str]:
    """시간 순 후보를 모은 뒤, 초·중·후 등 간격을 두어 인용을 고른다."""
    candidates: list[tuple[float, str]] = []
    seen_norm: set[str] = set()
    for s in segs:
        t = s.text.strip()
        if len(t) < min_chars:
            continue
        key = " ".join(t.split())
        if key in seen_norm:
            continue
        seen_norm.add(key)
        candidates.append((float(s.start), t))
    candidates.sort(key=lambda x: x[0])
    n = len(candidates)
    if n == 0:
        return []
    if n <= max_quotes:
        return [t for _, t in candidates]

    indices: list[int] = []
    if max_quotes == 1:
        indices = [n // 2]
    else:
        for k in range(max_quotes):
            idx = round(k * (n - 1) / (max_quotes - 1))
            indices.append(max(0, min(n - 1, idx)))

    picked: list[str] = []
    seen_line: set[str] = set()
    for i in indices:
        line = candidates[i][1]
        if line not in seen_line:
            seen_line.add(line)
            picked.append(line)
    for _, t in candidates:
        if len(picked) >= max_quotes:
            break
        if t not in seen_line:
            seen_line.add(t)
            picked.append(t)
    return picked[:max_quotes]


def _heuristic_speaker_summary(
    *,
    segment_count: int,
    char_count: int,
    char_share_ratio: float,
    question_like_ratio: float,
) -> str:
    """LLM 없이 읽기 쉬운 한 줄 요약(휴리스틱)."""
    parts: list[str] = [
        f"전체 글자 수 대비 약 {char_share_ratio:.0%}를 말함.",
        f"발화 {segment_count}회·약 {char_count}자.",
    ]
    if question_like_ratio >= 0.38:
        parts.append("질문·확인형 문장 비중이 큼.")
    elif question_like_ratio <= 0.12:
        parts.append("설명·서술형 문장이 많음.")
    else:
        parts.append("질문과 설명이 섞임.")
    return " ".join(parts)


def build_speaker_preview(
    segments: list[TranscriptSegment],
    *,
    min_chars: int = SPEAKER_PREVIEW_MIN_CHARS,
    max_quotes: int = SPEAKER_PREVIEW_MAX_QUOTES,
) -> list[SpeakerPreview]:
    """화자별 인용 샘플과 간단 통계를 만든다(결정적 규칙만 사용)."""
    by_speaker: dict[str, list[TranscriptSegment]] = {}
    order: list[str] = []
    for seg in segments:
        if not seg.text.strip():
            continue
        spk = seg.speaker
        if spk not in by_speaker:
            by_speaker[spk] = []
            order.append(spk)
        by_speaker[spk].append(seg)

    total_chars = sum(len(s.text) for segs in by_speaker.values() for s in segs)
    if total_chars <= 0:
        total_chars = 1

    out: list[SpeakerPreview] = []
    for spk in order:
        segs = sorted(by_speaker[spk], key=lambda s: s.start)
        char_count = sum(len(s.text) for s in segs)
        share = char_count / total_chars
        q_like = 0
        total = 0
        for s in segs:
            total += 1
            if "?" in s.text or "？" in s.text:
                q_like += 1
        ratio = (q_like / total) if total else 0.0

        quotes = _pick_diverse_quotes(segs, min_chars, max_quotes)
        summary = _heuristic_speaker_summary(
            segment_count=len(segs),
            char_count=char_count,
            char_share_ratio=share,
            question_like_ratio=ratio,
        )

        out.append(
            SpeakerPreview(
                speaker_label=spk,
                quotes=quotes,
                segment_count=len(segs),
                char_count=char_count,
                first_start_sec=float(segs[0].start),
                last_end_sec=float(segs[-1].end),
                question_like_ratio=ratio,
                summary_line=summary,
                char_share_ratio=share,
            )
        )
    return out


def build_speaker_label_mapping(
    mentor_label: str | list[str] | tuple[str, ...] | set[str] | None,
    distinct_speakers: list[str],
    *,
    map_others_to_trainee: bool = SPEAKER_MAP_OTHERS_TO_TRAINEE_DEFAULT,
    trainee_label: str = SPEAKER_DEFAULT_TRAINEE_LABEL,
) -> dict[str, str]:
    """선택한 한 명 이상의 멘토와 나머지 화자에 대한 치환 맵을 만든다.

    기존 호출과의 호환을 위해 단일 문자열도 허용한다.
    """
    if mentor_label is None:
        return {}
    if isinstance(mentor_label, str):
        mentors = {mentor_label.strip()} if mentor_label.strip() else set()
    else:
        mentors = {str(label).strip() for label in mentor_label if str(label).strip()}
    if not mentors:
        return {}

    mapping: dict[str, str] = {}
    for spk in distinct_speakers:
        if spk in mentors:
            mapping[spk] = "멘토"
        elif map_others_to_trainee:
            mapping[spk] = trainee_label
        else:
            mapping[spk] = spk
    return mapping


def apply_speaker_label_map(
    segments: list[TranscriptSegment],
    label_mapping: dict[str, str],
    *,
    use_timestamps: bool = True,
) -> tuple[str, list[TranscriptSegment]]:
    """
    세그먼트의 speaker 필드를 치환하고 전사 문자열을 재생성한다.
    label_mapping이 비어 있으면 입력과 동일한 의미의 출력을 반환한다.
    """
    if not label_mapping:
        return render_transcript_from_segments(segments, use_timestamps=use_timestamps), list(segments)

    new_segments: list[TranscriptSegment] = []
    for seg in segments:
        if not seg.text.strip():
            continue
        new_spk = label_mapping.get(seg.speaker, seg.speaker)
        new_segments.append(
            TranscriptSegment(
                start=seg.start,
                end=seg.end,
                timestamp=seg.timestamp,
                speaker=new_spk,
                text=seg.text,
            )
        )
    transcript = render_transcript_from_segments(new_segments, use_timestamps=use_timestamps)
    return transcript, new_segments


def distinct_speaker_labels_in_order(segments: list[TranscriptSegment]) -> list[str]:
    order: list[str] = []
    seen: set[str] = set()
    for seg in segments:
        if not seg.text.strip():
            continue
        if seg.speaker not in seen:
            seen.add(seg.speaker)
            order.append(seg.speaker)
    return order
