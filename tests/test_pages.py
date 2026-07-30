from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))

from build_pages import build_site  # noqa: E402
from project_metadata import DATASET_VERSION  # noqa: E402


def directory_hashes(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        result[path.relative_to(root).as_posix()] = hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
    return result


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

                required_files = {
                    ".nojekyll",
                    "assets/app.js",
                    "assets/core.mjs",
                    "assets/italy-regions.geojson",
                    "assets/locations.json",
                    "assets/social-preview.jpg",
                    "assets/styles.css",
                    "build-manifest.json",
                    "favicon.svg",
                    "index.html",
                    "robots.txt",
                    "sitemap.xml",
                }
                self.assertEqual(required_files, set(directory_hashes(first)))

                payload = json.loads(
                    (first / "assets" / "locations.json").read_text(
                        encoding="utf-8"
                    )
                )
                rows = payload["rows"]
                total = len(rows)
                municipalities = sum(
                    row["location_kind"] == "municipality" for row in rows
                )
                with_coordinates = sum(row["latitude"] is not None for row in rows)
                verified_coordinates = sum(
                    row["coordinate_verification"] == "verified" for row in rows
                )
                legacy_unverified_coordinates = sum(
                    row["coordinate_verification"]
                    in {"legacy_unverified", "corrected_legacy_unverified"}
                    for row in rows
                )
                self.assertEqual(DATASET_VERSION, payload["metadata"]["release"])
                self.assertEqual("prerelease", payload["metadata"]["release_status"])
                self.assertEqual(
                    total, payload["stats"]["total_locations"]
                )
                self.assertEqual(municipalities, payload["stats"]["municipalities"])
                self.assertEqual(
                    total - municipalities,
                    payload["stats"]["unclassified_localities"],
                )
                self.assertEqual(
                    len({row["postal_code"] for row in rows}),
                    payload["stats"]["unique_postal_codes"],
                )
                self.assertEqual(
                    with_coordinates, payload["stats"]["with_coordinates"]
                )
                self.assertEqual(
                    total - with_coordinates,
                    payload["stats"]["missing_coordinates"],
                )
                self.assertEqual(
                    round(with_coordinates / total * 100, 2),
                    payload["stats"]["coordinate_coverage_percent"],
                )
                self.assertEqual(
                    verified_coordinates,
                    payload["stats"]["verified_coordinates"],
                )
                self.assertEqual(
                    legacy_unverified_coordinates,
                    payload["stats"]["legacy_unverified_coordinates"],
                )
                self.assertEqual(
                    sum(
                        row["postal_code_status"] == "generic_multicap"
                        for row in rows
                    ),
                    payload["stats"]["generic_multicap_rows"],
                )

    def test_site_declares_search_map_downloads_and_metadata(self) -> None:
        source = (REPOSITORY_ROOT / "site" / "index.html").read_text(
            encoding="utf-8"
        )
        for required in (
            'id="query"',
            'id="province"',
            'id="coverage-map"',
            'id="map-fallback-body"',
            'property="og:image"',
            "releases/download/v1.1.0/italian_locations.csv",
            "releases/download/v1.1.0/italian_locations.json",
            "releases/download/v1.1.0/italian_locations.sqlite",
            "Confini regionali generalizzati ISTAT",
        ):
            self.assertIn(required, source)
        self.assertNotIn("http://", source)

    def test_committed_geographic_base_has_official_provenance(self) -> None:
        payload = json.loads(
            (
                REPOSITORY_ROOT / "site" / "assets" / "italy-regions.geojson"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual("FeatureCollection", payload["type"])
        self.assertEqual(20, len(payload["features"]))
        self.assertEqual("2026-01-01", payload["source"]["reference_date"])
        self.assertEqual("CC BY 4.0", payload["source"]["license"])
        self.assertEqual(
            "b011a590656c3a3ebc297fba80726a376aa843b6f164641cf6a4a990021a81d6",
            payload["source"]["archive_sha256"],
        )
        self.assertIn("istat.it", payload["source"]["url"])
        self.assertIn("simplified", payload["source"]["modifications"])

    def test_required_issue_forms_exist(self) -> None:
        template_dir = REPOSITORY_ROOT / ".github" / "ISSUE_TEMPLATE"
        required = {
            "wrong-locality.yml",
            "wrong-postal-code.yml",
            "missing-coordinate.yml",
            "administrative-change.yml",
        }
        self.assertTrue(required.issubset({path.name for path in template_dir.iterdir()}))
        for name in required:
            content = (template_dir / name).read_text(encoding="utf-8")
            self.assertIn("validations:", content)
            self.assertIn("required: true", content)
            self.assertIn("Provenienza", content)


if __name__ == "__main__":
    unittest.main()
