from __future__ import annotations

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


class SchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.locations = read_csv_rows(
            GENERATED_PATHS["italian_locations"],
            ITALIAN_LOCATION_FIELDS,
        )

    def test_all_declared_csv_schemas(self) -> None:
        contracts = (
            ("municipalities", MUNICIPALITY_FIELDS),
            ("localities", LOCALITY_FIELDS),
            ("postal_codes", POSTAL_CODE_FIELDS),
            ("italian_locations", ITALIAN_LOCATION_FIELDS),
        )
        for name, fields in contracts:
            with self.subTest(name=name):
                rows = read_csv_rows(GENERATED_PATHS[name], fields)
                self.assertTrue(rows)

    def test_normalized_names_are_reproducible(self) -> None:
        for row in self.locations:
            self.assertEqual(row["normalized_name"], normalize_name(row["name"]))

    def test_normalization_contract(self) -> None:
        equivalents = (
            ("Sant’Agata", "SANT'AGATA"),
            ("Città", "citta"),
            ("  L'Aquila  ", "l aquila"),
        )
        for left, right in equivalents:
            with self.subTest(left=left, right=right):
                self.assertEqual(normalize_name(left), normalize_name(right))

    def test_postal_codes_remain_five_character_strings(self) -> None:
        codes = [row["postal_code"] for row in self.locations]
        self.assertTrue(any(code.startswith("0") for code in codes))
        self.assertTrue(all(re.fullmatch(r"\d{5}", code) for code in codes))

    def test_no_literal_null_values(self) -> None:
        self.assertFalse(
            any(
                value.strip().casefold() == "null"
                for row in self.locations
                for value in row.values()
            )
        )


if __name__ == "__main__":
    unittest.main()
