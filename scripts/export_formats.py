#!/usr/bin/env python3
"""Export the canonical CSV to JSON, XLSX and SQLite without manual edits."""

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
from xlsxwriter.utility import xl_col_to_name

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
    SCHEMA_VERSION,
    version_number,
)


FIXED_XLSX_TIMESTAMP = f"{BUILD_DATE}T00:00:00Z"
DEFAULT_REPORT = REPORTS_DIR / "export-manifest.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--canonical", type=Path, default=GENERATED_PATHS["italian_locations"])
    parser.add_argument("--json", type=Path, default=GENERATED_PATHS["json"])
    parser.add_argument("--xlsx", type=Path, default=GENERATED_PATHS["xlsx"])
    parser.add_argument("--sqlite", type=Path, default=GENERATED_PATHS["sqlite"])
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def export_json(rows: list[dict[str, str]], canonical_sha256: str, path: Path) -> None:
    payload = {
        "schema_version": SCHEMA_VERSION,
        "canonical_sha256": canonical_sha256,
        "fields": list(ITALIAN_LOCATION_FIELDS),
        "rows": rows,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
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
            columns = ", ".join(f'"{field}" TEXT NOT NULL' for field in ITALIAN_LOCATION_FIELDS)
            connection.execute(
                f'CREATE TABLE "italian_locations" ({columns}, '
                'PRIMARY KEY ("location_id")) WITHOUT ROWID'
            )
            placeholders = ", ".join("?" for _ in ITALIAN_LOCATION_FIELDS)
            quoted_fields = ", ".join(f'"{field}"' for field in ITALIAN_LOCATION_FIELDS)
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
                'CREATE TABLE "_metadata" ("key" TEXT PRIMARY KEY, "value" TEXT NOT NULL) '
                "WITHOUT ROWID"
            )
            connection.executemany(
                'INSERT INTO "_metadata" ("key", "value") VALUES (?, ?)',
                (
                    ("canonical_sha256", canonical_sha256),
                    ("record_digest", record_digest(rows)),
                    ("row_count", str(len(rows))),
                    ("schema_version", SCHEMA_VERSION),
                ),
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
    """Make ZIP metadata and workbook timestamps deterministic."""

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
                    r"(<dcterms:(?:created|modified)[^>]*>).*?(</dcterms:(?:created|modified)>)",
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
    xlsx_path: Path,
) -> None:
    xlsx_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = xlsx_path.with_suffix(xlsx_path.suffix + ".tmp")
    workbook = xlsxwriter.Workbook(
        temporary,
        {"constant_memory": True, "in_memory": False},
    )
    workbook.set_properties(
        {
            "title": "Italian Cities — Generated Dataset",
            "subject": f"Italian Cities {DATASET_VERSION} canonical locations",
            "author": "Codewriter90x",
            "company": "Italian_Cities",
            "comments": "Generated by scripts/build_dataset.py; do not edit manually.",
            "created": datetime.fromisoformat(BUILD_DATE).replace(
                tzinfo=timezone.utc
            ),
        }
    )

    data_sheet = workbook.add_worksheet("Italian Locations")
    info_sheet = workbook.add_worksheet("Dataset Info")
    data_sheet.hide_gridlines(2)
    info_sheet.hide_gridlines(2)
    data_sheet.freeze_panes(1, 3)
    info_sheet.freeze_panes(1, 0)

    header_format = workbook.add_format(
        {
            "bold": True,
            "font_color": "#FFFFFF",
            "bg_color": "#0F4C5C",
            "text_wrap": True,
            "valign": "vcenter",
        }
    )
    text_format = workbook.add_format({"num_format": "@"})
    alternate_row_format = workbook.add_format({"bg_color": "#EAF6F8"})
    coordinate_format = workbook.add_format(
        {"num_format": "0.000000000000000"}
    )
    title_format = workbook.add_format(
        {
            "bold": True,
            "font_color": "#FFFFFF",
            "bg_color": "#0F4C5C",
            "font_size": 18,
            "valign": "vcenter",
        }
    )
    section_format = workbook.add_format(
        {
            "bold": True,
            "font_color": "#17324D",
            "bg_color": "#DCEFF1",
        }
    )
    wrapped_format = workbook.add_format({"text_wrap": True, "valign": "top"})
    integer_format = workbook.add_format({"num_format": "#,##0"})

    for column, field in enumerate(ITALIAN_LOCATION_FIELDS):
        data_sheet.write_string(0, column, field, header_format)
    data_sheet.set_row(0, 32)

    coordinate_fields = {"latitude", "longitude"}
    for row_index, row in enumerate(rows, start=1):
        for column, field in enumerate(ITALIAN_LOCATION_FIELDS):
            value = row[field]
            if not value:
                continue
            if field in coordinate_fields:
                data_sheet.write_number(
                    row_index,
                    column,
                    float(value),
                    coordinate_format,
                )
            else:
                data_sheet.write_string(row_index, column, value, text_format)

    widths = (
        40,
        38,
        30,
        30,
        29,
        17,
        25,
        13,
        20,
        14,
        28,
        28,
        23,
        13,
        15,
        20,
        20,
        18,
        30,
        22,
        32,
    )
    for column, width in enumerate(widths):
        data_sheet.set_column(column, column, width)
    data_sheet.autofilter(0, 0, len(rows), len(ITALIAN_LOCATION_FIELDS) - 1)
    data_sheet.conditional_format(
        1,
        0,
        len(rows),
        len(ITALIAN_LOCATION_FIELDS) - 1,
        {
            "type": "formula",
            "criteria": "=MOD(ROW(),2)=0",
            "format": alternate_row_format,
        },
    )

    info_sheet.write("A1", "Italian Cities — Generated Dataset", title_format)
    info_sheet.write_blank("B1", None, title_format)
    info_sheet.set_row(0, 34)
    info_sheet.write_row("A3", ["Metric", "Value"], section_format)
    info_sheet.write("A4", "Schema version")
    info_sheet.write("B4", SCHEMA_VERSION)
    info_sheet.write("A5", "Canonical CSV SHA-256")
    info_sheet.write("B5", canonical_sha256)
    info_sheet.write("A6", "Total locations")
    info_sheet.write_formula(
        "B6",
        f"=ROWS('Italian Locations'!A2:A{len(rows) + 1})",
        integer_format,
        len(rows),
    )
    municipality_count = sum(
        row["location_kind"] == "municipality" for row in rows
    )
    locality_count = len(rows) - municipality_count
    missing_count = sum(row["coordinate_status"] == "missing" for row in rows)
    kind_column = xl_col_to_name(ITALIAN_LOCATION_FIELDS.index("location_kind"))
    status_column = xl_col_to_name(
        ITALIAN_LOCATION_FIELDS.index("coordinate_status")
    )
    info_sheet.write("A7", "Municipalities")
    info_sheet.write_formula(
        "B7",
        f'=COUNTIF(\'Italian Locations\'!{kind_column}2:'
        f'{kind_column}{len(rows) + 1},"municipality")',
        integer_format,
        municipality_count,
    )
    info_sheet.write("A8", "Unclassified localities")
    info_sheet.write_formula(
        "B8",
        f'=COUNTIF(\'Italian Locations\'!{kind_column}2:'
        f'{kind_column}{len(rows) + 1},'
        '"postal_locality_unclassified")',
        integer_format,
        locality_count,
    )
    info_sheet.write("A9", "Missing coordinates")
    info_sheet.write_formula(
        "B9",
        f'=COUNTIF(\'Italian Locations\'!{status_column}2:'
        f'{status_column}{len(rows) + 1},"missing")',
        integer_format,
        missing_count,
    )
    info_sheet.write_row("A11", ["Declared source", "URL"], section_format)
    info_sheet.write("A12", "ISTAT — Codici delle unità amministrative")
    info_sheet.write_url(
        "B12",
        "https://www.istat.it/classificazione/"
        "codici-dei-comuni-delle-province-e-delle-regioni/",
    )
    info_sheet.write("A13", "ISTAT — Open data")
    info_sheet.write_url("B13", "https://www.istat.it/dati/open-data/")
    info_sheet.write("A14", "Repository provenance and licence notes")
    info_sheet.write("B14", "DATA_SOURCES.md")
    info_sheet.write("A15", "Generation warning")
    info_sheet.write(
        "B15",
        "Generated file: do not edit manually; run scripts/build_dataset.py.",
        wrapped_format,
    )
    info_sheet.set_column("A:A", 38)
    info_sheet.set_column("B:B", 88)

    workbook.close()
    os.replace(temporary, xlsx_path)
    normalize_xlsx_package(xlsx_path)


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

    report = {
        "status": "exported",
        "schema_version": SCHEMA_VERSION,
        "rows": len(rows),
        "record_digest": record_digest(rows),
        "outputs": {
            "csv": {
                "path": str(canonical_path.relative_to(ROOT)),
                "sha256": canonical_sha256,
            },
            "json": {
                "path": str(json_path.relative_to(ROOT)),
                "sha256": sha256_file(json_path),
            },
            "xlsx": {
                "path": str(xlsx_path.relative_to(ROOT)),
                "sha256": sha256_file(xlsx_path),
            },
            "sqlite": {
                "path": str(sqlite_path.relative_to(ROOT)),
                "semantic_sha256": record_digest(rows),
                "binary_hash_portability": (
                    "not guaranteed across SQLite library versions"
                ),
            },
        },
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
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
