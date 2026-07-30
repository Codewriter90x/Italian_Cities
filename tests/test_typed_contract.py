from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from dataset_common import GENERATED_PATHS  # noqa: E402
from export_typed_json import (  # noqa: E402
    export_typed_json,
    export_typed_sqlite,
)


class TypedContractTests(unittest.TestCase):
    def test_preview_uses_numbers_and_null_without_changing_v2(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "typed.json"
            export_typed_json(GENERATED_PATHS["italian_locations"], output)
            payload = json.loads(output.read_text(encoding="utf-8"))
        rows = payload["rows"]
        present = next(row for row in rows if row["latitude"] is not None)
        missing = next(row for row in rows if row["latitude"] is None)
        self.assertIsInstance(present["latitude"], float)
        self.assertIsInstance(present["longitude"], float)
        self.assertIsInstance(present["coordinate_accuracy"], int)
        self.assertIsNone(missing["longitude"])
        self.assertIsNone(missing["coordinate_accuracy"])
        self.assertEqual("4.0.0", payload["metadata"]["schema_version"])

    def test_typed_sqlite_preview_uses_real_integer_and_null(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "typed.sqlite"
            export_typed_sqlite(
                GENERATED_PATHS["italian_locations"],
                output,
            )
            connection = sqlite3.connect(output)
            try:
                types = connection.execute(
                    'SELECT typeof(latitude), typeof(longitude), '
                    'typeof(coordinate_accuracy) '
                    'FROM "italian_locations" '
                    'WHERE latitude IS NOT NULL LIMIT 1'
                ).fetchone()
                missing = connection.execute(
                    'SELECT latitude, longitude, coordinate_accuracy '
                    'FROM "italian_locations" '
                    'WHERE coordinate_verification = "missing" LIMIT 1'
                ).fetchone()
            finally:
                connection.close()
        self.assertEqual(("real", "real", "integer"), types)
        self.assertEqual((None, None, None), missing)


if __name__ == "__main__":
    unittest.main()
