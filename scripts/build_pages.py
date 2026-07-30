#!/usr/bin/env python3
"""Build the deterministic static GitHub Pages site."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from project_metadata import (
    BUILD_DATE,
    DATASET_VERSION,
    GEONAMES_REFERENCE_DATE,
    ISTAT_REFERENCE_DATE,
    OPERATIONAL_DATA_READINESS,
    RELEASE_STATUS,
    SCHEMA_VERSION,
    STRUCTURAL_QUALITY,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_SITE = REPOSITORY_ROOT / "site"
CANONICAL_DATA = REPOSITORY_ROOT / "data" / "italian_locations.csv"
SOCIAL_PREVIEW = REPOSITORY_ROOT / "assets" / "social-preview.jpg"
DEFAULT_OUTPUT = REPOSITORY_ROOT / "dist" / "pages"
RELEASE_VERSION = DATASET_VERSION

WEB_FIELDS = (
    "location_id",
    "name",
    "normalized_name",
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
    "reconciliation_confidence",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_locations(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        missing = set(WEB_FIELDS) - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Canonical dataset is missing fields: {sorted(missing)}")

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
    unique_locations = {
        row["location_id"]: row for row in reversed(rows)
    }
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


def prepare_output(output: Path) -> None:
    output = output.resolve()
    forbidden = {
        Path("/").resolve(),
        REPOSITORY_ROOT.resolve(),
        SOURCE_SITE.resolve(),
        CANONICAL_DATA.parent.resolve(),
    }
    if output in forbidden:
        raise ValueError(f"Refusing unsafe output directory: {output}")
    if output.exists():
        shutil.rmtree(output)
    shutil.copytree(SOURCE_SITE, output)


def build_site(output: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    output = output.resolve()
    prepare_output(output)

    rows = read_locations(CANONICAL_DATA)
    stats = calculate_stats(rows)
    payload = {
        "metadata": {
            "release": RELEASE_VERSION,
            "release_status": RELEASE_STATUS,
            "schema_version": SCHEMA_VERSION,
            "build_date": BUILD_DATE,
            "structural_quality": STRUCTURAL_QUALITY,
            "operational_data_readiness": OPERATIONAL_DATA_READINESS,
            "istat_reference_date": ISTAT_REFERENCE_DATE,
            "geonames_reference_date": GEONAMES_REFERENCE_DATE,
            "canonical_source_ids": [
                "istat_municipalities",
                "geonames_postal_codes",
            ],
            "attribution": {
                "istat": "ISTAT — CC BY 4.0",
                "geonames": (
                    "GeoNames postal code dump — CC BY 4.0 — "
                    "https://www.geonames.org/"
                ),
            },
            "warning": (
                "GeoNames is not Poste Italiane. CAP and coordinates are "
                "non-official and provided without warranty."
            ),
        },
        "stats": stats,
        "rows": rows,
    }

    assets = output / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    locations_path = assets / "locations.json"
    locations_path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    shutil.copy2(SOCIAL_PREVIEW, assets / "social-preview.jpg")
    (output / ".nojekyll").write_text("", encoding="utf-8")
    (output / "robots.txt").write_text(
        "User-agent: *\nAllow: /\n"
        "Sitemap: https://codewriter90x.github.io/Italian_Cities/sitemap.xml\n",
        encoding="utf-8",
    )
    (output / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        "  <url>\n"
        "    <loc>https://codewriter90x.github.io/Italian_Cities/</loc>\n"
        "  </url>\n"
        "</urlset>\n",
        encoding="utf-8",
    )

    manifest = {
        "release": RELEASE_VERSION,
        "canonical_rows": len(rows),
        "canonical_sha256": sha256(CANONICAL_DATA),
        "locations_json_sha256": sha256(locations_path),
        "stats": stats,
    }
    (output / "build-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Destination directory (default: dist/pages)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = build_site(args.output)
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
