"""Cross-format and generated-report equivalence validators."""

from __future__ import annotations

import json
import sqlite3
import xml.etree.ElementTree as ET
import zipfile
from decimal import Decimal, InvalidOperation
from pathlib import Path

from check_determinism import collect_signatures
from dataset_common import (
    GENERATED_PATHS,
    ITALIAN_LOCATION_FIELDS,
    REPORTS_DIR,
    ROOT,
    record_digest,
    sha256_file,
)
from project_metadata import SCHEMA_VERSION
from validators.common import QualityChecks, add_error, add_quality_error


SHEET_NS = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
DOC_REL_NS = {
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
}
PACKAGE_REL_NS = {
    "r": "http://schemas.openxmlformats.org/package/2006/relationships"
}


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
        relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
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
        zip(canonical_rows, xlsx_rows, strict=True), start=2
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


def validate_formats(
    *,
    locations: list[dict[str, str]],
    determinism_report_path: Path,
    errors: list[str],
    checks: QualityChecks,
) -> tuple[dict[str, object], list[dict[str, str]]]:
    json_payload = json.loads(GENERATED_PATHS["json"].read_text(encoding="utf-8"))
    if tuple(json_payload.get("fields", ())) != ITALIAN_LOCATION_FIELDS:
        add_error(errors, "JSON field contract differs from canonical CSV")
    if json_payload.get("schema_version") != SCHEMA_VERSION:
        add_error(errors, "JSON schema version metadata is stale")
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
    if metadata.get("schema_version") != SCHEMA_VERSION:
        add_error(errors, "SQLite schema version metadata is stale")

    xlsx_fields, xlsx_rows = load_xlsx_table(GENERATED_PATHS["xlsx"])
    if xlsx_fields != ITALIAN_LOCATION_FIELDS:
        add_error(errors, "XLSX field contract differs from canonical CSV")
    else:
        compare_xlsx_rows(locations, xlsx_rows, errors)

    diff_report = json.loads(
        (REPORTS_DIR / "release-diff.json").read_text(encoding="utf-8")
    )
    if diff_report.get("schema_version") != SCHEMA_VERSION:
        add_error(errors, "release diff schema metadata is stale")
    if diff_report.get("current", {}).get("sha256") != sha256_file(
        GENERATED_PATHS["italian_locations"]
    ):
        add_error(errors, "release diff canonical checksum is stale")

    if not determinism_report_path.exists():
        add_quality_error(
            errors,
            checks,
            "deterministic_build",
            f"{determinism_report_path.relative_to(ROOT)} is missing",
        )
    else:
        determinism_report = json.loads(
            determinism_report_path.read_text(encoding="utf-8")
        )
        if determinism_report.get("status") != "passed":
            add_quality_error(
                errors,
                checks,
                "deterministic_build",
                "the last two-build comparison did not pass",
            )
        if determinism_report.get("runs") != 2:
            add_quality_error(
                errors,
                checks,
                "deterministic_build",
                "the determinism report must compare exactly two builds",
            )
        if determinism_report.get("signatures") != collect_signatures():
            add_quality_error(
                errors,
                checks,
                "deterministic_build",
                "the determinism report is stale for the committed outputs",
            )

    return json_payload, sqlite_rows
