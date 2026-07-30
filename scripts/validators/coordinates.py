"""Coordinate value, geographic-bound and verification validators."""

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from typing import Any

from validators.common import QualityChecks, add_quality_error

ITALY_BOUNDS = {
    "latitude_min": 35.0,
    "latitude_max": 48.0,
    "longitude_min": 6.0,
    "longitude_max": 19.0,
}
COORDINATE_VERIFICATIONS = {
    "geonames_estimated",
    "geonames_place_match",
    "official_boundary_derived",
    "missing",
}
SHARED_COORDINATE_REVIEW_THRESHOLD = 10


def analyze_coordinate_distribution(
    rows: list[dict[str, str]],
) -> dict[str, Any]:
    """Profile exact coordinate reuse at unique-location grain."""

    unique_locations: dict[str, dict[str, str]] = {}
    for row in rows:
        location_id = row.get("location_id") or row.get("municipality_id")
        if location_id:
            unique_locations.setdefault(location_id, row)

    groups: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in unique_locations.values():
        latitude = row.get("latitude", "")
        longitude = row.get("longitude", "")
        if latitude and longitude:
            groups[(latitude, longitude)].append(row)

    shared = [
        (coordinate, members)
        for coordinate, members in groups.items()
        if len(members) > 1
    ]
    shared.sort(key=lambda item: (-len(item[1]), item[0]))
    details: list[dict[str, Any]] = []
    for (latitude, longitude), members in shared:
        ordered = sorted(
            members,
            key=lambda row: (
                row.get("location_kind", ""),
                row.get("name", ""),
                row.get("location_id", row.get("municipality_id", "")),
            ),
        )
        details.append(
            {
                "latitude": float(latitude),
                "longitude": float(longitude),
                "location_count": len(ordered),
                "municipality_count": sum(
                    row.get("location_kind") == "municipality"
                    or bool(row.get("municipality_id"))
                    for row in ordered
                ),
                "verification_counts": dict(
                    sorted(
                        Counter(
                            row.get("coordinate_verification", "")
                            for row in ordered
                        ).items()
                    )
                ),
                "locations": [
                    {
                        "location_id": row.get(
                            "location_id",
                            row.get("municipality_id", ""),
                        ),
                        "name": row.get("name", ""),
                        "province_code": row.get("province_code", ""),
                        "region_name": row.get("region_name", ""),
                    }
                    for row in ordered
                ],
            }
        )

    review_groups = [
        group
        for group in details
        if group["location_count"] >= SHARED_COORDINATE_REVIEW_THRESHOLD
    ]
    return {
        "grain": "unique_location",
        "exact_shared_coordinate_groups": len(details),
        "locations_in_shared_coordinate_groups": sum(
            group["location_count"] for group in details
        ),
        "largest_shared_coordinate_group": (
            details[0]["location_count"] if details else 0
        ),
        "review_threshold": SHARED_COORDINATE_REVIEW_THRESHOLD,
        "groups_requiring_review": len(review_groups),
        "interpretation": (
            "Exact coordinate reuse is a source-quality signal, not automatic "
            "proof of an error. geonames_place_match records a conservative "
            "name and territory match; it does not certify coordinate accuracy."
        ),
        "review_groups": review_groups,
    }


def validate_coordinate_table(
    *,
    rows: list[dict[str, str]],
    dataset: str,
    errors: list[str],
    checks: QualityChecks,
) -> None:
    for line_number, row in enumerate(rows, start=2):
        latitude = row["latitude"]
        longitude = row["longitude"]
        verification = row["coordinate_verification"]
        accuracy = row.get("coordinate_accuracy", "")
        label = f"{dataset}:{line_number}"
        if verification not in COORDINATE_VERIFICATIONS:
            add_quality_error(
                errors,
                checks,
                "coordinate_verification",
                f"{label}: unsupported coordinate verification",
            )
        if verification == "official_boundary_derived":
            add_quality_error(
                errors,
                checks,
                "coordinate_verification",
                f"{label}: official_boundary_derived is reserved",
            )
        if bool(latitude) != bool(longitude):
            add_quality_error(
                errors,
                checks,
                "numeric_coordinates",
                f"{label}: partial coordinate pair",
            )
            continue
        if not latitude:
            if verification != "missing" or accuracy:
                add_quality_error(
                    errors,
                    checks,
                    "coordinate_verification",
                    f"{label}: missing coordinates require missing "
                    "verification and empty accuracy",
                )
            continue
        if verification not in {
            "geonames_estimated",
            "geonames_place_match",
        }:
            add_quality_error(
                errors,
                checks,
                "coordinate_verification",
                f"{label}: GeoNames coordinates must be labelled as such",
            )
        if not re.fullmatch(r"[1-6]", accuracy):
            add_quality_error(
                errors,
                checks,
                "coordinate_verification",
                f"{label}: GeoNames accuracy must be preserved",
            )
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
