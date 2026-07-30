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
    MUNICIPALITY_FIELDS,
    POSTAL_CODE_FIELDS,
    SOURCE_MANIFEST,
    canonical_row_sort_key,
    read_csv_rows,
)
from build_dataset import validate_declared_sources  # noqa: E402
from normalize_legacy import DEFAULT_ISTAT  # noqa: E402
from validate_dataset import validate  # noqa: E402
from check_determinism import (  # noqa: E402
    DEFAULT_REPORT as DETERMINISM_REPORT,
    collect_signatures,
)


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
        self.assertEqual(
            len({row["municipality_id"] for row in self.municipalities}),
            len(self.municipalities),
        )
        self.assertEqual(
            len({row["istat_code"] for row in self.municipalities}),
            len(self.municipalities),
        )
        self.assertEqual(
            len({row["locality_id"] for row in self.localities}),
            len(self.localities),
        )
        self.assertEqual(
            len(
                {
                    (row["location_id"], row["postal_code"])
                    for row in self.postal_codes
                }
            ),
            len(self.postal_codes),
        )

    def test_logical_keys_are_unique_in_every_dataset(self) -> None:
        for name, rows, fields in (
            (
                "municipalities",
                self.municipalities,
                ("normalized_name", "postal_code", "province_code"),
            ),
            (
                "localities",
                self.localities,
                ("normalized_name", "postal_code", "province_code"),
            ),
            (
                "postal_codes",
                self.postal_codes,
                ("location_id", "postal_code", "province_code"),
            ),
            (
                "italian_locations",
                self.locations,
                ("normalized_name", "postal_code", "province_code"),
            ),
        ):
            with self.subTest(name=name):
                keys = [tuple(row[field] for field in fields) for row in rows]
                self.assertEqual(len(keys), len(set(keys)))

    def test_partition_counts_reconcile(self) -> None:
        self.assertTrue(self.locations)
        self.assertTrue(self.municipalities)
        self.assertTrue(self.localities)
        self.assertEqual(
            len(self.municipalities) + len(self.localities),
            len(self.locations),
        )
        self.assertEqual(
            len(self.municipalities),
            sum(row["location_kind"] == "municipality" for row in self.locations),
        )
        self.assertEqual(
            len(self.localities),
            sum(
                row["location_kind"] == "postal_locality_unclassified"
                for row in self.locations
            ),
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

    def test_diff_report_describes_real_release_changes(self) -> None:
        report = json.loads(
            (ROOT / "reports/release-diff.json").read_text(encoding="utf-8")
        )
        self.assertEqual(report["comparison"], {"from": "v1.0.0", "to": "v1.1.0"})
        self.assertEqual(report["record_changes"]["added"], 0)
        self.assertEqual(report["record_changes"]["removed"], 0)
        self.assertGreater(report["record_changes"]["changed"], 0)
        self.assertEqual(
            set(report["schema_changes"]["added_fields"]),
            {
                "postal_code_status",
                "legacy_province_name",
                "coordinate_verification",
                "source_ids",
            },
        )
        self.assertEqual(report["postal_code_status_counts"]["generic_multicap"], 9)

    def test_all_export_formats_are_equivalent(self) -> None:
        report = validate()
        self.assertEqual(report["status"], "passed", report["errors"])
        self.assertTrue(all(report["cross_format_equivalence"].values()))
        self.assertTrue(
            all(
                check["status"] == "passed"
                for check in report["quality_checks"].values()
            ),
            report["quality_checks"],
        )

    def test_istat_and_territorial_quality_gates_pass(self) -> None:
        report = validate()
        for check_name in ("istat_code_validity", "territorial_coherence"):
            with self.subTest(check=check_name):
                self.assertEqual(
                    report["quality_checks"][check_name],
                    {"status": "passed", "violations": 0},
                )

    def test_committed_determinism_report_matches_outputs(self) -> None:
        report = json.loads(DETERMINISM_REPORT.read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["runs"], 2)
        self.assertEqual(report["signatures"], collect_signatures())

    def test_source_checksum_gate_rejects_modified_input(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            modified = Path(directory) / "legacy.csv"
            modified.write_text("modified\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                validate_declared_sources(
                    SOURCE_MANIFEST,
                    legacy_path=modified,
                    istat_path=DEFAULT_ISTAT,
                )


if __name__ == "__main__":
    unittest.main()
