from __future__ import annotations

import json
import re
import sys
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
    normalize_name,
    read_csv_rows,
)
from validate_dataset import completely_blank_record_lines  # noqa: E402
from validators.formats import load_xlsx_table  # noqa: E402


class SchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.locations = read_csv_rows(
            GENERATED_PATHS["italian_locations"],
            ITALIAN_LOCATION_FIELDS,
        )
        cls.postal_codes = read_csv_rows(
            GENERATED_PATHS["postal_codes"], POSTAL_CODE_FIELDS
        )

    def test_all_declared_csv_schemas(self) -> None:
        for name, fields in (
            ("municipalities", MUNICIPALITY_FIELDS),
            ("localities", LOCALITY_FIELDS),
            ("postal_codes", POSTAL_CODE_FIELDS),
            ("italian_locations", ITALIAN_LOCATION_FIELDS),
        ):
            with self.subTest(name=name):
                rows = read_csv_rows(GENERATED_PATHS[name], fields)
                self.assertTrue(rows)
                self.assertEqual(set(rows[0]), set(fields))

    def test_no_completely_blank_csv_rows(self) -> None:
        for name in GENERATED_PATHS:
            if name in {
                "municipalities",
                "localities",
                "postal_codes",
                "italian_locations",
            }:
                with self.subTest(name=name):
                    self.assertEqual(
                        completely_blank_record_lines(
                            GENERATED_PATHS[name]
                        ),
                        [],
                    )

    def test_normalized_names_are_reproducible(self) -> None:
        for row in self.locations:
            self.assertEqual(
                row["normalized_name"], normalize_name(row["name"])
            )

    def test_normalization_contract(self) -> None:
        for left, right in (
            ("Sant’Agata", "SANT'AGATA"),
            ("Città", "citta"),
            ("  L'Aquila  ", "l aquila"),
        ):
            with self.subTest(left=left):
                self.assertEqual(normalize_name(left), normalize_name(right))

    def test_postal_codes_are_five_digits_or_explicitly_missing(self) -> None:
        self.assertTrue(
            any(
                row["postal_code"].startswith("0")
                for row in self.postal_codes
                if row["postal_code"]
            )
        )
        for row in self.postal_codes:
            if row["postal_code_status"] == "missing":
                self.assertEqual("", row["postal_code"])
            else:
                self.assertRegex(row["postal_code"], r"^\d{5}$")

    def test_reserved_official_statuses_are_unused(self) -> None:
        self.assertFalse(
            {
                row["postal_code_status"] for row in self.postal_codes
            }
            & {"official_verified", "obsolete"}
        )
        self.assertNotIn(
            "official_boundary_derived",
            {
                row["coordinate_verification"]
                for row in self.locations
            },
        )

    def test_json_metadata_is_explicitly_non_official(self) -> None:
        payload = json.loads(
            GENERATED_PATHS["json"].read_text(encoding="utf-8")
        )
        metadata = payload["metadata"]
        self.assertEqual("3.0.0", metadata["schema_version"])
        self.assertEqual(
            "experimental_non_official",
            metadata["operational_data_readiness"],
        )
        self.assertIn("GeoNames", metadata["attribution"]["geonames"])
        self.assertIn("not Poste Italiane", metadata["warning"])
        self.assertTrue(
            all(
                not re.search(r"\blegacy_csv\b", row["source_ids"])
                for row in payload["rows"]
            )
        )

    def test_xlsx_information_sheet_contains_geonames_attribution(self) -> None:
        _, rows = load_xlsx_table(
            GENERATED_PATHS["xlsx"], "Dataset Info"
        )
        values = " ".join(value for row in rows for value in row.values())
        self.assertIn("GeoNames", values)
        self.assertIn("CC BY 4.0", values)
        self.assertIn("not Poste Italiane", values)


if __name__ == "__main__":
    unittest.main()
