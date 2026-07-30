#!/usr/bin/env python3
"""Build the opt-in typed JSON contract planned for the next major release."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

from dataset_common import (
    GENERATED_PATHS,
    ITALIAN_LOCATION_FIELDS,
    read_csv_rows,
    write_json,
)
from project_metadata import DATASET_VERSION
from typed_contract import (
    TYPED_CONTRACT_VERSION,
    sqlite_column_definition,
    typed_row,
)


def export_typed_json(canonical: Path, output: Path) -> dict[str, object]:
    rows = read_csv_rows(canonical, ITALIAN_LOCATION_FIELDS)
    payload = {
        "metadata": {
            "source_dataset_version": DATASET_VERSION,
            "schema_version": TYPED_CONTRACT_VERSION,
            "contract_status": "next_major_preview",
            "null_policy": "JSON null for missing numeric values",
        },
        "fields": list(ITALIAN_LOCATION_FIELDS),
        "rows": [typed_row(row) for row in rows],
    }
    write_json(output, payload)
    return {
        "status": "exported",
        "schema_version": TYPED_CONTRACT_VERSION,
        "rows": len(rows),
        "output": str(output),
    }


def export_typed_sqlite(canonical: Path, output: Path) -> dict[str, object]:
    rows = read_csv_rows(canonical, ITALIAN_LOCATION_FIELDS)
    output.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(output)
    try:
        columns = ", ".join(
            sqlite_column_definition(field)
            for field in ITALIAN_LOCATION_FIELDS
        )
        connection.execute(
            f'CREATE TABLE "italian_locations" ({columns}, '
            'PRIMARY KEY ("location_postal_id")) WITHOUT ROWID'
        )
        quoted_fields = ", ".join(
            f'"{field}"' for field in ITALIAN_LOCATION_FIELDS
        )
        placeholders = ", ".join("?" for _ in ITALIAN_LOCATION_FIELDS)
        converted_rows = [typed_row(row) for row in rows]
        connection.executemany(
            f'INSERT INTO "italian_locations" ({quoted_fields}) '
            f"VALUES ({placeholders})",
            [
                tuple(row[field] for field in ITALIAN_LOCATION_FIELDS)
                for row in converted_rows
            ],
        )
        connection.commit()
    finally:
        connection.close()
    return {
        "status": "exported",
        "schema_version": TYPED_CONTRACT_VERSION,
        "rows": len(rows),
        "output": str(output),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--canonical",
        type=Path,
        default=GENERATED_PATHS["italian_locations"],
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--sqlite-output",
        type=Path,
        help="Optional typed SQLite preview output.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report: dict[str, object] = {
        "json": export_typed_json(args.canonical, args.output)
    }
    if args.sqlite_output:
        report["sqlite"] = export_typed_sqlite(
            args.canonical,
            args.sqlite_output,
        )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
