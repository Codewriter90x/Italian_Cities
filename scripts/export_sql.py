#!/usr/bin/env python3
"""Generate a deterministic SQLite-compatible SQL script from the canonical CSV."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from dataset_common import (
    GENERATED_PATHS,
    ITALIAN_LOCATION_FIELDS,
    read_csv_rows,
    record_digest,
)
from project_metadata import DATASET_VERSION, SCHEMA_VERSION, version_number

DEFAULT_OUTPUT = Path("dist") / DATASET_VERSION / "italian_locations.sql"
INSERT_BATCH_SIZE = 250


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--canonical",
        type=Path,
        default=GENERATED_PATHS["italian_locations"],
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def export_sql(rows: list[dict[str, str]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    quoted_fields = ", ".join(f'"{field}"' for field in ITALIAN_LOCATION_FIELDS)
    columns = ",\n    ".join(
        f'"{field}" TEXT NOT NULL' for field in ITALIAN_LOCATION_FIELDS
    )

    with temporary.open("w", encoding="utf-8", newline="\n") as destination:
        destination.write(
            f"-- Italian Cities {DATASET_VERSION}\n"
            "-- Generated from data/italian_locations.csv; do not edit manually.\n"
            "-- SQLite-compatible schema and data. All source columns are TEXT.\n\n"
            "PRAGMA foreign_keys = ON;\n"
            "BEGIN TRANSACTION;\n"
            'CREATE TABLE "italian_locations" (\n'
            f"    {columns},\n"
            '    PRIMARY KEY ("location_postal_id")\n'
            ") WITHOUT ROWID;\n\n"
        )

        for start in range(0, len(rows), INSERT_BATCH_SIZE):
            batch = rows[start : start + INSERT_BATCH_SIZE]
            destination.write(
                f'INSERT INTO "italian_locations" ({quoted_fields}) VALUES\n'
            )
            for index, row in enumerate(batch):
                values = ", ".join(
                    sql_literal(row[field]) for field in ITALIAN_LOCATION_FIELDS
                )
                suffix = ",\n" if index < len(batch) - 1 else ";\n\n"
                destination.write(f"({values}){suffix}")

        destination.write(
            'CREATE INDEX "idx_locations_postal_code" '
            'ON "italian_locations" ("postal_code", "location_id");\n'
            'CREATE INDEX "idx_locations_normalized_name" '
            'ON "italian_locations" ("normalized_name", "location_id");\n'
            'CREATE INDEX "idx_locations_istat_code" '
            'ON "italian_locations" ("municipality_istat_code");\n'
            'CREATE TABLE "_metadata" (\n'
            '    "key" TEXT PRIMARY KEY,\n'
            '    "value" TEXT NOT NULL\n'
            ") WITHOUT ROWID;\n"
            'INSERT INTO "_metadata" ("key", "value") VALUES\n'
            f"('record_digest', {sql_literal(record_digest(rows))}),\n"
            f"('row_count', {sql_literal(str(len(rows)))}),\n"
            f"('schema_version', {sql_literal(SCHEMA_VERSION)}),\n"
            f"('release_version', {sql_literal(DATASET_VERSION)});\n"
            f"PRAGMA user_version = {version_number(SCHEMA_VERSION)};\n"
            "COMMIT;\n"
        )
    os.replace(temporary, output)


def main() -> None:
    args = parse_args()
    rows = read_csv_rows(args.canonical, ITALIAN_LOCATION_FIELDS)
    export_sql(rows, args.output)
    print(f"wrote {args.output} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
