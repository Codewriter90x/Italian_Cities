from __future__ import annotations

import hashlib
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
)
from check_determinism import (
    collect_signatures,
)
from dataset_common import (  # noqa: E402
    GENERATED_PATHS,
    ITALIAN_LOCATION_FIELDS,
    LOCALITY_FIELDS,
    MUNICIPALITY_FIELDS,
    POSTAL_CODE_FIELDS,
    REPORTS_DIR,
    canonical_row_sort_key,
    read_csv_rows,
    record_digest,
)
from reconciliation_backlog import build_backlog  # noqa: E402
from source_data import (  # noqa: E402
    DEFAULT_GEONAMES,
    DEFAULT_ISTAT_REGIONS,
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

    def test_clean_room_builder_is_independent_from_withdrawn_material(self) -> None:
        first = build_clean_room()["canonical_source_digest"]
        with tempfile.TemporaryDirectory() as directory:
            unrelated = Path(directory) / "withdrawn.csv"
            unrelated.write_text("unrelated historical bytes\n", encoding="utf-8")
            second = build_clean_room()["canonical_source_digest"]
        self.assertEqual(first, second)

    def test_source_checksum_gate_rejects_modified_geonames(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            modified = Path(directory) / "IT.zip"
            modified.write_bytes(DEFAULT_GEONAMES.read_bytes() + b"modified")
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                validate_declared_sources(geonames_path=modified)

    def test_geographic_source_is_declared_and_checksum_gated(self) -> None:
        manifest = validate_declared_sources()
        source = next(
            item
            for item in manifest["sources"]
            if item["id"] == "istat_region_boundaries"
        )
        self.assertFalse(source["canonical_input"])
        self.assertEqual(
            source["sha256"],
            hashlib.sha256(DEFAULT_ISTAT_REGIONS.read_bytes()).hexdigest(),
        )

    def test_withdrawn_material_is_not_distributed(self) -> None:
        forbidden_paths = (
            ROOT / "legacy",
            ROOT / "reports/legacy-comparison.json",
            ROOT / "baselines/releases/v1.0.0",
            ROOT / "baselines/releases/v1.1.0",
        )
        self.assertTrue(all(not path.exists() for path in forbidden_paths))

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
        blocking_checks = [
            check
            for check in report["quality_checks"].values()
            if check.get("blocking", True)
        ]
        self.assertTrue(
            all(check["status"] == "passed" for check in blocking_checks)
        )
        distribution = report["coordinate_distribution"]
        self.assertGreater(
            distribution["largest_shared_coordinate_group"],
            distribution["review_threshold"],
        )
        self.assertGreater(distribution["groups_requiring_review"], 0)

    def test_committed_determinism_report_matches_outputs(self) -> None:
        report = json.loads(DETERMINISM_REPORT.read_text(encoding="utf-8"))
        self.assertEqual("passed", report["status"])
        self.assertEqual(2, report["runs"])
        self.assertEqual(report["signatures"], collect_signatures())

    def test_export_manifest_uses_semantic_sqlite_digest(self) -> None:
        report = json.loads(
            (REPORTS_DIR / "export-manifest.json").read_text(encoding="utf-8")
        )
        sqlite_output = report["outputs"]["sqlite"]
        self.assertNotIn("sha256", sqlite_output)
        self.assertEqual(
            record_digest(self.locations),
            sqlite_output["semantic_sha256"],
        )

    def test_reconciliation_backlog_is_evidence_first(self) -> None:
        report = build_backlog(self.municipalities, self.localities)
        self.assertEqual(10270, report["summary"]["unreconciled_localities"])
        self.assertEqual(
            396,
            report["summary"]["municipalities_without_geonames_postal_match"],
        )
        self.assertIn(
            "SU",
            report["summary"]["noncurrent_source_province_codes"],
        )
        self.assertFalse(report["policy"]["automatic_fuzzy_promotion"])


if __name__ == "__main__":
    unittest.main()
