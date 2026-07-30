#!/usr/bin/env python3
"""Validate release assets, checksums and the generated SQL import."""

from __future__ import annotations

import argparse
import json
import sqlite3
import tempfile
from pathlib import Path

from build_release import (
    CHECKSUM_ASSET,
    DEFAULT_OUTPUT,
    RELEASE_ASSETS,
    SQL_ASSET,
)
from check_determinism import sqlite_semantic_digest
from dataset_common import (
    GENERATED_PATHS,
    ITALIAN_LOCATION_FIELDS,
    read_csv_rows,
    record_digest,
    sha256_file,
)
from project_metadata import DATASET_VERSION, SCHEMA_VERSION

EXPECTED_ASSETS = {*RELEASE_ASSETS, SQL_ASSET, CHECKSUM_ASSET}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def read_checksums(path: Path) -> dict[str, str]:
    checksums: dict[str, str] = {}
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        parts = line.split("  ", 1)
        if len(parts) != 2 or len(parts[0]) != 64:
            raise ValueError(f"{path}:{line_number}: invalid SHA256SUMS entry")
        checksum, name = parts
        if name in checksums:
            raise ValueError(f"{path}:{line_number}: duplicate checksum for {name}")
        checksums[name] = checksum
    return checksums


def validate_sql_import(path: Path) -> dict[str, object]:
    with tempfile.NamedTemporaryFile(suffix=".sqlite") as handle:
        connection = sqlite3.connect(handle.name)
        try:
            connection.executescript(path.read_text(encoding="utf-8"))
            fields = tuple(
                row[1]
                for row in connection.execute(
                    'PRAGMA table_info("italian_locations")'
                )
            )
            rows = [
                dict(zip(ITALIAN_LOCATION_FIELDS, values, strict=True))
                for values in connection.execute(
                    'SELECT * FROM "italian_locations" '
                    'ORDER BY "normalized_name", "province_code", "postal_code", '
                    '"location_id", "location_postal_id"'
                )
            ]
            metadata = dict(
                connection.execute('SELECT "key", "value" FROM "_metadata"')
            )
        finally:
            connection.close()

    if fields != ITALIAN_LOCATION_FIELDS:
        raise ValueError(f"SQL schema mismatch: {fields}")
    digest = record_digest(rows)
    if metadata.get("record_digest") != digest:
        raise ValueError("SQL metadata record digest is stale")
    if metadata.get("row_count") != str(len(rows)):
        raise ValueError("SQL metadata row count is stale")
    if metadata.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("SQL metadata schema version is stale")
    if metadata.get("release_version") != DATASET_VERSION:
        raise ValueError("SQL metadata release version is stale")
    return {"rows": len(rows), "record_digest": digest}


def validate_release(directory: Path) -> dict[str, object]:
    entries = list(directory.iterdir())
    actual_assets = {path.name for path in entries}
    if actual_assets != EXPECTED_ASSETS:
        raise ValueError(
            f"release asset mismatch: expected {sorted(EXPECTED_ASSETS)}, "
            f"found {sorted(actual_assets)}"
        )
    if any(not path.is_file() for path in entries):
        raise ValueError("release directory must contain files only")

    checksums = read_checksums(directory / CHECKSUM_ASSET)
    checksum_assets = EXPECTED_ASSETS - {CHECKSUM_ASSET}
    if set(checksums) != checksum_assets:
        raise ValueError("SHA256SUMS does not list every release asset exactly once")
    for name, expected in checksums.items():
        actual = sha256_file(directory / name)
        if actual != expected:
            raise ValueError(f"{name}: checksum mismatch {actual} != {expected}")

    for name, source in RELEASE_ASSETS.items():
        if sha256_file(directory / name) != sha256_file(source):
            raise ValueError(f"{name}: release copy differs from generated source")

    canonical_rows = read_csv_rows(
        GENERATED_PATHS["italian_locations"],
        ITALIAN_LOCATION_FIELDS,
    )
    expected_digest = record_digest(canonical_rows)
    sql_result = validate_sql_import(directory / SQL_ASSET)
    if sql_result["record_digest"] != expected_digest:
        raise ValueError("SQL records differ from the canonical CSV")
    sqlite_digest = sqlite_semantic_digest(
        directory / "italian_locations.sqlite"
    )
    if sqlite_digest != expected_digest:
        raise ValueError("release SQLite records differ from the canonical CSV")

    return {
        "status": "passed",
        "release_version": DATASET_VERSION,
        "assets": sorted(EXPECTED_ASSETS),
        "checksums": checksums,
        "canonical_rows": len(canonical_rows),
        "record_digest": expected_digest,
        "sql_import": sql_result,
        "sqlite_record_digest": sqlite_digest,
    }


def main() -> None:
    args = parse_args()
    try:
        report = validate_release(args.directory)
    except (FileNotFoundError, ValueError, sqlite3.DatabaseError) as error:
        report = {"status": "failed", "errors": [str(error)]}
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    if report["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
