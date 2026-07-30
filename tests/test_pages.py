from __future__ import annotations

import hashlib
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_pages import WEB_FIELDS, build_site  # noqa: E402
from project_metadata import DATASET_VERSION  # noqa: E402
from validate_site import validate_site  # noqa: E402


def directory_hashes(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
        for path in sorted(item for item in root.rglob("*") if item.is_file())
    }


class GitHubPagesBuildTests(unittest.TestCase):
    def test_build_is_complete_and_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as first_dir:  # noqa: SIM117
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
                    list(WEB_FIELDS),
                    payload["fields"],
                )
                self.assertIsInstance(payload["rows"][0], list)
                self.assertEqual(len(payload["fields"]), len(payload["rows"][0]))
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
                self.assertLess(
                    (first / "assets/locations.json").stat().st_size,
                    5_000_000,
                )
                self.assertEqual(25, first_manifest["page_count"])

    def test_site_declares_seo_release_and_clean_room_contracts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            output = Path(temporary_dir) / "site"
            build_site(output)
            source = (output / "index.html").read_text(encoding="utf-8")
            for required in (
                'id="query"',
                'id="province"',
                'id="coverage-map"',
                'id="map-fallback-body"',
                "GeoNames non è Poste Italiane",
                "GeoNames</a>, CC BY 4.0",
                "v2.0.0 · prerelease pubblicata",
                "releases/download/v2.0.0/italian_locations.csv",
                "releases/download/v2.0.0/SHA256SUMS",
                "releases/tag/v2.0.0",
                "Confini regionali generalizzati ISTAT",
                'rel="canonical"',
                'name="robots"',
                'property="og:image:width"',
                'type="application/ld+json"',
            ):
                self.assertIn(required, source)
            self.assertNotIn("non ancora pubblicata", source)
            self.assertNotIn("releases/tag/v1.1.0", source)
            self.assertNotIn("{{", source)
            self.assertNotIn("analytics", source.casefold())
            self.assertNotIn("cookie", source.casefold())
            self.assertNotIn("nominatim", source.casefold())

            match = re.search(
                r'<script type="application/ld\+json">(.*?)</script>',
                source,
            )
            self.assertIsNotNone(match)
            structured = json.loads(match.group(1))
            types = {item["@type"] for item in structured["@graph"]}
            self.assertEqual({"WebSite", "Dataset", "FAQPage"}, types)
            dataset = next(
                item
                for item in structured["@graph"]
                if item["@type"] == "Dataset"
            )
            self.assertEqual("2.0.0", dataset["version"])
            self.assertEqual(6, len(dataset["distribution"]))
            self.assertIn('id="copy-filter-link"', source)
            self.assertNotIn(
                "Gli asset pubblicati sono immutabili",
                source,
            )

    def test_sitemap_and_indexable_information_pages(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            output = Path(temporary_dir) / "site"
            manifest = build_site(output)
            sitemap = (output / "sitemap.xml").read_text(encoding="utf-8")
            self.assertEqual(manifest["page_count"], sitemap.count("<url>"))
            for path in (
                "dataset/",
                "schema/",
                "fonti/",
                "regioni/",
                "regioni/lazio/",
            ):
                self.assertIn(
                    f"https://codewriter90x.github.io/Italian_Cities/{path}",
                    sitemap,
                )
                self.assertTrue((output / path / "index.html").is_file())

            lazio = (output / "regioni/lazio/index.html").read_text(
                encoding="utf-8"
            )
            self.assertIn("Comuni, CAP e coordinate: Lazio", lazio)
            self.assertIn(">Roma</a>", lazio)
            self.assertIn("ISTAT 058091", lazio)
            self.assertIn('rel="canonical"', lazio)

    def test_committed_geographic_base_has_official_provenance(self) -> None:
        payload = json.loads(
            (ROOT / "site/assets/italy-regions.geojson").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual("FeatureCollection", payload["type"])
        self.assertEqual(20, len(payload["features"]))
        self.assertEqual("CC BY 4.0", payload["source"]["license"])

    def test_site_accessibility_links_and_budgets(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            output = Path(temporary_dir) / "site"
            build_site(output)
            report = validate_site(output)
        self.assertEqual("passed", report["status"])
        self.assertEqual(25, report["pages"])


if __name__ == "__main__":
    unittest.main()
