from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_dataset import (  # noqa: E402
    QUALITY_CHECK_NAMES,
    analyze_coordinate_distribution,
    completely_blank_record_lines,
    territorial_names_compatible,
    validate_coordinate_table,
    validate_logical_key,
    validate_postal_code_table,
    validate_postal_semantics,
    validate_unique_key,
    validate_verification_and_provenance,
)


def empty_checks() -> dict[str, dict[str, object]]:
    return {
        name: {"status": "passed", "violations": 0}
        for name in QUALITY_CHECK_NAMES
    }


class QualityGateNegativeTests(unittest.TestCase):
    def test_duplicate_identifier_is_rejected(self) -> None:
        errors: list[str] = []
        checks = empty_checks()
        validate_unique_key(
            rows=[{"id": "same"}, {"id": "same"}],
            fields=("id",),
            dataset="fixture.csv",
            errors=errors,
            checks=checks,
        )
        self.assertEqual(1, checks["unique_identifiers"]["violations"])

    def test_empty_identifier_is_rejected(self) -> None:
        errors: list[str] = []
        checks = empty_checks()
        validate_unique_key(
            rows=[{"id": ""}],
            fields=("id",),
            dataset="fixture.csv",
            errors=errors,
            checks=checks,
        )
        self.assertIn("empty identifier", errors[0])

    def test_invalid_and_inconsistent_cap_are_rejected(self) -> None:
        errors: list[str] = []
        checks = empty_checks()
        validate_postal_code_table(
            rows=[
                {"postal_code": "1234", "postal_code_status": "geonames_matched"},
                {"postal_code": "00100", "postal_code_status": "missing"},
            ],
            dataset="fixture.csv",
            errors=errors,
            checks=checks,
        )
        self.assertEqual(1, checks["postal_code_format"]["violations"])
        self.assertEqual(1, checks["postal_code_semantics"]["violations"])

    def test_reserved_and_unknown_postal_statuses_are_rejected(self) -> None:
        errors: list[str] = []
        checks = empty_checks()
        validate_postal_semantics(
            rows=[
                {"postal_code_status": "official_verified"},
                {"postal_code_status": "made_up"},
            ],
            dataset="fixture.csv",
            errors=errors,
            checks=checks,
        )
        self.assertEqual(2, checks["postal_code_semantics"]["violations"])

    def test_duplicate_logical_key_is_rejected(self) -> None:
        errors: list[str] = []
        checks = empty_checks()
        validate_logical_key(
            rows=[
                {"name": "roma", "cap": "00100"},
                {"name": "roma", "cap": "00100"},
            ],
            fields=("name", "cap"),
            dataset="fixture.csv",
            errors=errors,
            checks=checks,
        )
        self.assertEqual(1, checks["no_logical_duplicates"]["violations"])

    def test_bad_coordinates_and_accuracy_are_rejected(self) -> None:
        errors: list[str] = []
        checks = empty_checks()
        validate_coordinate_table(
            rows=[
                {
                    "latitude": "north",
                    "longitude": "12",
                    "coordinate_verification": "geonames_estimated",
                    "coordinate_accuracy": "4",
                },
                {
                    "latitude": "90",
                    "longitude": "12",
                    "coordinate_verification": "geonames_estimated",
                    "coordinate_accuracy": "4",
                },
                {
                    "latitude": "42",
                    "longitude": "13",
                    "coordinate_verification": "official_boundary_derived",
                    "coordinate_accuracy": "",
                },
            ],
            dataset="fixture.csv",
            errors=errors,
            checks=checks,
        )
        self.assertEqual(1, checks["numeric_coordinates"]["violations"])
        self.assertEqual(1, checks["coordinate_bounds"]["violations"])
        self.assertGreaterEqual(
            checks["coordinate_verification"]["violations"], 1
        )

    def test_missing_coordinate_contract_is_enforced(self) -> None:
        errors: list[str] = []
        checks = empty_checks()
        validate_coordinate_table(
            rows=[
                {
                    "latitude": "",
                    "longitude": "",
                    "coordinate_verification": "geonames_estimated",
                    "coordinate_accuracy": "4",
                }
            ],
            dataset="fixture.csv",
            errors=errors,
            checks=checks,
        )
        self.assertEqual(1, checks["coordinate_verification"]["violations"])

    def test_shared_coordinate_groups_are_profiled_at_location_grain(self) -> None:
        report = analyze_coordinate_distribution(
            [
                {
                    "location_id": "IT-COM-000001",
                    "name": "Uno",
                    "location_kind": "municipality",
                    "province_code": "AA",
                    "region_name": "Regione",
                    "latitude": "41.0",
                    "longitude": "12.0",
                    "coordinate_verification": "geonames_place_match",
                },
                {
                    "location_id": "IT-COM-000001",
                    "name": "Uno",
                    "location_kind": "municipality",
                    "province_code": "AA",
                    "region_name": "Regione",
                    "latitude": "41.0",
                    "longitude": "12.0",
                    "coordinate_verification": "geonames_place_match",
                },
                {
                    "location_id": "IT-COM-000002",
                    "name": "Due",
                    "location_kind": "municipality",
                    "province_code": "AA",
                    "region_name": "Regione",
                    "latitude": "41.0",
                    "longitude": "12.0",
                    "coordinate_verification": "geonames_place_match",
                },
            ]
        )
        self.assertEqual(1, report["exact_shared_coordinate_groups"])
        self.assertEqual(2, report["locations_in_shared_coordinate_groups"])
        self.assertEqual(2, report["largest_shared_coordinate_group"])

    def test_legacy_and_ambiguous_promotion_are_rejected(self) -> None:
        errors: list[str] = []
        checks = empty_checks()
        validate_verification_and_provenance(
            rows=[
                {
                    "source_ids": "legacy_csv",
                    "source_record_ids": "legacy-1",
                    "reconciliation_outcome": "multiple_candidates",
                    "parent_municipality_id": "IT-COM-000001",
                    "candidate_municipality_ids": "",
                }
            ],
            dataset="fixture.csv",
            errors=errors,
            checks=checks,
        )
        self.assertGreaterEqual(
            checks["provenance_completeness"]["violations"], 2
        )
        self.assertGreaterEqual(checks["clean_room_isolation"]["violations"], 2)

    def test_blank_rows_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.csv"
            path.write_text("a,b\n1,2\n\n,\n", encoding="utf-8")
            self.assertEqual([3, 4], completely_blank_record_lines(path))

    def test_territorial_alias_and_bilingual_suffix(self) -> None:
        self.assertTrue(territorial_names_compatible("Abruzzi", "Abruzzo"))
        self.assertTrue(
            territorial_names_compatible(
                "Trentino-Alto Adige",
                "Trentino-Alto Adige/Südtirol",
            )
        )
        self.assertFalse(
            territorial_names_compatible("Piemonte", "Lombardia")
        )


if __name__ == "__main__":
    unittest.main()
