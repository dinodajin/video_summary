from __future__ import annotations

import unittest

from app.services.speaker_roles import (
    apply_speaker_label_map,
    build_speaker_label_mapping,
    build_speaker_preview,
    distinct_speaker_labels_in_order,
)
from app.services.transcript_formatter import TranscriptSegment, render_transcript_from_segments


def _seg(
    start: float,
    end: float,
    ts: str,
    speaker: str,
    text: str,
) -> TranscriptSegment:
    return TranscriptSegment(
        start=start,
        end=end,
        timestamp=ts,
        speaker=speaker,
        text=text,
    )


class SpeakerRolesTests(unittest.TestCase):
    def test_distinct_speakers_order(self) -> None:
        segments = [
            _seg(0.0, 1.0, "00:00:00", "화자1", "짧음"),
            _seg(1.0, 2.0, "00:00:01", "화자2", "이것은 충분히 긴 문장입니다."),
            _seg(3.0, 4.0, "00:00:03", "화자1", "다른 내용의 긴 문장입니다."),
        ]
        self.assertEqual(distinct_speaker_labels_in_order(segments), ["화자1", "화자2"])

    def test_build_speaker_preview_quotes_and_stats(self) -> None:
        segments = [
            _seg(0.0, 1.0, "00:00:00", "화자1", "짧음"),
            _seg(1.0, 2.0, "00:00:01", "화자1", "중복입니다."),
            _seg(2.0, 3.0, "00:00:02", "화자1", "중복입니다."),
            _seg(4.0, 6.0, "00:00:04", "화자1", "새로운 긴 문장입니다."),
        ]
        previews = build_speaker_preview(segments, min_chars=8, max_quotes=6)
        self.assertEqual(len(previews), 1)
        p = previews[0]
        self.assertEqual(p.speaker_label, "화자1")
        self.assertIn("새로운 긴 문장입니다.", p.quotes)
        self.assertEqual(p.segment_count, 4)
        self.assertGreaterEqual(p.char_count, 10)
        self.assertTrue(p.summary_line)
        self.assertGreaterEqual(p.char_share_ratio, 0.99)

    def test_apply_mapping_transcript_and_segments(self) -> None:
        segments = [
            _seg(0.0, 1.0, "00:00:00", "화자1", "안녕하세요."),
            _seg(2.0, 3.0, "00:00:02", "화자2", "반갑습니다."),
        ]
        mapping = build_speaker_label_mapping(
            "화자2",
            distinct_speaker_labels_in_order(segments),
            map_others_to_trainee=True,
            trainee_label="교육생",
        )
        transcript, mapped = apply_speaker_label_map(segments, mapping, use_timestamps=True)
        self.assertEqual(mapped[0].speaker, "교육생")
        self.assertEqual(mapped[1].speaker, "멘토")
        self.assertIn("멘토:", transcript)
        self.assertIn("교육생:", transcript)
        rerendered = render_transcript_from_segments(mapped, use_timestamps=True)
        self.assertEqual(transcript, rerendered)

    def test_empty_mapping_no_change(self) -> None:
        segments = [_seg(0.0, 1.0, "00:00:00", "화자1", "테스트 문장입니다.")]
        t1, s1 = apply_speaker_label_map(segments, {}, use_timestamps=False)
        t2 = render_transcript_from_segments(segments, use_timestamps=False)
        self.assertEqual(t1, t2)
        self.assertEqual(len(s1), 1)
        self.assertEqual(s1[0].speaker, "화자1")


if __name__ == "__main__":
    unittest.main()
