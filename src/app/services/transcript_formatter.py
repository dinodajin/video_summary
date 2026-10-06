from __future__ import annotations

from dataclasses import asdict, dataclass

from app.services.diarization import DiarizationSegment
from app.services.stt import SttSegment, SttWord


@dataclass(slots=True)
class TranscriptSegment:
    start: float
    end: float
    timestamp: str
    speaker: str
    text: str


def build_transcript(
    stt_segments: list[SttSegment],
    diarization_segments: list[DiarizationSegment],
    use_timestamps: bool = True,
    speaker_label_style: str = "ko",
    smooth_short_spike_sec: float = 1.0,
) -> tuple[str, list[TranscriptSegment]]:
    if not stt_segments:
        return "", []

    raw_speakers = _assign_speakers(
        stt_segments, diarization_segments, smooth_short_spike_sec=smooth_short_spike_sec
    )
    speaker_alias = _speaker_alias_map(raw_speakers, speaker_label_style=speaker_label_style)

    out_segments: list[TranscriptSegment] = []
    lines: list[str] = []
    for idx, stt_seg in enumerate(stt_segments):
        if not stt_seg.text.strip():
            continue
        raw_speaker = raw_speakers[idx]
        speaker = speaker_alias.get(raw_speaker, _fallback_label(speaker_label_style))
        timestamp = _format_timestamp(stt_seg.start)
        line = _format_line(stt_seg.text, speaker, timestamp, use_timestamps)
        lines.append(line)
        out_segments.append(
            TranscriptSegment(
                start=stt_seg.start,
                end=stt_seg.end,
                timestamp=timestamp,
                speaker=speaker,
                text=stt_seg.text,
            )
        )
    return "\n".join(lines).strip(), out_segments


def segments_to_jsonable(segments: list[TranscriptSegment]) -> list[dict[str, object]]:
    return [asdict(item) for item in segments]


def render_transcript_from_segments(
    segments: list[TranscriptSegment],
    use_timestamps: bool = True,
) -> str:
    """세그먼트 목록에서 전사 본문 문자열을 재구성한다(화자 라벨 치환 후 등에 사용)."""
    lines: list[str] = []
    for seg in segments:
        if not seg.text.strip():
            continue
        line = _format_line(seg.text, seg.speaker, seg.timestamp, use_timestamps)
        lines.append(line)
    return "\n".join(lines).strip()


def refine_stt_segments_with_diarization_words(
    stt_segments: list[SttSegment],
    diarization_segments: list[DiarizationSegment],
) -> list[SttSegment]:
    """단어 타임스탬프와 다이어리제이션을 맞춰, 한 STT 구간에 화자가 섞인 경우 세그먼트를 나눕니다."""
    if not diarization_segments:
        return [
            SttSegment(start=s.start, end=s.end, text=s.text.strip(), words=None)
            for s in stt_segments
            if s.text.strip()
        ]

    refined: list[SttSegment] = []
    for seg in stt_segments:
        text = seg.text.strip()
        if not text:
            continue
        if not seg.words:
            refined.append(SttSegment(start=seg.start, end=seg.end, text=text, words=None))
            continue

        bucket: list[SttWord] = []
        bucket_speaker: str | None = None

        for w in seg.words:
            spk = _best_speaker(w.start, w.end, diarization_segments)
            if not bucket:
                bucket.append(w)
                bucket_speaker = spk
                continue
            if spk == bucket_speaker:
                bucket.append(w)
            else:
                _append_merged_word_segment(refined, bucket)
                bucket = [w]
                bucket_speaker = spk

        if bucket:
            _append_merged_word_segment(refined, bucket)

    return refined


def _append_merged_word_segment(out: list[SttSegment], bucket: list[SttWord]) -> None:
    merged = "".join(w.word for w in bucket).strip()
    if not merged:
        return
    out.append(
        SttSegment(
            start=float(bucket[0].start),
            end=float(bucket[-1].end),
            text=merged,
            words=None,
        )
    )


def _assign_speakers(
    stt_segments: list[SttSegment],
    diarization_segments: list[DiarizationSegment],
    smooth_short_spike_sec: float = 1.0,
) -> list[str]:
    if not diarization_segments:
        return ["UNKNOWN"] * len(stt_segments)
    initial = [_best_speaker(seg.start, seg.end, diarization_segments) for seg in stt_segments]
    return _smooth_speaker_sequence(stt_segments, initial, short_spike_merge_max_sec=smooth_short_spike_sec)


def _best_speaker(start: float, end: float, diarization_segments: list[DiarizationSegment]) -> str:
    best_speaker = "UNKNOWN"
    best_overlap = 0.0
    for dia in diarization_segments:
        overlap = _overlap(start, end, dia.start, dia.end)
        if overlap > best_overlap:
            best_overlap = overlap
            best_speaker = dia.speaker
    return best_speaker


def _overlap(a_start: float, a_end: float, b_start: float, b_end: float) -> float:
    return max(0.0, min(a_end, b_end) - max(a_start, b_start))


def _segment_duration(seg: SttSegment) -> float:
    return max(0.0, float(seg.end) - float(seg.start))


def _smooth_speaker_sequence(
    stt_segments: list[SttSegment],
    speakers: list[str],
    short_spike_merge_max_sec: float = 1.0,
) -> list[str]:
    if not speakers:
        return speakers
    if len(speakers) == 1:
        return speakers

    out = list(speakers)

    # 1) UNKNOWN 라벨은 인접 화자로 보정
    for idx, spk in enumerate(out):
        if spk != "UNKNOWN":
            continue
        prev_spk = out[idx - 1] if idx > 0 else None
        next_spk = out[idx + 1] if idx + 1 < len(out) else None
        if prev_spk and prev_spk != "UNKNOWN":
            out[idx] = prev_spk
        elif next_spk and next_spk != "UNKNOWN":
            out[idx] = next_spk

    # 2) 매우 짧은 단일 스파이크(예: A-B-A, B가 임계 시간 미만) 제거
    if short_spike_merge_max_sec > 0:
        for idx in range(1, len(out) - 1):
            prev_spk = out[idx - 1]
            curr_spk = out[idx]
            next_spk = out[idx + 1]
            if curr_spk == "UNKNOWN":
                continue
            if prev_spk == next_spk and curr_spk != prev_spk:
                if _segment_duration(stt_segments[idx]) <= short_spike_merge_max_sec:
                    out[idx] = prev_spk

    return out


def _speaker_alias_map(raw_speakers: list[str], speaker_label_style: str) -> dict[str, str]:
    aliases: dict[str, str] = {}
    sequence = 1
    for raw in raw_speakers:
        if raw == "UNKNOWN" or raw in aliases:
            continue
        if speaker_label_style == "en":
            aliases[raw] = f"Speaker{sequence}"
        else:
            aliases[raw] = f"화자{sequence}"
        sequence += 1
    return aliases


def _fallback_label(style: str) -> str:
    if style == "en":
        return "Speaker?"
    return "화자?"


def _format_timestamp(total_seconds: float) -> str:
    whole = max(0, int(total_seconds))
    hours = whole // 3600
    minutes = (whole % 3600) // 60
    seconds = whole % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def _format_line(text: str, speaker: str, timestamp: str, use_timestamps: bool) -> str:
    if use_timestamps:
        return f"[{timestamp}] {speaker}: {text}"
    return f"{speaker}: {text}"
