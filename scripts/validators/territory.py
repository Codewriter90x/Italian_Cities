"""ISTAT municipality and administrative-territory validators."""

from __future__ import annotations

import re

from dataset_common import normalize_name

from validators.common import QualityChecks, add_quality_error


def territorial_names_compatible(left: str, right: str) -> bool:
    aliases = {"abruzzi": "abruzzo"}
    left_key = aliases.get(normalize_name(left), normalize_name(left))
    right_key = aliases.get(normalize_name(right), normalize_name(right))
    return (
        left_key == right_key
        or left_key.startswith(f"{right_key} ")
        or right_key.startswith(f"{left_key} ")
    )


def validate_territories(
    *,
    municipalities: list[dict[str, str]],
    localities: list[dict[str, str]],
    official_records: list[dict[str, str]],
    errors: list[str],
    checks: QualityChecks,
) -> None:
    official_by_code = {
        row["istat_code"]: row for row in official_records
    }
    municipality_codes = {row["istat_code"] for row in municipalities}
    if municipality_codes != set(official_by_code):
        add_quality_error(
            errors,
            checks,
            "istat_code_validity",
            "municipalities.csv must contain every municipality from ISTAT "
            "exactly once",
        )
    provinces = {
        row["province_code"]: (row["province_name"], row["region_name"])
        for row in official_records
    }
    for line_number, row in enumerate(municipalities, start=2):
        label = f"data/municipalities.csv:{line_number}"
        if not re.fullmatch(r"\d{6}", row["istat_code"]):
            add_quality_error(
                errors,
                checks,
                "istat_code_validity",
                f"{label}: ISTAT code must contain six digits",
            )
            continue
        official = official_by_code.get(row["istat_code"])
        if official is None:
            continue
        for field in (
            "name",
            "province_code",
            "province_name",
            "region_name",
        ):
            if row[field] != official[field]:
                add_quality_error(
                    errors,
                    checks,
                    "territorial_coherence",
                    f"{label}: {field} differs from ISTAT",
                )
        if row["municipality_id"] != f"IT-COM-{row['istat_code']}":
            add_quality_error(
                errors,
                checks,
                "istat_code_validity",
                f"{label}: municipality_id disagrees with ISTAT code",
            )
    for line_number, row in enumerate(localities, start=2):
        territory = provinces.get(row["province_code"])
        if territory is None:
            if (
                row["source_id"] != "geonames_postal_codes"
                or row["reconciliation_outcome"] != "unmatched_no_parent"
            ):
                add_quality_error(
                    errors,
                    checks,
                    "territorial_coherence",
                    f"data/localities.csv:{line_number}: unknown province "
                    "code is allowed only for an unreconciled GeoNames place",
                )
        elif (
            row["province_name"],
            row["region_name"],
        ) != territory:
            add_quality_error(
                errors,
                checks,
                "territorial_coherence",
                f"data/localities.csv:{line_number}: province or region "
                "differs from ISTAT",
            )
