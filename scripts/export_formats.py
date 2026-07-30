#!/usr/bin/env python3
"""Export the clean-room canonical CSV to JSON, XLSX and SQLite."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
import re
import sqlite3
import tempfile
import zipfile
from pathlib import Path

import xlsxwriter

from dataset_common import (
    GENERATED_PATHS,
    ITALIAN_LOCATION_FIELDS,
    REPORTS_DIR,
    ROOT,
    read_csv_rows,
    record_digest,
    sha256_file,
    write_json,
)
from project_metadata import (
    BUILD_DATE,
    DATASET_VERSION,
    OPERATIONAL_DATA_READINESS,
    SCHEMA_VERSION,
    STRUCTURAL_QUALITY,
    version_number,
)


FIXED_XLSX_TIMESTAMP = f"{BUILD_DATE}T00:00:00Z"
DEFAULT_REPORT = REPORTS_DIR / "export-manifest.json"
GEONAMES_ATTRIBUTION = (
    "GeoNames postal code dump — CC BY 4.0 — https://www.geonames.org/"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--canonical",
        type=Path,
        default=GENERATED_PATHS["italian_locations"],
    )
    parser.add_argument("--json", type=Path, default=GENERATED_PATHS["json"])
    parser.add_argument("--xlsx", type=Path, default=GENERATED_PATHS["xlsx"])
    parser.add_argument(
        "--sqlite", type=Path, default=GENERATED_PATHS["sqlite"]
    )
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def export_json(
    rows: list[dict[str, str]],
    canonical_sha256: str,
    path: Path,
) -> None:
    payload = {
        "metadata": {
            "dataset_version": DATASET_VERSION,
            "schema_version": SCHEMA_VERSION,
            "canonical_sha256": canonical_sha256,
            "structural_quality": STRUCTURAL_QUALITY,
            "operational_data_readiness": OPERATIONAL_DATA_READINESS,
            "canonical_source_ids": [
                "istat_municipalities",
                "geonames_postal_codes",
            ],
            "attribution": {
                "istat": (
                    "Istituto nazionale di statistica (ISTAT), CC BY 4.0"
                ),
                "geonames": GEONAMES_ATTRIBUTION,
            },
            "warning": (
                "GeoNames is not Poste Italiane. Postal codes and coordinates "
                "are provided without warranty; coordinates may be estimated."
            ),
        },
        "fields": list(ITALIAN_LOCATION_FIELDS),
        "rows": rows,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def export_sqlite(
    rows: list[dict[str, str]],
    canonical_sha256: str,
    path: Path,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        prefix="italian_locations-",
        suffix=".sqlite",
        dir=path.parent,
        delete=False,
    ) as handle:
        temporary = Path(handle.name)
    try:
        connection = sqlite3.connect(temporary)
        try:
            connection.execute("PRAGMA page_size = 4096")
            connection.execute("PRAGMA journal_mode = OFF")
            connection.execute("PRAGMA synchronous = OFF")
            columns = ", ".join(
                f'"{field}" TEXT NOT NULL'
                for field in ITALIAN_LOCATION_FIELDS
            )
            connection.execute(
                f'CREATE TABLE "italian_locations" ({columns}, '
                'PRIMARY KEY ("location_postal_id")) WITHOUT ROWID'
            )
            placeholders = ", ".join("?" for _ in ITALIAN_LOCATION_FIELDS)
            quoted_fields = ", ".join(
                f'"{field}"' for field in ITALIAN_LOCATION_FIELDS
            )
            connection.executemany(
                f'INSERT INTO "italian_locations" ({quoted_fields}) '
                f"VALUES ({placeholders})",
                [
                    tuple(row[field] for field in ITALIAN_LOCATION_FIELDS)
                    for row in rows
                ],
            )
            connection.execute(
                'CREATE INDEX "idx_locations_postal_code" '
                'ON "italian_locations" ("postal_code", "location_id")'
            )
            connection.execute(
                'CREATE INDEX "idx_locations_normalized_name" '
                'ON "italian_locations" ("normalized_name", "location_id")'
            )
            connection.execute(
                'CREATE INDEX "idx_locations_istat_code" '
                'ON "italian_locations" ("municipality_istat_code")'
            )
            connection.execute(
                'CREATE TABLE "_metadata" '
                '("key" TEXT PRIMARY KEY, "value" TEXT NOT NULL) WITHOUT ROWID'
            )
            metadata = (
                ("canonical_sha256", canonical_sha256),
                ("dataset_version", DATASET_VERSION),
                ("record_digest", record_digest(rows)),
                ("row_count", str(len(rows))),
                ("schema_version", SCHEMA_VERSION),
                ("structural_quality", STRUCTURAL_QUALITY),
                (
                    "operational_data_readiness",
                    OPERATIONAL_DATA_READINESS,
                ),
                ("geonames_attribution", GEONAMES_ATTRIBUTION),
            )
            connection.executemany(
                'INSERT INTO "_metadata" ("key", "value") VALUES (?, ?)',
                metadata,
            )
            connection.execute(
                f"PRAGMA user_version = {version_number(SCHEMA_VERSION)}"
            )
            connection.commit()
            connection.execute("VACUUM")
        finally:
            connection.close()
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def normalize_xlsx_package(path: Path) -> None:
    temporary = path.with_suffix(path.suffix + ".normalized")
    with zipfile.ZipFile(path, "r") as source, zipfile.ZipFile(
        temporary,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as destination:
        for name in sorted(source.namelist()):
            data = source.read(name)
            if name == "docProps/core.xml":
                text = data.decode("utf-8")
                text = re.sub(
                    r"(<dcterms:(?:created|modified)[^>]*>).*?"
                    r"(</dcterms:(?:created|modified)>)",
                    rf"\g<1>{FIXED_XLSX_TIMESTAMP}\g<2>",
                    text,
                )
                data = text.encode("utf-8")
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            destination.writestr(info, data)
    os.replace(temporary, path)


def export_xlsx(
    rows: list[dict[str, str]],
    canonical_sha256: str,
    path: Path,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    workbook = xlsxwriter.Workbook(
        temporary,
        {"constant_memory": True, "in_memory": False},
    )
    workbook.set_properties(
        {
            "title": "Italian Cities v2 clean-room dataset",
            "subject": f"Italian Cities {DATASET_VERSION}",
            "author": "Codewriter90x",
            "comments": "Generated; do not edit manually.",
            "created": datetime.fromisoformat(BUILD_DATE).replace(
                tzinfo=timezone.utc
            ),
        }
    )
    data_sheet = workbook.add_worksheet("Italian Locations")
    info_sheet = workbook.add_worksheet("Dataset Info")
    data_sheet.freeze_panes(1, 3)
    data_sheet.hide_gridlines(2)
    info_sheet.hide_gridlines(2)

    header = workbook.add_format(
        {
            "bold": True,
            "font_color": "#FFFFFF",
            "bg_color": "#0F4C5C",
            "text_wrap": True,
        }
    )
    text = workbook.add_format({"num_format": "@"})
    coordinate = workbook.add_format({"num_format": "0.000000"})
    warning = workbook.add_format(
        {
            "bold": True,
            "font_color": "#7A271A",
            "bg_color": "#FEE4E2",
            "text_wrap": True,
        }
    )
    for column, field in enumerate(ITALIAN_LOCATION_FIELDS):
        data_sheet.write_string(0, column, field, header)
    for row_index, row in enumerate(rows, start=1):
        for column, field in enumerate(ITALIAN_LOCATION_FIELDS):
            value = row[field]
            if field in {"latitude", "longitude"} and value:
                data_sheet.write_number(
                    row_index, column, float(value), coordinate
                )
            else:
                data_sheet.write_string(row_index, column, value, text)
    for column, field in enumerate(ITALIAN_LOCATION_FIELDS):
        data_sheet.set_column(
            column,
            column,
            min(max(len(field) + 2, 14), 34),
        )
    data_sheet.autofilter(
        0, 0, len(rows), len(ITALIAN_LOCATION_FIELDS) - 1
    )

    info_rows = (
        ("Dataset version", DATASET_VERSION),
        ("Schema version", SCHEMA_VERSION),
        ("Canonical CSV SHA-256", canonical_sha256),
        ("Structural quality", STRUCTURAL_QUALITY),
        ("Operational data readiness", OPERATIONAL_DATA_READINESS),
        ("ISTAT attribution", "ISTAT municipality registry — CC BY 4.0"),
        ("GeoNames attribution", GEONAMES_ATTRIBUTION),
        (
            "Important warning",
            "GeoNames is not Poste Italiane. CAP and coordinates are "
            "non-official, without warranty; coordinates may be estimated.",
        ),
        (
            "Legacy role",
            "Historical comparison only; no legacy row contributes to v2.",
        ),
    )
    for row_index, (label, value) in enumerate(info_rows):
        cell_format = warning if label == "Important warning" else None
        info_sheet.write(row_index, 0, label, cell_format)
        info_sheet.write(row_index, 1, value, cell_format)
    info_sheet.set_column("A:A", 30)
    info_sheet.set_column("B:B", 100)
    workbook.close()
    os.replace(temporary, path)
    normalize_xlsx_package(path)


def export_all(
    *,
    canonical_path: Path = GENERATED_PATHS["italian_locations"],
    json_path: Path = GENERATED_PATHS["json"],
    xlsx_path: Path = GENERATED_PATHS["xlsx"],
    sqlite_path: Path = GENERATED_PATHS["sqlite"],
    report_path: Path = DEFAULT_REPORT,
) -> dict[str, object]:
    rows = read_csv_rows(canonical_path, ITALIAN_LOCATION_FIELDS)
    canonical_sha256 = sha256_file(canonical_path)
    export_json(rows, canonical_sha256, json_path)
    export_sqlite(rows, canonical_sha256, sqlite_path)
    export_xlsx(rows, canonical_sha256, xlsx_path)
    semantic_digest = record_digest(rows)
    report = {
        "status": "exported",
        "schema_version": SCHEMA_VERSION,
        "structural_quality": STRUCTURAL_QUALITY,
        "operational_data_readiness": OPERATIONAL_DATA_READINESS,
        "rows": len(rows),
        "record_digest": semantic_digest,
        "outputs": {
            name: {
                "repository_path": str(path.relative_to(ROOT)),
                "sha256": sha256_file(path),
            }
            for name, path in (
                ("csv", canonical_path),
                ("json", json_path),
                ("xlsx", xlsx_path),
            )
        },
    }
    # SQLite database bytes can differ across SQLite library versions even
    # when tables, metadata and row order are identical. Keep the committed
    # manifest portable by recording its canonical record digest instead.
    report["outputs"]["sqlite"] = {
        "repository_path": str(sqlite_path.relative_to(ROOT)),
        "semantic_sha256": semantic_digest,
    }
    write_json(report_path, report)
    return report


def main() -> None:
    args = parse_args()
    report = export_all(
        canonical_path=args.canonical,
        json_path=args.json,
        xlsx_path=args.xlsx,
        sqlite_path=args.sqlite,
        report_path=args.report,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
