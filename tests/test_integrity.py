from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from dataset_common import (  # noqa: E402
    GENERATED_PATHS,
    ITALIAN_LOCATION_FIELDS,
    LOCALITY_FIELDS,
    MILESTONE1_BASELINE,
    MUNICIPALITY_FIELDS,
    POSTAL_CODE_FIELDS,
    SOURCE_MANIFEST,
    canonical_row_sort_key,
    read_csv_rows,
)
from build_dataset import validate_declared_sources  # noqa: E402
from normalize_legacy import DEFAULT_ISTAT  # noqa: E402
from validate_dataset import validate  # noqa: E402


class IntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.locations = read_csv_rows(
            GENERATED_PATHS["italian_locations"],
            ITALIAN_LOCATION_FIELDS,
        )
        cls.municipalities = read_csv_rows(
            GENERATED_PATHS["municipalities"],
            MUNICIPALITY_FIELDS,
        )
        cls.localities = read_csv_rows(
            GENERATED_PATHS["localities"],
            LOCALITY_FIELDS,
        )
        cls.postal_codes = read_csv_rows(
            GENERATED_PATHS["postal_codes"],
            POSTAL_CODE_FIELDS,
        )

    def test_primary_identifiers_are_unique(self) -> None:
        self.assertEqual(
            len({row["location_id"] for row in self.locations}),
            len(self.locations),
        )
        self.assertEqual(
            len({row["legacy_uuid"] for row in self.locations}),
            len(self.locations),
        )

    def test_partition_counts_reconcile(self) -> None:
        self.assertEqual(len(self.locations), 14_480)
        self.assertEqual(len(self.municipalities), 7_186)
        self.assertEqual(len(self.localities), 7_294)
        self.assertEqual(
            len(self.municipalities) + len(self.localities),
            len(self.locations),
        )

    def test_postal_code_relations_have_no_orphans(self) -> None:
        location_ids = {row["location_id"] for row in self.locations}
        postal_location_ids = {row["location_id"] for row in self.postal_codes}
        self.assertEqual(postal_location_ids, location_ids)
        self.assertEqual(len(self.postal_codes), len(self.locations))

    def test_canonical_order_is_stable(self) -> None:
        self.assertEqual(
            self.locations,
            sorted(self.locations, key=canonical_row_sort_key),
        )

    def test_diff_report_has_no_semantic_changes(self) -> None:
        report = json.loads(
            (ROOT / "reports/milestone2-diff.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            report["record_changes"],
            {
                "added": 0,
                "removed": 0,
                "changed": 0,
                "unchanged": 14_480,
                "added_legacy_uuids": [],
                "removed_legacy_uuids": [],
                "changed_samples": [],
                "samples_truncated": False,
            },
        )

    def test_all_export_formats_are_equivalent(self) -> None:
        report = validate()
        self.assertEqual(report["status"], "passed", report["errors"])
        self.assertTrue(all(report["cross_format_equivalence"].values()))

    def test_source_checksum_gate_rejects_modified_input(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            modified = Path(directory) / "legacy.csv"
            modified.write_text("modified\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                validate_declared_sources(
                    SOURCE_MANIFEST,
                    legacy_path=modified,
                    istat_path=DEFAULT_ISTAT,
                    baseline_path=MILESTONE1_BASELINE,
                )


if __name__ == "__main__":
    unittest.main()
