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
                self.assertEqual("v1.0.0", payload["metadata"]["release"])
                self.assertEqual(14_480, len(payload["rows"]))
                self.assertEqual(14_480, payload["stats"]["total_locations"])
                self.assertEqual(7_186, payload["stats"]["municipalities"])
                self.assertEqual(
                    7_294, payload["stats"]["unclassified_localities"]
                )
                self.assertEqual(4_459, payload["stats"]["unique_postal_codes"])
                self.assertEqual(12_388, payload["stats"]["with_coordinates"])
                self.assertEqual(2_092, payload["stats"]["missing_coordinates"])
                self.assertEqual(
                    85.55, payload["stats"]["coordinate_coverage_percent"]
                )

    def test_site_declares_search_map_downloads_and_metadata(self) -> None:
        source = (REPOSITORY_ROOT / "site" / "index.html").read_text(
            encoding="utf-8"
        )
        for required in (
            'id="query"',
            'id="province"',
            'id="coverage-map"',
            'property="og:image"',
            "italian_locations.csv",
            "italian_locations.json",
            "italian_locations.sqlite",
        ):
            self.assertIn(required, source)
        self.assertNotIn("http://", source)

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
