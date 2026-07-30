#!/usr/bin/env python3
"""Validate the Milestone 1 canonical dataset and its migration invariants."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import uuid
from collections import Counter
from pathlib import Path

from normalize_legacy import (
    BROVELLO_BAD_LONGITUDE,
    BROVELLO_CORRECTED_LONGITUDE,
    BROVELLO_LEGACY_UUID,
    CANONICAL_FIELDS,
    DEFAULT_ISTAT,
    DEFAULT_LEGACY,
    DEFAULT_OUTPUT,
    EXPECTED_ISTAT_SHA256,
    EXPECTED_LEGACY_SHA256,
    deterministic_locality_id,
    is_null,
    load_istat_municipalities,
    load_legacy_rows,
    normalize_name,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = ROOT / "reports/milestone1-validation.json"


def add_error(errors: list[str], message: str, limit: int = 100) -> None:
    if len(errors) < limit:
        errors.append(message)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--legacy", type=Path, default=DEFAULT_LEGACY)
    parser.add_argument("--istat", type=Path, default=DEFAULT_ISTAT)
    parser.add_argument("--canonical", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    errors: list[str] = []
    warnings: list[str] = []
    legacy_sha256 = hashlib.sha256(args.legacy.read_bytes()).hexdigest()
    istat_sha256 = hashlib.sha256(args.istat.read_bytes()).hexdigest()
    if args.legacy == DEFAULT_LEGACY and legacy_sha256 != EXPECTED_LEGACY_SHA256:
        add_error(errors, "default legacy baseline checksum mismatch")
    if args.istat == DEFAULT_ISTAT and istat_sha256 != EXPECTED_ISTAT_SHA256:
        add_error(errors, "default ISTAT reference checksum mismatch")

    legacy_rows, removed_all_null = load_legacy_rows(args.legacy)
    legacy_by_uuid = {row["legacy_uuid"]: row for row in legacy_rows}
    if len(legacy_by_uuid) != len(legacy_rows):
        add_error(errors, "legacy UUIDs are not unique")

    municipalities = load_istat_municipalities(args.istat)

    with args.canonical.open(encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        actual_fields = tuple(reader.fieldnames or ())
        canonical_rows = list(reader)

    if actual_fields != CANONICAL_FIELDS:
        add_error(
            errors,
            f"canonical header mismatch: expected {CANONICAL_FIELDS}, found {actual_fields}",
        )

    if len(canonical_rows) != len(legacy_rows):
        add_error(
            errors,
            f"row count mismatch: canonical={len(canonical_rows)}, legacy={len(legacy_rows)}",
        )
    if removed_all_null != 1:
        add_error(errors, f"expected one all-NULL legacy row, found {removed_all_null}")

    location_ids: set[str] = set()
    canonical_legacy_ids: set[str] = set()
    logical_keys: set[tuple[str, str, str]] = set()
    record_type_counts: Counter[str] = Counter()
    coordinate_status_counts: Counter[str] = Counter()
    corrected_rows = 0

    expected_sorted = sorted(
        canonical_rows,
        key=lambda row: (
            normalize_name(row["name"]),
            row["province_code"],
            row["postal_code"],
            row["legacy_uuid"],
        ),
    )
    if canonical_rows != expected_sorted:
        add_error(errors, "canonical rows are not deterministically sorted")

    for index, row in enumerate(canonical_rows, start=2):
        row_label = f"{args.canonical}:{index}"
        location_id = row["location_id"]
        legacy_uuid = row["legacy_uuid"]

        if any((value or "").strip().casefold() == "null" for value in row.values()):
            add_error(errors, f"{row_label}: literal NULL is not allowed")

        if location_id in location_ids:
            add_error(errors, f"{row_label}: duplicate location_id {location_id}")
        location_ids.add(location_id)

        if legacy_uuid in canonical_legacy_ids:
            add_error(errors, f"{row_label}: duplicate legacy_uuid {legacy_uuid}")
        canonical_legacy_ids.add(legacy_uuid)

        try:
            uuid.UUID(legacy_uuid)
        except ValueError:
            add_error(errors, f"{row_label}: invalid legacy UUID {legacy_uuid}")

        if legacy_uuid not in legacy_by_uuid:
            add_error(errors, f"{row_label}: legacy UUID not present in baseline")
            continue
        legacy = legacy_by_uuid[legacy_uuid]

        for canonical_field, legacy_field in (
            ("name", "name"),
            ("postal_code", "postal_code"),
            ("province_code", "province_code"),
            ("province_name", "province_name"),
            ("region_name", "region_name"),
            ("country_name", "country_name"),
        ):
            if row[canonical_field] != legacy[legacy_field]:
                add_error(
                    errors,
                    f"{row_label}: {canonical_field} changed outside the approved migration",
                )

        if not re.fullmatch(r"\d{5}", row["postal_code"]):
            add_error(errors, f"{row_label}: invalid postal code {row['postal_code']!r}")
        if not re.fullmatch(r"[A-Z]{2}", row["province_code"]):
            add_error(
                errors,
                f"{row_label}: invalid province code {row['province_code']!r}",
            )
        if row["country_code"] != "IT":
            add_error(errors, f"{row_label}: country_code must be IT")
        if row["source_snapshot"] != "legacy-2023-05-02":
            add_error(errors, f"{row_label}: unexpected source_snapshot")

        logical_key = (
            normalize_name(row["name"]),
            row["postal_code"],
            row["province_code"],
        )
        if logical_key in logical_keys:
            add_error(errors, f"{row_label}: duplicate logical locality key {logical_key}")
        logical_keys.add(logical_key)

        municipality = municipalities.get(
            (normalize_name(row["name"]), row["province_code"])
        )
        if municipality:
            expected_location_id = f"IT-COM-{municipality['istat_code']}"
            if row["record_type"] != "municipality":
                add_error(errors, f"{row_label}: exact ISTAT match not typed municipality")
            if row["municipality_istat_code"] != municipality["istat_code"]:
                add_error(errors, f"{row_label}: wrong municipality ISTAT code")
        else:
            expected_location_id = deterministic_locality_id(legacy)
            if row["record_type"] != "postal_locality_unclassified":
                add_error(errors, f"{row_label}: non-match has unsupported record_type")
            if row["municipality_istat_code"]:
                add_error(errors, f"{row_label}: unclassified locality has ISTAT code")
        if location_id != expected_location_id:
            add_error(errors, f"{row_label}: non-deterministic location_id")

        latitude = row["latitude"]
        longitude = row["longitude"]
        if bool(latitude) != bool(longitude):
            add_error(errors, f"{row_label}: partial coordinate pair")
        if latitude:
            try:
                lat = float(latitude)
                lon = float(longitude)
            except ValueError:
                add_error(errors, f"{row_label}: non-numeric coordinate")
            else:
                if not (math.isfinite(lat) and math.isfinite(lon)):
                    add_error(errors, f"{row_label}: non-finite coordinate")
                if not (35 <= lat <= 48 and 6 <= lon <= 19):
                    add_error(errors, f"{row_label}: coordinate outside broad Italy bounds")

        legacy_latitude = "" if is_null(legacy["latitude"]) else legacy["latitude"]
        legacy_longitude = "" if is_null(legacy["longitude"]) else legacy["longitude"]
        if legacy_uuid == BROVELLO_LEGACY_UUID:
            corrected_rows += 1
            if legacy_longitude != BROVELLO_BAD_LONGITUDE:
                add_error(errors, f"{row_label}: unexpected Brovello legacy longitude")
            if longitude != BROVELLO_CORRECTED_LONGITUDE:
                add_error(errors, f"{row_label}: Brovello longitude was not corrected")
            if row["coordinate_status"] != "corrected":
                add_error(errors, f"{row_label}: Brovello correction is not labelled")
        else:
            if latitude != legacy_latitude or longitude != legacy_longitude:
                add_error(errors, f"{row_label}: undocumented coordinate change")
            expected_status = "missing" if not latitude else "available"
            if row["coordinate_status"] != expected_status:
                add_error(errors, f"{row_label}: wrong coordinate_status")

        record_type_counts[row["record_type"]] += 1
        coordinate_status_counts[row["coordinate_status"]] += 1

    missing_legacy = set(legacy_by_uuid) - canonical_legacy_ids
    if missing_legacy:
        add_error(errors, f"canonical output dropped {len(missing_legacy)} legacy UUIDs")
    if corrected_rows != 1:
        add_error(errors, f"expected exactly one corrected row, found {corrected_rows}")

    if coordinate_status_counts["missing"]:
        warnings.append(
            f"{coordinate_status_counts['missing']} records still lack coordinates"
        )
    if record_type_counts["postal_locality_unclassified"]:
        warnings.append(
            f"{record_type_counts['postal_locality_unclassified']} records remain "
            "postal localities without a conservative current ISTAT municipality match"
        )
    warnings.append(
        "Legacy source provenance and the applicability of the root CC0 license remain unproven"
    )

    report = {
        "status": "passed" if not errors else "failed",
        "canonical_sha256": hashlib.sha256(args.canonical.read_bytes()).hexdigest(),
        "legacy_sha256": legacy_sha256,
        "istat_sha256": istat_sha256,
        "canonical_rows": len(canonical_rows),
        "removed_all_null_rows": removed_all_null,
        "record_type_counts": dict(sorted(record_type_counts.items())),
        "coordinate_status_counts": dict(sorted(coordinate_status_counts.items())),
        "corrected_rows": corrected_rows,
        "errors": errors,
        "warnings": warnings,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
