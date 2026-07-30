"""Coordinate value, geographic-bound and verification validators."""

from __future__ import annotations

import math
import re

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
