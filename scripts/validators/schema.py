"""Schema, identifier and postal-code validators."""

from __future__ import annotations

import re

from build_dataset import GENERIC_MULTICAP_POSTAL_CODES
from validators.common import QualityChecks, add_quality_error


def validate_unique_key(
    *,
    rows: list[dict[str, str]],
    fields: tuple[str, ...],
    dataset: str,
    errors: list[str],
    checks: QualityChecks,
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
    checks: QualityChecks,
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


def validate_postal_code_table(
    *,
    rows: list[dict[str, str]],
    dataset: str,
    errors: list[str],
    checks: QualityChecks,
) -> None:
    for line_number, row in enumerate(rows, start=2):
        if not re.fullmatch(r"\d{5}", row["postal_code"]):
            add_quality_error(
                errors,
                checks,
                "postal_code_format",
                f"{dataset}:{line_number}: CAP must contain exactly five digits",
            )


def validate_postal_semantics(
    *,
    rows: list[dict[str, str]],
    dataset: str,
    errors: list[str],
    checks: QualityChecks,
) -> None:
    allowed = {"generic_multicap", "legacy_unverified", "verified", "obsolete"}
    for line_number, row in enumerate(rows, start=2):
        status = row["postal_code_status"]
        label = f"{dataset}:{line_number}"
        if status not in allowed:
            add_quality_error(
                errors,
                checks,
                "postal_code_semantics",
                f"{label}: unsupported postal_code_status {status!r}",
            )
            continue
        if "normalized_name" not in row:
            continue
        key = (
            row["normalized_name"],
            row["province_code"],
            row["postal_code"],
        )
        if key in GENERIC_MULTICAP_POSTAL_CODES and status != "generic_multicap":
            add_quality_error(
                errors,
                checks,
                "postal_code_semantics",
                f"{label}: expected postal_code_status='generic_multicap'",
            )
        elif key not in GENERIC_MULTICAP_POSTAL_CODES and status == "generic_multicap":
            add_quality_error(
                errors,
                checks,
                "postal_code_semantics",
                f"{label}: generic_multicap is not declared for this record",
            )


def expected_municipality(row: dict[str, str]) -> dict[str, str]:
    return {
        "municipality_id": row["location_id"],
        "istat_code": row["municipality_istat_code"],
        "legacy_uuid": row["legacy_uuid"],
        "name": row["name"],
        "normalized_name": row["normalized_name"],
        "postal_code": row["postal_code"],
        "postal_code_status": row["postal_code_status"],
        "province_code": row["province_code"],
        "province_name": row["province_name"],
        "legacy_province_name": row["legacy_province_name"],
        "region_name": row["region_name"],
        "country_code": row["country_code"],
        "country_name": row["country_name"],
        "latitude": row["latitude"],
        "longitude": row["longitude"],
        "coordinate_status": row["coordinate_status"],
        "coordinate_verification": row["coordinate_verification"],
        "source_snapshot": row["source_snapshot"],
        "source_ids": row["source_ids"],
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
        "postal_code_status": row["postal_code_status"],
        "province_code": row["province_code"],
        "province_name": row["province_name"],
        "legacy_province_name": row["legacy_province_name"],
        "region_name": row["region_name"],
        "country_code": row["country_code"],
        "country_name": row["country_name"],
        "latitude": row["latitude"],
        "longitude": row["longitude"],
        "coordinate_status": row["coordinate_status"],
        "coordinate_verification": row["coordinate_verification"],
        "source_snapshot": row["source_snapshot"],
        "source_ids": row["source_ids"],
    }


def expected_postal_code(row: dict[str, str]) -> dict[str, str]:
    return {
        "location_id": row["location_id"],
        "location_kind": row["location_kind"],
        "postal_code": row["postal_code"],
        "postal_code_status": row["postal_code_status"],
        "province_code": row["province_code"],
        "is_primary": "true",
        "source_snapshot": row["source_snapshot"],
        "source_ids": row["source_ids"],
    }
