#!/usr/bin/env python3
"""Validate schema, integrity and cross-format equivalence for Milestone 2."""

from __future__ import annotations

import argparse
import json
import math
import re
import sqlite3
import uuid
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path

from dataset_common import (
    GENERATED_PATHS,
    ITALIAN_LOCATION_FIELDS,
    LOCALITY_FIELDS,
    MILESTONE1_BASELINE,
    MUNICIPALITY_FIELDS,
    POSTAL_CODE_FIELDS,
    REPORTS_DIR,
    ROOT,
    canonical_row_sort_key,
    normalize_name,
    read_csv_rows,
    record_digest,
    sha256_file,
    write_json,
)


DEFAULT_REPORT = REPORTS_DIR / "milestone2-validation.json"
EXPECTED_BASELINE_SHA256 = (
    "735a7e9a1e7fb4eab005022478772ceab73d0034120f4f243ca68d4c64668a3d"
)
SHEET_NS = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
DOC_REL_NS = {
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
}
PACKAGE_REL_NS = {
    "r": "http://schemas.openxmlformats.org/package/2006/relationships"
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def column_index(reference: str) -> int:
    letters = "".join(character for character in reference if character.isalpha())
    index = 0
    for character in letters:
        index = index * 26 + ord(character.upper()) - ord("A") + 1
    return index - 1


def load_xlsx_table(
    path: Path,
    sheet_name: str = "Italian Locations",
) -> tuple[tuple[str, ...], list[dict[str, str]]]:
    with zipfile.ZipFile(path) as archive:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        relationships = ET.fromstring(
            archive.read("xl/_rels/workbook.xml.rels")
        )
        targets = {
            node.get("Id"): node.get("Target")
            for node in relationships.findall("r:Relationship", PACKAGE_REL_NS)
        }
        sheet_target = None
        for sheet in workbook.findall(".//x:sheets/x:sheet", SHEET_NS):
            if sheet.get("name") == sheet_name:
                relation_id = sheet.get(f"{{{DOC_REL_NS['r']}}}id")
                sheet_target = targets.get(relation_id)
                break
        if not sheet_target:
            raise ValueError(f"{path}: worksheet {sheet_name!r} not found")
        sheet_path = (
            sheet_target.lstrip("/")
            if sheet_target.startswith("/")
            else f"xl/{sheet_target}"
        )

        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            shared_root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            shared_strings = [
                "".join(node.text or "" for node in item.iterfind(".//x:t", SHEET_NS))
                for item in shared_root.findall("x:si", SHEET_NS)
            ]
        sheet_root = ET.fromstring(archive.read(sheet_path))

    raw_rows: list[list[str]] = []
    for row in sheet_root.findall(".//x:sheetData/x:row", SHEET_NS):
        values: list[str] = []
        for cell in row.findall("x:c", SHEET_NS):
            index = column_index(cell.get("r", ""))
            while len(values) <= index:
                values.append("")
            cell_type = cell.get("t")
            if cell_type == "inlineStr":
                value = "".join(
                    node.text or "" for node in cell.iterfind(".//x:t", SHEET_NS)
                )
            else:
                value_node = cell.find("x:v", SHEET_NS)
                if value_node is None or value_node.text is None:
                    value = ""
                elif cell_type == "s":
                    value = shared_strings[int(value_node.text)]
                elif cell_type == "b":
                    value = "true" if value_node.text == "1" else "false"
                else:
                    value = value_node.text
            values[index] = value
        raw_rows.append(values)

    if not raw_rows:
        raise ValueError(f"{path}: worksheet {sheet_name!r} is empty")
    fields = tuple(raw_rows[0])
    records: list[dict[str, str]] = []
    for values in raw_rows[1:]:
        values.extend([""] * (len(fields) - len(values)))
        records.append(dict(zip(fields, values[: len(fields)], strict=True)))
    return fields, records


def add_error(errors: list[str], message: str, limit: int = 200) -> None:
    if len(errors) < limit:
        errors.append(message)


def coordinates_equal(left: str, right: str) -> bool:
    if left == right:
        return True
    if not left or not right:
        return False
    try:
        return abs(Decimal(left) - Decimal(right)) <= Decimal("1e-12")
    except InvalidOperation:
        return False


def compare_xlsx_rows(
    canonical_rows: list[dict[str, str]],
    xlsx_rows: list[dict[str, str]],
    errors: list[str],
) -> None:
    if len(canonical_rows) != len(xlsx_rows):
        add_error(
            errors,
            f"XLSX row count mismatch: csv={len(canonical_rows)}, xlsx={len(xlsx_rows)}",
        )
        return
    for index, (canonical, workbook) in enumerate(
        zip(canonical_rows, xlsx_rows, strict=True),
        start=2,
    ):
        for field in ITALIAN_LOCATION_FIELDS:
            if field in {"latitude", "longitude"}:
                equal = coordinates_equal(canonical[field], workbook[field])
            else:
                equal = canonical[field] == workbook[field]
            if not equal:
                add_error(
                    errors,
                    f"XLSX divergence at row {index}, field {field}: "
                    f"{canonical[field]!r} != {workbook[field]!r}",
                )


def expected_municipality(row: dict[str, str]) -> dict[str, str]:
    return {
        "municipality_id": row["location_id"],
        "istat_code": row["municipality_istat_code"],
        "legacy_uuid": row["legacy_uuid"],
        "name": row["name"],
        "normalized_name": row["normalized_name"],
        "postal_code": row["postal_code"],
        "province_code": row["province_code"],
        "province_name": row["province_name"],
        "region_name": row["region_name"],
        "country_code": row["country_code"],
        "country_name": row["country_name"],
        "latitude": row["latitude"],
        "longitude": row["longitude"],
        "coordinate_status": row["coordinate_status"],
        "source_snapshot": row["source_snapshot"],
    }


def expected_locality(row: dict[str, str]) -> dict[str, str]:
    return {
        "locality_id": row["location_id"],
        "legacy_uuid": row["legacy_uuid"],
        "name": row["name"],
        "normalized_name": row["normalized_name"],
        "locality_type": row["location_kind"],
        "parent_municipality_id": row["parent_municipality_id"],
        "postal_code": row["postal_code"],
        "province_code": row["province_code"],
        "province_name": row["province_name"],
        "region_name": row["region_name"],
        "country_code": row["country_code"],
        "country_name": row["country_name"],
        "latitude": row["latitude"],
        "longitude": row["longitude"],
        "coordinate_status": row["coordinate_status"],
        "source_snapshot": row["source_snapshot"],
    }


def expected_postal_code(row: dict[str, str]) -> dict[str, str]:
    return {
        "location_id": row["location_id"],
        "location_kind": row["location_kind"],
        "postal_code": row["postal_code"],
        "province_code": row["province_code"],
        "is_primary": "true",
        "source_snapshot": row["source_snapshot"],
    }


def validate() -> dict[str, object]:
    errors: list[str] = []
    warnings: list[str] = []
    locations = read_csv_rows(
        GENERATED_PATHS["italian_locations"],
        ITALIAN_LOCATION_FIELDS,
    )
    municipalities = read_csv_rows(
        GENERATED_PATHS["municipalities"],
        MUNICIPALITY_FIELDS,
    )
    localities = read_csv_rows(GENERATED_PATHS["localities"], LOCALITY_FIELDS)
    postal_codes = read_csv_rows(
        GENERATED_PATHS["postal_codes"],
        POSTAL_CODE_FIELDS,
    )

    if sha256_file(MILESTONE1_BASELINE) != EXPECTED_BASELINE_SHA256:
        add_error(errors, "Milestone 1 comparison baseline checksum mismatch")
    if len(locations) != 14_480:
        add_error(errors, f"expected 14480 canonical rows, found {len(locations)}")
    if locations != sorted(locations, key=canonical_row_sort_key):
        add_error(errors, "italian_locations.csv is not deterministically sorted")

    location_ids: set[str] = set()
    legacy_uuids: set[str] = set()
    logical_keys: set[tuple[str, str, str]] = set()
    kind_counts: Counter[str] = Counter()
    coordinate_counts: Counter[str] = Counter()

    for line_number, row in enumerate(locations, start=2):
        label = f"data/italian_locations.csv:{line_number}"
        if row["location_id"] in location_ids:
            add_error(errors, f"{label}: duplicate location_id")
        location_ids.add(row["location_id"])
        if row["legacy_uuid"] in legacy_uuids:
            add_error(errors, f"{label}: duplicate legacy_uuid")
        legacy_uuids.add(row["legacy_uuid"])
        try:
            uuid.UUID(row["legacy_uuid"])
        except ValueError:
            add_error(errors, f"{label}: invalid legacy UUID")

        if row["normalized_name"] != normalize_name(row["name"]):
            add_error(errors, f"{label}: normalized_name is not reproducible")
        if not re.fullmatch(r"\d{5}", row["postal_code"]):
            add_error(errors, f"{label}: CAP is not a five-character string")
        if not re.fullmatch(r"[A-Z]{2}", row["province_code"]):
            add_error(errors, f"{label}: invalid province code")
        if row["country_code"] != "IT":
            add_error(errors, f"{label}: country_code must be IT")
        if row["parent_municipality_id"]:
            add_error(
                errors,
                f"{label}: parent municipality must remain empty until sourced",
            )
        if any(value.strip().casefold() == "null" for value in row.values()):
            add_error(errors, f"{label}: literal NULL is forbidden")

        logical_key = (
            row["normalized_name"],
            row["postal_code"],
            row["province_code"],
        )
        if logical_key in logical_keys:
            add_error(errors, f"{label}: duplicate normalized logical key")
        logical_keys.add(logical_key)

        if row["location_kind"] == "municipality":
            if not re.fullmatch(r"\d{6}", row["municipality_istat_code"]):
                add_error(errors, f"{label}: municipality lacks a six-digit ISTAT code")
            if row["location_id"] != f"IT-COM-{row['municipality_istat_code']}":
                add_error(errors, f"{label}: municipality ID and ISTAT code disagree")
        elif row["location_kind"] == "postal_locality_unclassified":
            if row["municipality_istat_code"]:
                add_error(errors, f"{label}: unclassified locality has an ISTAT code")
            if not re.fullmatch(
                r"IT-LOC-[0-9a-f]{8}-[0-9a-f]{4}-5[0-9a-f]{3}-"
                r"[89ab][0-9a-f]{3}-[0-9a-f]{12}",
                row["location_id"],
            ):
                add_error(errors, f"{label}: locality ID is not UUIDv5-based")
        else:
            add_error(errors, f"{label}: unsupported location_kind")

        latitude = row["latitude"]
        longitude = row["longitude"]
        if bool(latitude) != bool(longitude):
            add_error(errors, f"{label}: partial coordinate pair")
        if latitude:
            try:
                lat = float(latitude)
                lon = float(longitude)
            except ValueError:
                add_error(errors, f"{label}: non-numeric coordinates")
            else:
                if not (math.isfinite(lat) and math.isfinite(lon)):
                    add_error(errors, f"{label}: non-finite coordinates")
                if not (35 <= lat <= 48 and 6 <= lon <= 19):
                    add_error(errors, f"{label}: coordinates outside broad Italy bounds")
            if row["coordinate_status"] not in {"available", "corrected"}:
                add_error(errors, f"{label}: populated coordinates have wrong status")
        elif row["coordinate_status"] != "missing":
            add_error(errors, f"{label}: missing coordinates have wrong status")

        kind_counts[row["location_kind"]] += 1
        coordinate_counts[row["coordinate_status"]] += 1

    expected_municipalities = [
        expected_municipality(row)
        for row in locations
        if row["location_kind"] == "municipality"
    ]
    expected_localities = [
        expected_locality(row)
        for row in locations
        if row["location_kind"] == "postal_locality_unclassified"
    ]
    expected_postal_codes = sorted(
        [expected_postal_code(row) for row in locations],
        key=lambda row: (
            row["postal_code"],
            row["location_kind"],
            row["location_id"],
        ),
    )
    if municipalities != expected_municipalities:
        add_error(errors, "municipalities.csv diverges from the canonical partition")
    if localities != expected_localities:
        add_error(errors, "localities.csv diverges from the canonical partition")
    if postal_codes != expected_postal_codes:
        add_error(errors, "postal_codes.csv diverges from canonical relations")

    json_payload = json.loads(GENERATED_PATHS["json"].read_text(encoding="utf-8"))
    if tuple(json_payload.get("fields", ())) != ITALIAN_LOCATION_FIELDS:
        add_error(errors, "JSON field contract differs from canonical CSV")
    if json_payload.get("rows") != locations:
        add_error(errors, "JSON records diverge from canonical CSV")
    if json_payload.get("canonical_sha256") != sha256_file(
        GENERATED_PATHS["italian_locations"]
    ):
        add_error(errors, "JSON canonical checksum metadata is stale")

    connection = sqlite3.connect(GENERATED_PATHS["sqlite"])
    try:
        quoted_fields = ", ".join(f'"{field}"' for field in ITALIAN_LOCATION_FIELDS)
        sqlite_rows = [
            dict(zip(ITALIAN_LOCATION_FIELDS, values, strict=True))
            for values in connection.execute(
                f'SELECT {quoted_fields} FROM "italian_locations" '
                'ORDER BY "normalized_name", "province_code", "postal_code", '
                '"legacy_uuid"'
            )
        ]
        metadata = dict(connection.execute('SELECT "key", "value" FROM "_metadata"'))
    finally:
        connection.close()
    if sqlite_rows != locations:
        add_error(errors, "SQLite records diverge from canonical CSV")
    if metadata.get("record_digest") != record_digest(locations):
        add_error(errors, "SQLite record digest metadata is stale")

    xlsx_fields, xlsx_rows = load_xlsx_table(GENERATED_PATHS["xlsx"])
    if xlsx_fields != ITALIAN_LOCATION_FIELDS:
        add_error(errors, "XLSX field contract differs from canonical CSV")
    else:
        compare_xlsx_rows(locations, xlsx_rows, errors)

    diff_report = json.loads(
        (REPORTS_DIR / "milestone2-diff.json").read_text(encoding="utf-8")
    )
    record_changes = diff_report.get("record_changes", {})
    if any(record_changes.get(field) for field in ("added", "removed", "changed")):
        add_error(errors, "Milestone 2 contains undocumented semantic record changes")

    if coordinate_counts["missing"]:
        warnings.append(
            f"{coordinate_counts['missing']} records still lack coordinates"
        )
    if kind_counts["postal_locality_unclassified"]:
        warnings.append(
            f"{kind_counts['postal_locality_unclassified']} localities remain unclassified"
        )
    warnings.append(
        "Legacy source provenance and release licensing remain unresolved"
    )

    output_hashes = {
        name: sha256_file(path)
        for name, path in GENERATED_PATHS.items()
        if path.exists() and name != "sqlite"
    }
    return {
        "status": "passed" if not errors else "failed",
        "schema_version": "2.0.0",
        "canonical_rows": len(locations),
        "record_digest": record_digest(locations),
        "record_type_counts": dict(sorted(kind_counts.items())),
        "coordinate_status_counts": dict(sorted(coordinate_counts.items())),
        "table_rows": {
            "municipalities": len(municipalities),
            "localities": len(localities),
            "postal_codes": len(postal_codes),
        },
        "cross_format_equivalence": {
            "csv": True,
            "json": json_payload.get("rows") == locations,
            "xlsx": not any(error.startswith("XLSX") for error in errors),
            "sqlite": sqlite_rows == locations,
        },
        "output_sha256": output_hashes,
        "output_semantic_sha256": {
            "sqlite": record_digest(sqlite_rows),
        },
        "errors": errors,
        "warnings": warnings,
    }


def main() -> None:
    args = parse_args()
    try:
        report = validate()
    except (FileNotFoundError, ValueError, KeyError, zipfile.BadZipFile) as error:
        report = {
            "status": "failed",
            "errors": [str(error)],
            "warnings": [],
        }
    write_json(args.report, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
