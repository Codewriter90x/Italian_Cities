from __future__ import annotations

import inspect
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_dataset import build_clean_room  # noqa: E402
from check_determinism import (  # noqa: E402
    DEFAULT_REPORT as DETERMINISM_REPORT,
    collect_signatures,
)
from dataset_common import (  # noqa: E402
    GENERATED_PATHS,
    ITALIAN_LOCATION_FIELDS,
    LOCALITY_FIELDS,
    MUNICIPALITY_FIELDS,
    POSTAL_CODE_FIELDS,
    canonical_row_sort_key,
    read_csv_rows,
)
from legacy_comparison import build_legacy_comparison  # noqa: E402
from source_data import (  # noqa: E402
    DEFAULT_GEONAMES,
    DEFAULT_LEGACY,
    load_istat_records,
    load_manifest,
    validate_declared_sources,
)
from validate_dataset import validate  # noqa: E402


class IntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.locations = read_csv_rows(
            GENERATED_PATHS["italian_locations"],
            ITALIAN_LOCATION_FIELDS,
        )
        cls.municipalities = read_csv_rows(
            GENERATED_PATHS["municipalities"], MUNICIPALITY_FIELDS
        )
        cls.localities = read_csv_rows(
            GENERATED_PATHS["localities"], LOCALITY_FIELDS
        )
        cls.postal_codes = read_csv_rows(
            GENERATED_PATHS["postal_codes"], POSTAL_CODE_FIELDS
        )

    def test_municipality_count_equals_istat_snapshot(self) -> None:
        official = load_istat_records()
        self.assertEqual(7894, len(official))
        self.assertEqual(len(official), len(self.municipalities))
        self.assertEqual(
            {row["istat_code"] for row in official},
            {row["istat_code"] for row in self.municipalities},
        )

    def test_identifiers_and_logical_relations_are_unique(self) -> None:
        contracts = (
            (self.municipalities, "municipality_id"),
            (self.municipalities, "istat_code"),
            (self.localities, "locality_id"),
            (self.postal_codes, "postal_code_relation_id"),
            (self.locations, "location_postal_id"),
        )
        for rows, field in contracts:
            values = [row[field] for row in rows]
            self.assertEqual(len(values), len(set(values)), field)
        keys = [
            (row["location_id"], row["postal_code"])
            for row in self.postal_codes
        ]
        self.assertEqual(len(keys), len(set(keys)))

    def test_all_municipalities_exist_even_without_postal_code(self) -> None:
        relation_locations = {
            row["location_id"] for row in self.postal_codes
        }
        self.assertTrue(
            {
                row["municipality_id"] for row in self.municipalities
            }.issubset(relation_locations)
        )
        missing = [
            row
            for row in self.postal_codes
            if row["postal_code_status"] == "missing"
        ]
        self.assertEqual(396, len(missing))
        self.assertTrue(all(row["location_kind"] == "municipality" for row in missing))

    def test_ambiguous_matches_are_never_promoted(self) -> None:
        ambiguous = [
            row
            for row in self.locations
            if row["reconciliation_outcome"] == "multiple_candidates"
        ]
        for row in ambiguous:
            self.assertEqual("geonames_ambiguous", row["location_kind"])
            self.assertFalse(row["parent_municipality_id"])
            self.assertTrue(row["candidate_municipality_ids"])
            self.assertFalse(row["municipality_istat_code"])

    def test_canonical_data_has_only_declared_clean_room_sources(self) -> None:
        manifest = load_manifest()
        declared = set(manifest["canonical_source_ids"])
        self.assertEqual(
            {"istat_municipalities", "geonames_postal_codes"}, declared
        )
        for row in self.locations:
            source_ids = set(row["source_ids"].split(";"))
            self.assertTrue(source_ids.issubset(declared))
            self.assertNotIn("legacy_csv", source_ids)

    def test_clean_room_builder_has_no_legacy_input(self) -> None:
        self.assertNotIn("legacy", inspect.signature(build_clean_room).parameters)
        first = build_clean_room()["canonical_source_digest"]
        with tempfile.TemporaryDirectory() as directory:
            unrelated_legacy = Path(directory) / "legacy.csv"
            unrelated_legacy.write_text("completely different\n", encoding="utf-8")
            second = build_clean_room()["canonical_source_digest"]
        self.assertEqual(first, second)

    def test_source_checksum_gate_rejects_modified_geonames(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            modified = Path(directory) / "IT.zip"
            modified.write_bytes(DEFAULT_GEONAMES.read_bytes() + b"modified")
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                validate_declared_sources(geonames_path=modified)

    def test_legacy_report_is_deterministic_and_investigative(self) -> None:
        first = build_legacy_comparison(DEFAULT_LEGACY, self.locations)
        second = build_legacy_comparison(DEFAULT_LEGACY, self.locations)
        self.assertEqual(first, second)
        self.assertEqual("historical_comparison_only", first["legacy_role"])
        self.assertIn("not proof", first["provenance_warning"])

    def test_canonical_order_and_cross_table_integrity(self) -> None:
        self.assertEqual(
            self.locations,
            sorted(self.locations, key=canonical_row_sort_key),
        )
        self.assertEqual(
            {
                row["postal_code_relation_id"] for row in self.postal_codes
            },
            {row["location_postal_id"] for row in self.locations},
        )

    def test_all_formats_and_quality_gates_pass(self) -> None:
        report = validate()
        self.assertEqual("passed", report["structural_quality"], report["errors"])
        self.assertEqual(
            "experimental_non_official",
            report["operational_data_readiness"],
        )
        self.assertNotIn("status", report)
        self.assertTrue(all(report["cross_format_equivalence"].values()))
        self.assertTrue(
            all(
                check["status"] == "passed"
                for check in report["quality_checks"].values()
            )
        )

    def test_committed_determinism_report_matches_outputs(self) -> None:
        report = json.loads(DETERMINISM_REPORT.read_text(encoding="utf-8"))
        self.assertEqual("passed", report["status"])
        self.assertEqual(2, report["runs"])
        self.assertEqual(report["signatures"], collect_signatures())


if __name__ == "__main__":
    unittest.main()
