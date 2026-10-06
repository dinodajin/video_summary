from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.services.ingest import validate_video_file
from app.utils.errors import ValidationError


class MediaValidationTests(unittest.TestCase):
    def test_validate_video_file_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.mp4"
            path.write_bytes(b"0" * 1024)
            out = validate_video_file(str(path), max_file_mb=1)
            self.assertEqual(out, path)

    def test_validate_video_file_unsupported_extension(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.txt"
            path.write_text("x", encoding="utf-8")
            with self.assertRaises(ValidationError):
                validate_video_file(str(path), max_file_mb=1)

    def test_validate_video_file_too_large(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.mp4"
            path.write_bytes(b"0" * (2 * 1024 * 1024))
            with self.assertRaises(ValidationError):
                validate_video_file(str(path), max_file_mb=1)


if __name__ == "__main__":
    unittest.main()
