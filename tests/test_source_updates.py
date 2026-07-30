from __future__ import annotations

import hashlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from update_sources import download, inspect_source, stage_download  # noqa: E402


class FakeResponse(io.BytesIO):
    def __init__(self, payload: bytes) -> None:
        super().__init__(payload)
        self.headers = {
            "Last-Modified": "Thu, 30 Jul 2026 00:00:00 GMT",
            "ETag": '"test"',
        }

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


class SourceUpdateTests(unittest.TestCase):
    def test_download_records_hash_and_http_metadata(self) -> None:
        payload = b"upstream artifact"
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "source.bin"
            with patch(
                "update_sources.urlopen",
                return_value=FakeResponse(payload),
            ):
                report = download("https://example.test/source", destination)
            self.assertEqual(payload, destination.read_bytes())
        self.assertEqual(hashlib.sha256(payload).hexdigest(), report["sha256"])
        self.assertEqual('"test"', report["etag"])

    def test_inspection_distinguishes_current_and_changed(self) -> None:
        payload = b"declared"
        source = {
            "id": "example",
            "url": "https://example.test/source",
            "path": "source.bin",
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
        with patch(
            "update_sources.urlopen",
            return_value=FakeResponse(payload),
        ):
            self.assertEqual("current", inspect_source(source)["status"])
        with patch(
            "update_sources.urlopen",
            return_value=FakeResponse(b"changed"),
        ):
            self.assertEqual(
                "update_available",
                inspect_source(source)["status"],
            )

    def test_staging_never_overwrites_an_existing_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "existing.zip"
            output.write_bytes(b"keep")
            with self.assertRaisesRegex(FileExistsError, "refusing to overwrite"):
                stage_download("geonames_postal_codes", output)
            self.assertEqual(b"keep", output.read_bytes())


if __name__ == "__main__":
    unittest.main()
