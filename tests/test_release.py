from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_release import (  # noqa: E402
    CHECKSUM_ASSET,
    RELEASE_ASSETS,
    SQL_ASSET,
    build_release,
)
from dataset_common import (  # noqa: E402
    GENERATED_PATHS,
    ITALIAN_LOCATION_FIELDS,
    read_csv_rows,
    sha256_file,
)
from export_sql import export_sql  # noqa: E402
from validate_release import EXPECTED_ASSETS, validate_release  # noqa: E402


class ReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory()
        cls.release_dir = Path(cls.temporary.name) / "v1.0.0"
        build_release(cls.release_dir)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_release_contains_the_exact_public_assets(self) -> None:
        self.assertEqual(
            {path.name for path in self.release_dir.iterdir()},
            EXPECTED_ASSETS,
        )
        self.assertIn(SQL_ASSET, EXPECTED_ASSETS)
        self.assertIn(CHECKSUM_ASSET, EXPECTED_ASSETS)
        self.assertNotIn("italian Cities.sql", EXPECTED_ASSETS)

    def test_release_copies_generated_outputs_without_changes(self) -> None:
        for name, source in RELEASE_ASSETS.items():
            with self.subTest(name=name):
                self.assertEqual(
                    sha256_file(self.release_dir / name),
                    sha256_file(source),
                )

    def test_release_checksums_and_sql_import_pass(self) -> None:
        report = validate_release(self.release_dir)
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["canonical_rows"], 14_480)
        self.assertEqual(report["sql_import"]["rows"], 14_480)

    def test_sql_export_is_byte_deterministic(self) -> None:
        rows = read_csv_rows(
            GENERATED_PATHS["italian_locations"],
            ITALIAN_LOCATION_FIELDS,
        )
        first = Path(self.temporary.name) / "first.sql"
        second = Path(self.temporary.name) / "second.sql"
        export_sql(rows, first)
        export_sql(rows, second)
        self.assertEqual(sha256_file(first), sha256_file(second))


if __name__ == "__main__":
    unittest.main()
