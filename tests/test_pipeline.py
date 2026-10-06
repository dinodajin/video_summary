from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.config import AppConfig
from app.core.pipeline import VideoPipeline


class PipelineTests(unittest.TestCase):
    @patch("app.core.pipeline.ensure_audio_stream")
    @patch("app.core.pipeline.extract_audio_wav")
    @patch("app.core.pipeline.SttService.transcribe")
    def test_pipeline_run(
        self,
        transcribe_mock,
        extract_mock,
        ensure_mock,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            video = Path(tmp) / "sample.mp4"
            audio = Path(tmp) / "sample.wav"
            video.write_bytes(b"123")
            audio.write_bytes(b"456")

            cfg = AppConfig(max_file_mb=100)
            cfg.diarization_enabled = False
            pipeline = VideoPipeline(cfg)

            class DummySttResult:
                transcript = "테스트 전사"
                detected_language = "ko"
                segments = []

            extract_mock.return_value = audio
            transcribe_mock.return_value = DummySttResult()

            result = pipeline.run(
                str(video),
                lang_mode="default",
                manual_language="ko",
            )

            self.assertEqual(result.transcript, "테스트 전사")
            self.assertEqual(result.language, "ko")
            self.assertEqual(result.segments, [])
            self.assertFalse(result.diarization_used)
            self.assertEqual(result.warnings, [])
            ensure_mock.assert_called_once()
            extract_mock.assert_called_once()
            transcribe_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
