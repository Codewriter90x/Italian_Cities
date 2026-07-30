"""Data loading and aggregation for the static Pages build."""

from __future__ import annotations

import csv
import re
import unicodedata
from pathlib import Path
from typing import Any

WEB_FIELDS = (
    "location_id",
    "name",
    "location_kind",
    "municipality_istat_code",
    "postal_code",
    "postal_code_status",
    "province_code",
    "province_name",
    "region_name",
    "latitude",
    "longitude",
    "coordinate_verification",
    "coordinate_accuracy",
    "reconciliation_outcome",
)


def read_locations(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        missing = set(WEB_FIELDS) - set(reader.fieldnames or [])
        if missing:
            raise ValueError(
                f"Canonical dataset is missing fields: {sorted(missing)}"
            )

        rows: list[dict[str, Any]] = []
        for source in reader:
            latitude = source["latitude"].strip()
            longitude = source["longitude"].strip()
            if bool(latitude) != bool(longitude):
                raise ValueError(
                    f"Coordinate pair is incomplete for {source['location_id']}"
                )
            row = {field: source[field] for field in WEB_FIELDS}
            row["latitude"] = float(latitude) if latitude else None
            row["longitude"] = float(longitude) if longitude else None
            rows.append(row)
    return rows


def calculate_stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    unique_locations = {row["location_id"]: row for row in reversed(rows)}
    location_rows = list(unique_locations.values())
    with_coordinates = [
        row
        for row in location_rows
        if row["latitude"] is not None and row["longitude"] is not None
    ]
    latitudes = [row["latitude"] for row in with_coordinates]
    longitudes = [row["longitude"] for row in with_coordinates]
    return {
        "total_locations": len(location_rows),
        "postal_code_relations": len(rows),
        "municipalities": sum(
            row["location_kind"] == "municipality" for row in location_rows
        ),
        "unclassified_localities": sum(
            row["location_kind"] != "municipality" for row in location_rows
        ),
        "unique_postal_codes": len(
            {row["postal_code"] for row in rows if row["postal_code"]}
        ),
        "with_coordinates": len(with_coordinates),
        "missing_coordinates": len(location_rows) - len(with_coordinates),
        "geonames_place_match_coordinates": sum(
            row["coordinate_verification"] == "geonames_place_match"
            for row in location_rows
        ),
        "geonames_estimated_coordinates": sum(
            row["coordinate_verification"] == "geonames_estimated"
            for row in location_rows
        ),
        "missing_postal_code_municipalities": sum(
            row["postal_code_status"] == "missing" for row in rows
        ),
        "provinces": len({row["province_code"] for row in rows}),
        "regions": len({row["region_name"] for row in rows}),
        "bounds": {
            "min_latitude": min(latitudes),
            "max_latitude": max(latitudes),
            "min_longitude": min(longitudes),
            "max_longitude": max(longitudes),
        },
    }


def format_integer(value: int) -> str:
    return f"{value:,}".replace(",", ".")


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", ascii_value.casefold()).strip("-")
