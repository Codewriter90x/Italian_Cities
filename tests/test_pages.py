from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_pages import build_site  # noqa: E402
from project_metadata import DATASET_VERSION  # noqa: E402


def directory_hashes(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
        for path in sorted(item for item in root.rglob("*") if item.is_file())
    }


class GitHubPagesBuildTests(unittest.TestCase):
    def test_build_is_complete_and_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as first_dir:
            with tempfile.TemporaryDirectory() as second_dir:
                first = Path(first_dir) / "site"
                second = Path(second_dir) / "site"
                first_manifest = build_site(first)
                second_manifest = build_site(second)
                self.assertEqual(first_manifest, second_manifest)
                self.assertEqual(directory_hashes(first), directory_hashes(second))
                payload = json.loads(
                    (first / "assets/locations.json").read_text(
                        encoding="utf-8"
                    )
                )
                self.assertEqual(DATASET_VERSION, payload["metadata"]["release"])
                self.assertEqual(
                    "experimental_non_official",
                    payload["metadata"]["operational_data_readiness"],
                )
                self.assertIn(
                    "GeoNames", payload["metadata"]["attribution"]["geonames"]
                )
                self.assertEqual(
                    7894, payload["stats"]["municipalities"]
                )
                self.assertEqual(
                    396,
                    payload["stats"]["missing_postal_code_municipalities"],
                )
                self.assertNotIn(
                    "coordinate_coverage_percent", payload["stats"]
                )

    def test_site_declares_clean_room_warnings_and_downloads(self) -> None:
        source = (ROOT / "site/index.html").read_text(encoding="utf-8")
        for required in (
            'id="query"',
            'id="province"',
            'id="coverage-map"',
            'id="map-fallback-body"',
            "GeoNames non è Poste Italiane",
            "GeoNames</a>, CC BY 4.0",
            "v2.0.0 · prerelease",
            "raw/refs/heads/main/data/italian_locations.csv",
            "Confini regionali generalizzati ISTAT",
        ):
            self.assertIn(required, source)
        self.assertNotIn("analytics", source.casefold())
        self.assertNotIn("cookie", source.casefold())
        self.assertNotIn("nominatim", source.casefold())

    def test_committed_geographic_base_has_official_provenance(self) -> None:
        payload = json.loads(
            (ROOT / "site/assets/italy-regions.geojson").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual("FeatureCollection", payload["type"])
        self.assertEqual(20, len(payload["features"]))
        self.assertEqual("CC BY 4.0", payload["source"]["license"])


if __name__ == "__main__":
    unittest.main()
