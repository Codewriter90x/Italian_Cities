#!/usr/bin/env python3
"""Shared schema and deterministic I/O helpers for the data pipeline."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import unicodedata
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
REPORTS_DIR = ROOT / "reports"
MILESTONE1_BASELINE = (
    ROOT / "legacy/milestone-1-canonical/italian_postal_localities.csv"
)
SOURCE_MANIFEST = ROOT / "sources/manifest.json"

V1_ITALIAN_LOCATION_FIELDS = (
    "location_id",
    "legacy_uuid",
    "name",
    "normalized_name",
    "location_kind",
    "municipality_istat_code",
    "parent_municipality_id",
    "postal_code",
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

MUNICIPALITY_FIELDS = (
    "municipality_id",
    "istat_code",
    "legacy_uuid",
    "name",
    "normalized_name",
    "postal_code",
    "postal_code_status",
    "province_code",
    "province_name",
    "legacy_province_name",
    "region_name",
    "country_code",
    "country_name",
    "latitude",
    "longitude",
    "coordinate_status",
    "coordinate_verification",
    "source_snapshot",
    "source_ids",
)

LOCALITY_FIELDS = (
    "locality_id",
    "legacy_uuid",
    "name",
    "normalized_name",
    "locality_type",
    "parent_municipality_id",
    "postal_code",
    "postal_code_status",
    "province_code",
    "province_name",
    "legacy_province_name",
    "region_name",
    "country_code",
    "country_name",
    "latitude",
    "longitude",
    "coordinate_status",
    "coordinate_verification",
    "source_snapshot",
    "source_ids",
)

POSTAL_CODE_FIELDS = (
    "location_id",
    "location_kind",
    "postal_code",
    "postal_code_status",
    "province_code",
    "is_primary",
    "source_snapshot",
    "source_ids",
)

ITALIAN_LOCATION_FIELDS = (
    "location_id",
    "legacy_uuid",
    "name",
    "normalized_name",
    "location_kind",
    "municipality_istat_code",
    "parent_municipality_id",
    "postal_code",
    "postal_code_status",
    "province_code",
    "province_name",
    "legacy_province_name",
    "region_name",
    "country_code",
    "country_name",
    "latitude",
    "longitude",
    "coordinate_status",
    "coordinate_verification",
    "source_snapshot",
    "source_ids",
)

GENERATED_PATHS = {
    "municipalities": DATA_DIR / "municipalities.csv",
    "localities": DATA_DIR / "localities.csv",
    "postal_codes": DATA_DIR / "postal_codes.csv",
    "italian_locations": DATA_DIR / "italian_locations.csv",
    "json": DATA_DIR / "italian_locations.json",
    "xlsx": DATA_DIR / "italian_locations.xlsx",
    "sqlite": DATA_DIR / "italian_locations.sqlite",
}


def normalize_name(value: str) -> str:
    """Return an accent-, apostrophe- and case-insensitive search key."""

    value = (value or "").replace("’", "'").replace("`", "'").strip()
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_like = "".join(
        character
        for character in decomposed
        if not unicodedata.combining(character)
    )
    return re.sub(r"[^a-z0-9]+", " ", ascii_like.casefold()).strip()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv_rows(
    path: Path,
    expected_fields: tuple[str, ...] | None = None,
) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        fields = tuple(reader.fieldnames or ())
        if expected_fields is not None and fields != expected_fields:
            raise ValueError(
                f"{path}: header mismatch; expected {expected_fields}, found {fields}"
            )
        return [dict(row) for row in reader]


def write_csv_rows(
    path: Path,
    fields: tuple[str, ...],
    rows: Iterable[dict[str, str]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as destination:
        writer = csv.DictWriter(
            destination,
            fieldnames=fields,
            lineterminator="\n",
            extrasaction="raise",
        )
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def canonical_row_sort_key(row: dict[str, str]) -> tuple[str, ...]:
    return (
        row["normalized_name"],
        row["province_code"],
        row["postal_code"],
        row["legacy_uuid"],
    )


def record_digest(rows: Iterable[dict[str, str]]) -> str:
    serialized = json.dumps(
        list(rows),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()
