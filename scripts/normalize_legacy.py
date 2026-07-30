#!/usr/bin/env python3
"""Build the Milestone 1 canonical CSV from the preserved legacy export."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import unicodedata
import uuid
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LEGACY = ROOT / "legacy/2023-05-02-original/Italian Cities.csv"
DEFAULT_ISTAT = (
    ROOT
    / "sources/snapshots/istat/Elenco-comuni-italiani-2026-02-21.xlsx"
)
DEFAULT_OUTPUT = (
    ROOT / "legacy/milestone-1-canonical/italian_postal_localities.csv"
)
DEFAULT_REPORT = ROOT / "reports/milestone1-normalization.json"
EXPECTED_LEGACY_SHA256 = (
    "45f31340a6f0c390927aa1224424a75c6c968e601aa2df0a746413431e82d050"
)
EXPECTED_ISTAT_SHA256 = (
    "83842076860450f7e482daecea6b7a769f5f93d0bf5b0d48802b44896d7a26d5"
)

LEGACY_FIELDS = (
    "legacy_uuid",
    "name",
    "postal_code",
    "province_code",
    "province_name",
    "region_name",
    "country_name",
    "latitude",
    "longitude",
    "visible",
)

CANONICAL_FIELDS = (
    "location_id",
    "legacy_uuid",
    "name",
    "postal_code",
    "record_type",
    "municipality_istat_code",
    "province_code",
    "province_name",
    "region_name",
    "country_code",
    "country_name",
    "latitude",
    "longitude",
    "coordinate_status",
    "source_snapshot",
)

NULL_TOKENS = {"", "null", "none", "n/a"}
ISTAT_NS = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
LOCATION_NAMESPACE = uuid.uuid5(
    uuid.NAMESPACE_URL,
    "https://github.com/Codewriter90x/Italian_Cities/location",
)

BROVELLO_LEGACY_UUID = "a8aec4c6-ab9e-49ae-becf-fd111125f56a"
BROVELLO_BAD_LONGITUDE = "539621684096616"
BROVELLO_CORRECTED_LONGITUDE = "8.539621684096616"


def normalize_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    normalized = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
    normalized = normalized.casefold().replace("’", "'")
    return re.sub(r"[^a-z0-9]+", " ", normalized).strip()


def is_null(value: str | None) -> bool:
    return (value or "").strip().casefold() in NULL_TOKENS


def column_index(cell_reference: str) -> int:
    letters = "".join(character for character in cell_reference if character.isalpha())
    index = 0
    for character in letters:
        index = index * 26 + ord(character) - ord("A") + 1
    return index - 1


def load_istat_municipalities(path: Path) -> dict[tuple[str, str], dict[str, str]]:
    with zipfile.ZipFile(path) as archive:
        shared_root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
        shared_strings = [
            "".join(node.text or "" for node in item.iterfind(".//x:t", ISTAT_NS))
            for item in shared_root.findall("x:si", ISTAT_NS)
        ]
        sheet_root = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))

    parsed_rows: list[list[str | None]] = []
    for row in sheet_root.findall(".//x:sheetData/x:row", ISTAT_NS):
        values: list[str | None] = [None] * 27
        for cell in row.findall("x:c", ISTAT_NS):
            value_node = cell.find("x:v", ISTAT_NS)
            if value_node is None:
                value = None
            elif cell.get("t") == "s":
                value = shared_strings[int(value_node.text)]
            else:
                value = value_node.text
            values[column_index(cell.get("r", ""))] = value
        parsed_rows.append(values)

    municipalities: dict[tuple[str, str], dict[str, str]] = {}
    for row in parsed_rows[1:]:
        record = {
            "istat_code": row[4] or "",
            "bilingual_name": row[5] or "",
            "italian_name": row[6] or "",
            "region_name": row[10] or "",
            "province_name": row[11] or "",
            "province_code": row[14] or "",
        }
        for name in (record["italian_name"], record["bilingual_name"]):
            if name:
                municipalities[(normalize_name(name), record["province_code"])] = record
    return municipalities


def load_legacy_rows(path: Path) -> tuple[list[dict[str, str]], int]:
    records: list[dict[str, str]] = []
    removed_all_null = 0
    with path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.reader(source, delimiter=";")
        for line_number, values in enumerate(reader, start=1):
            if len(values) != len(LEGACY_FIELDS):
                raise ValueError(
                    f"{path}:{line_number}: expected {len(LEGACY_FIELDS)} fields, "
                    f"found {len(values)}"
                )
            if all(is_null(value) for value in values):
                removed_all_null += 1
                continue
            records.append(dict(zip(LEGACY_FIELDS, values, strict=True)))
    return records, removed_all_null


def deterministic_locality_id(record: dict[str, str]) -> str:
    identity_key = "|".join(
        (
            "IT",
            record["postal_code"],
            record["province_code"],
            normalize_name(record["name"]),
        )
    )
    return f"IT-LOC-{uuid.uuid5(LOCATION_NAMESPACE, identity_key)}"


def canonicalize(
    legacy_records: list[dict[str, str]],
    municipalities: dict[tuple[str, str], dict[str, str]],
) -> tuple[list[dict[str, str]], dict[str, object]]:
    output: list[dict[str, str]] = []
    correction_log: list[dict[str, str]] = []

    for legacy in legacy_records:
        municipality = municipalities.get(
            (normalize_name(legacy["name"]), legacy["province_code"])
        )
        if municipality:
            record_type = "municipality"
            istat_code = municipality["istat_code"]
            location_id = f"IT-COM-{istat_code}"
        else:
            record_type = "postal_locality_unclassified"
            istat_code = ""
            location_id = deterministic_locality_id(legacy)

        latitude = "" if is_null(legacy["latitude"]) else legacy["latitude"].strip()
        longitude = "" if is_null(legacy["longitude"]) else legacy["longitude"].strip()
        coordinate_status = "missing" if not latitude and not longitude else "available"

        if (
            legacy["legacy_uuid"] == BROVELLO_LEGACY_UUID
            and longitude == BROVELLO_BAD_LONGITUDE
        ):
            longitude = BROVELLO_CORRECTED_LONGITUDE
            coordinate_status = "corrected"
            correction_log.append(
                {
                    "legacy_uuid": legacy["legacy_uuid"],
                    "name": legacy["name"],
                    "field": "longitude",
                    "before": BROVELLO_BAD_LONGITUDE,
                    "after": BROVELLO_CORRECTED_LONGITUDE,
                    "reason": "restored missing leading '8.' from a geographic outlier",
                }
            )

        output.append(
            {
                "location_id": location_id,
                "legacy_uuid": legacy["legacy_uuid"],
                "name": legacy["name"],
                "postal_code": legacy["postal_code"],
                "record_type": record_type,
                "municipality_istat_code": istat_code,
                "province_code": legacy["province_code"],
                "province_name": legacy["province_name"],
                "region_name": legacy["region_name"],
                "country_code": "IT",
                "country_name": legacy["country_name"],
                "latitude": latitude,
                "longitude": longitude,
                "coordinate_status": coordinate_status,
                "source_snapshot": "legacy-2023-05-02",
            }
        )

    output.sort(
        key=lambda row: (
            normalize_name(row["name"]),
            row["province_code"],
            row["postal_code"],
            row["legacy_uuid"],
        )
    )
    status_counts = Counter(row["coordinate_status"] for row in output)
    record_type_counts = Counter(row["record_type"] for row in output)

    report: dict[str, object] = {
        "output_rows": len(output),
        "record_type_counts": dict(sorted(record_type_counts.items())),
        "coordinate_status_counts": dict(sorted(status_counts.items())),
        "corrections": correction_log,
        "stable_locality_namespace_uuid": str(LOCATION_NAMESPACE),
    }
    return output, report


def validate_numeric_coordinates(rows: list[dict[str, str]]) -> None:
    for row in rows:
        latitude = row["latitude"]
        longitude = row["longitude"]
        if bool(latitude) != bool(longitude):
            raise ValueError(f"partial coordinate pair for {row['location_id']}")
        if not latitude:
            continue
        lat = float(latitude)
        lon = float(longitude)
        if not (math.isfinite(lat) and math.isfinite(lon)):
            raise ValueError(f"non-finite coordinate for {row['location_id']}")
        if not (35 <= lat <= 48 and 6 <= lon <= 19):
            raise ValueError(f"coordinate outside broad Italy bounds for {row['location_id']}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--legacy", type=Path, default=DEFAULT_LEGACY)
    parser.add_argument("--istat", type=Path, default=DEFAULT_ISTAT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.istat.exists():
        raise SystemExit(
            f"Missing ISTAT reference: {args.istat}. See sources/README.md."
        )

    legacy_sha256 = hashlib.sha256(args.legacy.read_bytes()).hexdigest()
    istat_sha256 = hashlib.sha256(args.istat.read_bytes()).hexdigest()
    if args.legacy == DEFAULT_LEGACY and legacy_sha256 != EXPECTED_LEGACY_SHA256:
        raise SystemExit("The default legacy baseline checksum does not match")
    if args.istat == DEFAULT_ISTAT and istat_sha256 != EXPECTED_ISTAT_SHA256:
        raise SystemExit("The default ISTAT reference checksum does not match")

    legacy_rows, removed_all_null = load_legacy_rows(args.legacy)
    municipalities = load_istat_municipalities(args.istat)
    canonical_rows, report = canonicalize(legacy_rows, municipalities)
    validate_numeric_coordinates(canonical_rows)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as destination:
        writer = csv.DictWriter(
            destination,
            fieldnames=CANONICAL_FIELDS,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(canonical_rows)

    report["removed_all_null_rows"] = removed_all_null
    report["legacy_input_sha256"] = legacy_sha256
    report["istat_reference_sha256"] = istat_sha256
    report["output_sha256"] = hashlib.sha256(args.output.read_bytes()).hexdigest()
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print("Legacy normalization completed; details are available in the report.")


if __name__ == "__main__":
    main()
