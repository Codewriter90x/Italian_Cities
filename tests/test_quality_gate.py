from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_dataset import (  # noqa: E402
    QUALITY_CHECK_NAMES,
    completely_blank_record_lines,
    territorial_names_compatible,
    validate_coordinate_table,
    validate_logical_key,
    validate_postal_code_table,
    validate_unique_key,
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
        self.assertEqual(checks["unique_identifiers"]["violations"], 1)
        self.assertIn("duplicate identifier", errors[0])

    def test_invalid_cap_is_rejected(self) -> None:
        errors: list[str] = []
        checks = empty_checks()
        validate_postal_code_table(
            rows=[{"postal_code": "1234"}],
            dataset="fixture.csv",
            errors=errors,
            checks=checks,
        )
        self.assertEqual(checks["postal_code_format"]["violations"], 1)
        self.assertIn("exactly five digits", errors[0])

    def test_duplicate_logical_key_is_rejected(self) -> None:
        errors: list[str] = []
        checks = empty_checks()
        rows = [
            {"name": "roma", "cap": "00100"},
            {"name": "roma", "cap": "00100"},
        ]
        validate_logical_key(
            rows=rows,
            fields=("name", "cap"),
            dataset="fixture.csv",
            errors=errors,
            checks=checks,
        )
        self.assertEqual(checks["no_logical_duplicates"]["violations"], 1)
        self.assertIn("duplicate logical key", errors[0])

    def test_non_numeric_and_implausible_coordinates_are_rejected(self) -> None:
        errors: list[str] = []
        checks = empty_checks()
        validate_coordinate_table(
            rows=[
                {"latitude": "north", "longitude": "12"},
                {"latitude": "90", "longitude": "12"},
            ],
            dataset="fixture.csv",
            errors=errors,
            checks=checks,
        )
        self.assertEqual(checks["numeric_coordinates"]["violations"], 1)
        self.assertEqual(checks["coordinate_bounds"]["violations"], 1)

    def test_physical_and_delimiter_only_blank_rows_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.csv"
            path.write_text("a,b\n1,2\n\n,\n", encoding="utf-8")
            self.assertEqual(completely_blank_record_lines(path), [3, 4])

    def test_official_bilingual_region_suffix_is_compatible(self) -> None:
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
