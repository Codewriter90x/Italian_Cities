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
    read_csv_rows,
)


BROVELLO_UUID = "a8aec4c6-ab9e-49ae-becf-fd111125f56a"


class CoordinateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.locations = read_csv_rows(
            GENERATED_PATHS["italian_locations"],
            ITALIAN_LOCATION_FIELDS,
        )

    def test_coordinate_status_counts(self) -> None:
        counts = Counter(row["coordinate_status"] for row in self.locations)
        self.assertEqual(set(counts), {"available", "missing", "corrected"})
        self.assertEqual(sum(counts.values()), len(self.locations))
        self.assertEqual(counts["corrected"], 1)

    def test_coordinate_verification_is_honest(self) -> None:
        counts = Counter(
            row["coordinate_verification"] for row in self.locations
        )
        self.assertEqual(
            counts["missing"],
            sum(row["coordinate_status"] == "missing" for row in self.locations),
        )
        self.assertEqual(
            counts["legacy_unverified"],
            sum(row["coordinate_status"] == "available" for row in self.locations),
        )
        self.assertEqual(
            counts["corrected_legacy_unverified"],
            sum(row["coordinate_status"] == "corrected" for row in self.locations),
        )
        self.assertNotIn("verified", counts)

    def test_coordinates_are_complete_pairs(self) -> None:
        for row in self.locations:
            self.assertEqual(bool(row["latitude"]), bool(row["longitude"]))
            if row["coordinate_status"] == "missing":
                self.assertEqual(row["latitude"], "")
                self.assertEqual(row["longitude"], "")

    def test_coordinates_are_numeric_and_within_broad_italy_bounds(self) -> None:
        for row in self.locations:
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

    def test_brovello_correction_is_preserved(self) -> None:
        row = next(
            row for row in self.locations if row["legacy_uuid"] == BROVELLO_UUID
        )
        self.assertEqual(row["name"], "Brovello Carpugnino")
        self.assertEqual(row["longitude"], "8.539621684096616")
        self.assertEqual(row["coordinate_status"], "corrected")
        self.assertEqual(
            row["coordinate_verification"],
            "corrected_legacy_unverified",
        )


if __name__ == "__main__":
    unittest.main()
