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
from project_metadata import (
    OPERATIONAL_DATA_READINESS,
    SCHEMA_VERSION,
    STRUCTURAL_QUALITY,
)

from validators.common import QualityChecks, add_quality_error

SHEET_NS = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
DOC_REL_NS = {
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
}
PACKAGE_REL_NS = {
    "r": "http://schemas.openxmlformats.org/package/2006/relationships"
}


def column_index(reference: str) -> int:
    letters = "".join(
        character for character in reference if character.isalpha()
    )
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
            for node in relationships.findall(
                "r:Relationship", PACKAGE_REL_NS
            )
        }
        target = None
        for sheet in workbook.findall(".//x:sheets/x:sheet", SHEET_NS):
            if sheet.get("name") == sheet_name:
                relation_id = sheet.get(f"{{{DOC_REL_NS['r']}}}id")
                target = targets.get(relation_id)
                break
        if not target:
            raise ValueError(f"{path}: worksheet {sheet_name!r} not found")
        sheet_path = (
            target.lstrip("/") if target.startswith("/") else f"xl/{target}"
        )
        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            shared_root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            shared_strings = [
                "".join(
                    node.text or ""
                    for node in item.iterfind(".//x:t", SHEET_NS)
                )
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
                    node.text or ""
                    for node in cell.iterfind(".//x:t", SHEET_NS)
                )
            else:
                node = cell.find("x:v", SHEET_NS)
                if node is None or node.text is None:
                    value = ""
                elif cell_type == "s":
                    value = shared_strings[int(node.text)]
                else:
                    value = node.text
            values[index] = value
        raw_rows.append(values)
    fields = tuple(raw_rows[0])
    records = []
    for values in raw_rows[1:]:
        values.extend([""] * (len(fields) - len(values)))
        records.append(dict(zip(fields, values[: len(fields)], strict=True)))
    return fields, records


def _coordinates_equal(left: str, right: str) -> bool:
    if left == right:
        return True
    try:
        return abs(Decimal(left) - Decimal(right)) <= Decimal("1e-12")
    except InvalidOperation:
        return False


def validate_formats(
    *,
    locations: list[dict[str, str]],
    determinism_report_path: Path,
    errors: list[str],
    checks: QualityChecks,
) -> dict[str, bool]:
    equivalence = {"json": True, "xlsx": True, "sqlite": True, "sql": True}
    payload = json.loads(GENERATED_PATHS["json"].read_text(encoding="utf-8"))
    metadata = payload.get("metadata", {})
    if (
        tuple(payload.get("fields", ())) != ITALIAN_LOCATION_FIELDS
        or payload.get("rows") != locations
        or metadata.get("schema_version") != SCHEMA_VERSION
        or metadata.get("canonical_sha256")
        != sha256_file(GENERATED_PATHS["italian_locations"])
        or metadata.get("structural_quality") != STRUCTURAL_QUALITY
        or metadata.get("operational_data_readiness")
        != OPERATIONAL_DATA_READINESS
        or "GeoNames" not in metadata.get("attribution", {}).get(
            "geonames", ""
        )
    ):
        equivalence["json"] = False

    connection = sqlite3.connect(GENERATED_PATHS["sqlite"])
    try:
        quoted = ", ".join(
            f'"{field}"' for field in ITALIAN_LOCATION_FIELDS
        )
        sqlite_rows = [
            dict(zip(ITALIAN_LOCATION_FIELDS, values, strict=True))
            for values in connection.execute(
                f'SELECT {quoted} FROM "italian_locations" '
                'ORDER BY "normalized_name", "province_code", "postal_code", '
                '"location_id", "location_postal_id"'
            )
        ]
        sqlite_metadata = dict(
            connection.execute('SELECT "key", "value" FROM "_metadata"')
        )
    finally:
        connection.close()
    if (
        sqlite_rows != locations
        or sqlite_metadata.get("record_digest") != record_digest(locations)
        or sqlite_metadata.get("schema_version") != SCHEMA_VERSION
        or "GeoNames" not in sqlite_metadata.get(
            "geonames_attribution", ""
        )
    ):
        equivalence["sqlite"] = False

    xlsx_fields, xlsx_rows = load_xlsx_table(GENERATED_PATHS["xlsx"])
    if xlsx_fields != ITALIAN_LOCATION_FIELDS or len(xlsx_rows) != len(
        locations
    ):
        equivalence["xlsx"] = False
    else:
        for canonical, workbook in zip(locations, xlsx_rows, strict=True):
            for field in ITALIAN_LOCATION_FIELDS:
                equal = (
                    _coordinates_equal(canonical[field], workbook[field])
                    if field in {"latitude", "longitude"}
                    else canonical[field] == workbook[field]
                )
                if not equal:
                    equivalence["xlsx"] = False
                    break
            if not equivalence["xlsx"]:
                break

    for name, passed in equivalence.items():
        if not passed:
            add_quality_error(
                errors,
                checks,
                "cross_format_equivalence",
                f"{name} diverges from canonical CSV",
            )

    required_reports = (
        REPORTS_DIR / "build-metadata.json",
        REPORTS_DIR / "release-diff.json",
    )
    for report in required_reports:
        if not report.is_file():
            add_quality_error(
                errors,
                checks,
                "cross_format_equivalence",
                f"{report.relative_to(ROOT)} is missing",
            )
    if not determinism_report_path.is_file():
        add_quality_error(
            errors,
            checks,
            "deterministic_build",
            f"{determinism_report_path.relative_to(ROOT)} is missing",
        )
    else:
        report = json.loads(
            determinism_report_path.read_text(encoding="utf-8")
        )
        if (
            report.get("status") != "passed"
            or report.get("runs") != 2
            or report.get("signatures") != collect_signatures()
        ):
            add_quality_error(
                errors,
                checks,
                "deterministic_build",
                "the two-build determinism report is stale or failed",
            )
    return equivalence
