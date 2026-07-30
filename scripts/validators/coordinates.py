"""Coordinate value and geographic-bounds validators."""

from __future__ import annotations

import math

from validators.common import QualityChecks, add_quality_error


ITALY_BOUNDS = {
    "latitude_min": 35.0,
    "latitude_max": 48.0,
    "longitude_min": 6.0,
    "longitude_max": 19.0,
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
        label = f"{dataset}:{line_number}"
        if bool(latitude) != bool(longitude):
            add_quality_error(
                errors, checks, "numeric_coordinates", f"{label}: partial coordinate pair"
            )
            continue
        if not latitude:
            continue
        try:
            lat = float(latitude)
            lon = float(longitude)
        except ValueError:
            add_quality_error(
                errors, checks, "numeric_coordinates", f"{label}: non-numeric coordinates"
            )
            continue
        if not (math.isfinite(lat) and math.isfinite(lon)):
            add_quality_error(
                errors, checks, "numeric_coordinates", f"{label}: non-finite coordinates"
            )
            continue
        if not (
            ITALY_BOUNDS["latitude_min"] <= lat <= ITALY_BOUNDS["latitude_max"]
            and ITALY_BOUNDS["longitude_min"] <= lon <= ITALY_BOUNDS["longitude_max"]
        ):
            add_quality_error(
                errors,
                checks,
                "coordinate_bounds",
                f"{label}: coordinates outside broad Italy bounds",
            )
