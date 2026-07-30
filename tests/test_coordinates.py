from __future__ import annotations

import math
import sys
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from dataset_common import (  # noqa: E402
    GENERATED_PATHS,
    ITALIAN_LOCATION_FIELDS,
    POSTAL_CODE_FIELDS,
    read_csv_rows,
)
from source_data import load_geonames_records  # noqa: E402


class CoordinateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.locations = read_csv_rows(
            GENERATED_PATHS["italian_locations"],
            ITALIAN_LOCATION_FIELDS,
        )
        cls.postal_codes = read_csv_rows(
            GENERATED_PATHS["postal_codes"], POSTAL_CODE_FIELDS
        )

    def test_coordinate_verification_is_honest(self) -> None:
        counts = Counter(
            row["coordinate_verification"] for row in self.locations
        )
        self.assertEqual(
            set(counts),
            {"geonames_estimated", "geonames_place_match", "missing"},
        )
        self.assertNotIn("official_boundary_derived", counts)
        for row in self.locations:
            if row["coordinate_verification"] == "missing":
                self.assertEqual(("", ""), (row["latitude"], row["longitude"]))
            else:
                self.assertIn(row["coordinate_accuracy"], set("123456"))

    def test_coordinates_are_numeric_and_plausible(self) -> None:
        for row in self.locations:
            self.assertEqual(bool(row["latitude"]), bool(row["longitude"]))
            if not row["latitude"]:
                continue
            latitude = float(row["latitude"])
            longitude = float(row["longitude"])
            self.assertTrue(math.isfinite(latitude))
            self.assertTrue(math.isfinite(longitude))
            self.assertGreaterEqual(latitude, 35)
            self.assertLessEqual(latitude, 48)
            self.assertGreaterEqual(longitude, 6)
            self.assertLessEqual(longitude, 19)

    def test_postal_relation_accuracy_is_preserved(self) -> None:
        source = {
            row["source_record_id"]: row for row in load_geonames_records()
        }
        for relation in self.postal_codes:
            if relation["source_id"] != "geonames_postal_codes":
                self.assertEqual("", relation["accuracy"])
                continue
            records = [
                source[source_id]
                for source_id in relation["source_record_ids"].split(";")
            ]
            expected = max(
                (row["accuracy"] for row in records),
                key=lambda value: int(value or "0"),
            )
            self.assertEqual(expected, relation["accuracy"])


if __name__ == "__main__":
    unittest.main()
