#!/usr/bin/env python3
"""Validate schema, integrity and cross-format equivalence for Milestone 2."""

from __future__ import annotations

import argparse
import csv
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
from check_determinism import (
    DEFAULT_REPORT as DETERMINISM_REPORT,
    collect_signatures,
)
from normalize_legacy import DEFAULT_ISTAT, load_istat_municipalities


DEFAULT_REPORT = REPORTS_DIR / "milestone3-validation.json"
EXPECTED_BASELINE_SHA256 = (
    "735a7e9a1e7fb4eab005022478772ceab73d0034120f4f243ca68d4c64668a3d"
)
QUALITY_GATE_VERSION = "3.0.0"
ITALY_BOUNDS = {
    "latitude_min": 35.0,
    "latitude_max": 48.0,
    "longitude_min": 6.0,
    "longitude_max": 19.0,
}
QUALITY_CHECK_NAMES = (
    "schema_columns",
    "unique_identifiers",
    "postal_code_format",
    "istat_code_validity",
    "territorial_coherence",
    "numeric_coordinates",
    "coordinate_bounds",
    "no_empty_rows",
    "no_logical_duplicates",
    "cross_table_integrity",
    "deterministic_build",
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


def add_quality_error(
    errors: list[str],
    checks: dict[str, dict[str, object]],
    check_name: str,
    message: str,
) -> None:
    checks[check_name]["violations"] = int(checks[check_name]["violations"]) + 1
    add_error(errors, f"[{check_name}] {message}")


def completely_blank_record_lines(path: Path) -> list[int]:
    """Return physical or delimiter-only blank data rows, excluding the header."""

    lines = path.read_text(encoding="utf-8-sig").splitlines()
    blank_lines: list[int] = []
    for line_number, line in enumerate(lines[1:], start=2):
        if not line.strip():
            blank_lines.append(line_number)
            continue
        values = next(csv.reader([line]))
        if values and all(not value.strip() for value in values):
            blank_lines.append(line_number)
    return blank_lines


def territorial_names_compatible(left: str, right: str) -> bool:
    """Allow an official bilingual suffix while retaining legacy display labels."""

    left_key = normalize_name(left)
    right_key = normalize_name(right)
    return (
        left_key == right_key
        or left_key.startswith(f"{right_key} ")
        or right_key.startswith(f"{left_key} ")
    )


def validate_unique_key(
    *,
    rows: list[dict[str, str]],
    fields: tuple[str, ...],
    dataset: str,
    errors: list[str],
    checks: dict[str, dict[str, object]],
) -> None:
    seen: set[tuple[str, ...]] = set()
    for line_number, row in enumerate(rows, start=2):
        key = tuple(row[field] for field in fields)
        if any(not value for value in key):
            add_quality_error(
                errors,
                checks,
                "unique_identifiers",
                f"{dataset}:{line_number}: empty identifier in {fields}",
            )
        if key in seen:
            add_quality_error(
                errors,
                checks,
                "unique_identifiers",
                f"{dataset}:{line_number}: duplicate identifier {fields}={key}",
            )
        seen.add(key)


def validate_logical_key(
    *,
    rows: list[dict[str, str]],
    fields: tuple[str, ...],
    dataset: str,
    errors: list[str],
    checks: dict[str, dict[str, object]],
) -> None:
    seen: set[tuple[str, ...]] = set()
    for line_number, row in enumerate(rows, start=2):
        key = tuple(row[field] for field in fields)
        if key in seen:
            add_quality_error(
                errors,
                checks,
                "no_logical_duplicates",
                f"{dataset}:{line_number}: duplicate logical key {fields}={key}",
            )
        seen.add(key)


def validate_coordinate_table(
    *,
    rows: list[dict[str, str]],
    dataset: str,
    errors: list[str],
    checks: dict[str, dict[str, object]],
) -> None:
    for line_number, row in enumerate(rows, start=2):
        latitude = row["latitude"]
        longitude = row["longitude"]
        label = f"{dataset}:{line_number}"
        if bool(latitude) != bool(longitude):
            add_quality_error(
                errors,
                checks,
                "numeric_coordinates",
                f"{label}: partial coordinate pair",
            )
            continue
        if not latitude:
            continue
        try:
            lat = float(latitude)
            lon = float(longitude)
        except ValueError:
            add_quality_error(
                errors,
                checks,
                "numeric_coordinates",
                f"{label}: non-numeric coordinates",
            )
            continue
        if not (math.isfinite(lat) and math.isfinite(lon)):
            add_quality_error(
                errors,
                checks,
                "numeric_coordinates",
                f"{label}: non-finite coordinates",
            )
            continue
        if not (
            ITALY_BOUNDS["latitude_min"]
            <= lat
            <= ITALY_BOUNDS["latitude_max"]
            and ITALY_BOUNDS["longitude_min"]
            <= lon
            <= ITALY_BOUNDS["longitude_max"]
        ):
            add_quality_error(
                errors,
                checks,
                "coordinate_bounds",
                f"{label}: coordinates outside broad Italy bounds",
            )


def validate_postal_code_table(
    *,
    rows: list[dict[str, str]],
    dataset: str,
    errors: list[str],
    checks: dict[str, dict[str, object]],
) -> None:
    for line_number, row in enumerate(rows, start=2):
        if not re.fullmatch(r"\d{5}", row["postal_code"]):
            add_quality_error(
                errors,
                checks,
                "postal_code_format",
                f"{dataset}:{line_number}: CAP must contain exactly five digits",
            )


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
    quality_checks: dict[str, dict[str, object]] = {
        name: {"status": "passed", "violations": 0}
        for name in QUALITY_CHECK_NAMES
    }
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

    table_rows = {
        "data/municipalities.csv": municipalities,
        "data/localities.csv": localities,
        "data/postal_codes.csv": postal_codes,
        "data/italian_locations.csv": locations,
    }
    for dataset, rows in table_rows.items():
        path = ROOT / dataset
        for line_number in completely_blank_record_lines(path):
            add_quality_error(
                errors,
                quality_checks,
                "no_empty_rows",
                f"{dataset}:{line_number}: completely empty row",
            )
        for line_number, row in enumerate(rows, start=2):
            if all(not (value or "").strip() for value in row.values()):
                add_quality_error(
                    errors,
                    quality_checks,
                    "no_empty_rows",
                    f"{dataset}:{line_number}: completely empty record",
                )
        validate_postal_code_table(
            rows=rows,
            dataset=dataset,
            errors=errors,
            checks=quality_checks,
        )

    unique_contracts = (
        (
            municipalities,
            "data/municipalities.csv",
            (("municipality_id",), ("istat_code",), ("legacy_uuid",)),
        ),
        (
            localities,
            "data/localities.csv",
            (("locality_id",), ("legacy_uuid",)),
        ),
        (
            postal_codes,
            "data/postal_codes.csv",
            (("location_id", "postal_code"),),
        ),
        (
            locations,
            "data/italian_locations.csv",
            (("location_id",), ("legacy_uuid",)),
        ),
    )
    for rows, dataset, keys in unique_contracts:
        for fields in keys:
            validate_unique_key(
                rows=rows,
                fields=fields,
                dataset=dataset,
                errors=errors,
                checks=quality_checks,
            )

    logical_contracts = (
        (
            municipalities,
            "data/municipalities.csv",
            ("normalized_name", "postal_code", "province_code"),
        ),
        (
            localities,
            "data/localities.csv",
            ("normalized_name", "postal_code", "province_code"),
        ),
        (
            postal_codes,
            "data/postal_codes.csv",
            ("location_id", "postal_code", "province_code"),
        ),
        (
            locations,
            "data/italian_locations.csv",
            ("normalized_name", "postal_code", "province_code"),
        ),
    )
    for rows, dataset, fields in logical_contracts:
        validate_logical_key(
            rows=rows,
            fields=fields,
            dataset=dataset,
            errors=errors,
            checks=quality_checks,
        )

    for rows, dataset in (
        (municipalities, "data/municipalities.csv"),
        (localities, "data/localities.csv"),
        (locations, "data/italian_locations.csv"),
    ):
        validate_coordinate_table(
            rows=rows,
            dataset=dataset,
            errors=errors,
            checks=quality_checks,
        )

    official_records = load_istat_municipalities(DEFAULT_ISTAT)
    official_by_istat = {
        record["istat_code"]: record for record in official_records.values()
    }
    official_province_codes = {
        record["province_code"] for record in official_by_istat.values()
    }
    municipality_province_codes = {
        row["province_code"] for row in municipalities
    }
    for line_number, row in enumerate(municipalities, start=2):
        label = f"data/municipalities.csv:{line_number}"
        istat_code = row["istat_code"]
        if not re.fullmatch(r"\d{6}", istat_code):
            add_quality_error(
                errors,
                quality_checks,
                "istat_code_validity",
                f"{label}: ISTAT code must contain exactly six digits",
            )
            continue
        official = official_by_istat.get(istat_code)
        if official is None:
            add_quality_error(
                errors,
                quality_checks,
                "istat_code_validity",
                f"{label}: ISTAT code {istat_code} is absent from the declared snapshot",
            )
            continue
        if row["municipality_id"] != f"IT-COM-{istat_code}":
            add_quality_error(
                errors,
                quality_checks,
                "istat_code_validity",
                f"{label}: municipality_id disagrees with ISTAT code",
            )
        if row["province_code"] != official["province_code"]:
            add_quality_error(
                errors,
                quality_checks,
                "territorial_coherence",
                f"{label}: municipality and official province code disagree",
            )
        if not territorial_names_compatible(
            row["region_name"],
            official["region_name"],
        ):
            add_quality_error(
                errors,
                quality_checks,
                "territorial_coherence",
                f"{label}: municipality and official region disagree",
            )

    territories_by_province: dict[str, set[tuple[str, str]]] = {}
    for line_number, row in enumerate(locations, start=2):
        province_code = row["province_code"]
        territories_by_province.setdefault(province_code, set()).add(
            (row["province_name"], row["region_name"])
        )
        if province_code not in official_province_codes:
            add_quality_error(
                errors,
                quality_checks,
                "territorial_coherence",
                f"data/italian_locations.csv:{line_number}: "
                f"province code {province_code!r} is absent from ISTAT",
            )
    for province_code, labels in sorted(territories_by_province.items()):
        if len(labels) != 1:
            add_quality_error(
                errors,
                quality_checks,
                "territorial_coherence",
                f"province {province_code} maps to multiple province/region labels: "
                f"{sorted(labels)}",
            )
    for line_number, row in enumerate(localities, start=2):
        if row["province_code"] not in municipality_province_codes:
            add_quality_error(
                errors,
                quality_checks,
                "territorial_coherence",
                f"data/localities.csv:{line_number}: province has no municipality",
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
        add_quality_error(
            errors,
            quality_checks,
            "cross_table_integrity",
            "municipalities.csv diverges from the canonical partition",
        )
    if localities != expected_localities:
        add_quality_error(
            errors,
            quality_checks,
            "cross_table_integrity",
            "localities.csv diverges from the canonical partition",
        )
    if postal_codes != expected_postal_codes:
        add_quality_error(
            errors,
            quality_checks,
            "cross_table_integrity",
            "postal_codes.csv diverges from canonical relations",
        )

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

    if not DETERMINISM_REPORT.exists():
        add_quality_error(
            errors,
            quality_checks,
            "deterministic_build",
            f"{DETERMINISM_REPORT.relative_to(ROOT)} is missing",
        )
    else:
        determinism_report = json.loads(
            DETERMINISM_REPORT.read_text(encoding="utf-8")
        )
        if determinism_report.get("status") != "passed":
            add_quality_error(
                errors,
                quality_checks,
                "deterministic_build",
                "the last two-build comparison did not pass",
            )
        if determinism_report.get("runs") != 2:
            add_quality_error(
                errors,
                quality_checks,
                "deterministic_build",
                "the determinism report must compare exactly two builds",
            )
        if determinism_report.get("signatures") != collect_signatures():
            add_quality_error(
                errors,
                quality_checks,
                "deterministic_build",
                "the determinism report is stale for the committed outputs",
            )

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
    for check in quality_checks.values():
        if check["violations"]:
            check["status"] = "failed"
    return {
        "status": "passed" if not errors else "failed",
        "schema_version": "2.0.0",
        "quality_gate_version": QUALITY_GATE_VERSION,
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
        "quality_checks": quality_checks,
        "coordinate_bounds": ITALY_BOUNDS,
        "territorial_reference": {
            "source": str(DEFAULT_ISTAT.relative_to(ROOT)),
            "municipalities": len(official_by_istat),
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
