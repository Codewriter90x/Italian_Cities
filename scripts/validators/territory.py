"""ISTAT and municipality-province-region coherence validators."""

from __future__ import annotations

import re
from collections.abc import Mapping

from dataset_common import normalize_name
from validators.common import QualityChecks, add_quality_error


def territorial_names_compatible(left: str, right: str) -> bool:
    """Allow an official bilingual suffix while retaining legacy display labels."""

    left_key = normalize_name(left)
    right_key = normalize_name(right)
    return (
        left_key == right_key
        or left_key.startswith(f"{right_key} ")
        or right_key.startswith(f"{left_key} ")
    )


def validate_territories(
    *,
    municipalities: list[dict[str, str]],
    localities: list[dict[str, str]],
    locations: list[dict[str, str]],
    official_records: Mapping[tuple[str, str], dict[str, str]],
    errors: list[str],
    checks: QualityChecks,
) -> dict[str, dict[str, str]]:
    official_by_istat = {
        record["istat_code"]: record for record in official_records.values()
    }
    official_province_codes = {
        record["province_code"] for record in official_by_istat.values()
    }
    official_province_names = {
        record["province_code"]: record["province_name"]
        for record in official_by_istat.values()
    }
    municipality_province_codes = {row["province_code"] for row in municipalities}

    for line_number, row in enumerate(municipalities, start=2):
        label = f"data/municipalities.csv:{line_number}"
        istat_code = row["istat_code"]
        if not re.fullmatch(r"\d{6}", istat_code):
            add_quality_error(
                errors,
                checks,
                "istat_code_validity",
                f"{label}: ISTAT code must contain exactly six digits",
            )
            continue
        official = official_by_istat.get(istat_code)
        if official is None:
            add_quality_error(
                errors,
                checks,
                "istat_code_validity",
                f"{label}: ISTAT code {istat_code} is absent from the declared snapshot",
            )
            continue
        if row["municipality_id"] != f"IT-COM-{istat_code}":
            add_quality_error(
                errors,
                checks,
                "istat_code_validity",
                f"{label}: municipality_id disagrees with ISTAT code",
            )
        if row["province_code"] != official["province_code"]:
            add_quality_error(
                errors,
                checks,
                "territorial_coherence",
                f"{label}: municipality and official province code disagree",
            )
        if not territorial_names_compatible(
            row["region_name"], official["region_name"]
        ):
            add_quality_error(
                errors,
                checks,
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
                checks,
                "territorial_coherence",
                f"data/italian_locations.csv:{line_number}: "
                f"province code {province_code!r} is absent from ISTAT",
            )
            continue
        if normalize_name(row["province_name"]) != normalize_name(
            official_province_names[province_code]
        ):
            add_quality_error(
                errors,
                checks,
                "territorial_coherence",
                f"data/italian_locations.csv:{line_number}: "
                "province display name disagrees with ISTAT",
            )
        if not row["legacy_province_name"]:
            add_quality_error(
                errors,
                checks,
                "provenance_completeness",
                f"data/italian_locations.csv:{line_number}: "
                "legacy province label is missing",
            )

    for province_code, labels in sorted(territories_by_province.items()):
        if len(labels) != 1:
            add_quality_error(
                errors,
                checks,
                "territorial_coherence",
                f"province {province_code} maps to multiple province/region labels: "
                f"{sorted(labels)}",
            )
    for line_number, row in enumerate(localities, start=2):
        if row["province_code"] not in municipality_province_codes:
            add_quality_error(
                errors,
                checks,
                "territorial_coherence",
                f"data/localities.csv:{line_number}: province has no municipality",
            )

    return official_by_istat
