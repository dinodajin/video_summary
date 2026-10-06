from __future__ import annotations

import unittest

from app.services.diarization import DiarizationSegment
from app.services.stt import SttSegment, SttWord
from app.services.transcript_formatter import build_transcript, refine_stt_segments_with_diarization_words


class TranscriptFormatterTests(unittest.TestCase):
    def test_build_transcript_with_speakers_and_timestamps(self) -> None:
        stt_segments = [
            SttSegment(start=0.0, end=2.2, text="안녕하세요."),
            SttSegment(start=2.2, end=5.0, text="반갑습니다."),
        ]
        diarization_segments = [
            DiarizationSegment(start=0.0, end=2.4, speaker="SPEAKER_00"),
            DiarizationSegment(start=2.4, end=5.0, speaker="SPEAKER_01"),
        ]

        transcript, segments = build_transcript(
            stt_segments,
            diarization_segments,
            use_timestamps=True,
            speaker_label_style="ko",
        )

        self.assertIn("[00:00:00] 화자1: 안녕하세요.", transcript)
        self.assertIn("[00:00:02] 화자2: 반갑습니다.", transcript)
        self.assertEqual(len(segments), 2)
        self.assertEqual(segments[0].speaker, "화자1")
        self.assertEqual(segments[1].speaker, "화자2")

    def test_build_transcript_without_diarization(self) -> None:
        stt_segments = [SttSegment(start=10.0, end=12.0, text="내용입니다.")]
        transcript, segments = build_transcript(stt_segments, [], use_timestamps=False)

        self.assertEqual(transcript, "화자?: 내용입니다.")
        self.assertEqual(len(segments), 1)
        self.assertEqual(segments[0].speaker, "화자?")

    def test_build_transcript_smooths_short_speaker_spike(self) -> None:
        stt_segments = [
            SttSegment(start=0.0, end=1.8, text="첫 문장"),
            SttSegment(start=1.8, end=2.4, text="짧은 끼어들기"),
            SttSegment(start=2.4, end=4.2, text="다시 이어서 설명"),
        ]
        diarization_segments = [
            DiarizationSegment(start=0.0, end=1.8, speaker="SPEAKER_00"),
            DiarizationSegment(start=1.8, end=2.4, speaker="SPEAKER_01"),
            DiarizationSegment(start=2.4, end=4.2, speaker="SPEAKER_00"),
        ]

        _, segments = build_transcript(stt_segments, diarization_segments, use_timestamps=False)

        self.assertEqual(segments[0].speaker, "화자1")
        self.assertEqual(segments[1].speaker, "화자1")
        self.assertEqual(segments[2].speaker, "화자1")

    def test_build_transcript_replaces_unknown_with_neighbor(self) -> None:
        stt_segments = [
            SttSegment(start=0.0, end=1.5, text="소개"),
            SttSegment(start=1.5, end=3.0, text="중간 발화"),
            SttSegment(start=3.0, end=4.5, text="마무리"),
        ]
        diarization_segments = [
            DiarizationSegment(start=0.0, end=1.5, speaker="SPEAKER_00"),
            DiarizationSegment(start=3.0, end=4.5, speaker="SPEAKER_00"),
        ]

        _, segments = build_transcript(stt_segments, diarization_segments, use_timestamps=False)
        self.assertEqual([seg.speaker for seg in segments], ["화자1", "화자1", "화자1"])

    def test_refine_splits_mixed_speaker_segment(self) -> None:
        words = [
            SttWord(0.0, 1.0, "첫"),
            SttWord(1.0, 2.0, "둘"),
        ]
        stt_segments = [
            SttSegment(start=0.0, end=2.0, text="첫 둘", words=words),
        ]
        diarization_segments = [
            DiarizationSegment(start=0.0, end=1.0, speaker="SPEAKER_00"),
            DiarizationSegment(start=1.0, end=2.0, speaker="SPEAKER_01"),
        ]
        refined = refine_stt_segments_with_diarization_words(stt_segments, diarization_segments)
        self.assertEqual(len(refined), 2)
        transcript, segments = build_transcript(
            refined,
            diarization_segments,
            use_timestamps=True,
            speaker_label_style="ko",
            smooth_short_spike_sec=0.0,
        )
        self.assertEqual(len(segments), 2)
        self.assertEqual(segments[0].speaker, "화자1")
        self.assertEqual(segments[1].speaker, "화자2")
        self.assertIn("화자1:", transcript)
        self.assertIn("화자2:", transcript)

    def test_smooth_short_spike_disabled_keeps_middle_speaker(self) -> None:
        stt_segments = [
            SttSegment(start=0.0, end=1.8, text="첫 문장"),
            SttSegment(start=1.8, end=2.4, text="짧은 끼어들기"),
            SttSegment(start=2.4, end=4.2, text="다시 이어서 설명"),
        ]
        diarization_segments = [
            DiarizationSegment(start=0.0, end=1.8, speaker="SPEAKER_00"),
            DiarizationSegment(start=1.8, end=2.4, speaker="SPEAKER_01"),
            DiarizationSegment(start=2.4, end=4.2, speaker="SPEAKER_00"),
        ]
        _, segments = build_transcript(
            stt_segments,
            diarization_segments,
            use_timestamps=False,
            smooth_short_spike_sec=0.0,
        )
        self.assertEqual(segments[0].speaker, "화자1")
        self.assertEqual(segments[1].speaker, "화자2")
        self.assertEqual(segments[2].speaker, "화자1")


if __name__ == "__main__":
    unittest.main()
