#!/usr/bin/env python3
"""Shared schema and deterministic I/O helpers for the data pipeline."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import unicodedata
from collections.abc import Iterable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
REPORTS_DIR = ROOT / "reports"
SOURCE_MANIFEST = ROOT / "sources/manifest.json"

MUNICIPALITY_FIELDS = (
    "municipality_id",
    "istat_code",
    "name",
    "normalized_name",
    "province_code",
    "province_name",
    "region_name",
    "country_code",
    "country_name",
    "latitude",
    "longitude",
    "coordinate_verification",
    "coordinate_accuracy",
    "coordinate_source_id",
    "coordinate_source_record_id",
    "coordinate_source_date",
    "coordinate_method",
    "coordinate_confidence",
    "administrative_source_id",
    "administrative_source_record_id",
    "administrative_source_date",
    "source_ids",
)

LOCALITY_FIELDS = (
    "locality_id",
    "name",
    "normalized_name",
    "locality_type",
    "parent_municipality_id",
    "candidate_municipality_ids",
    "province_code",
    "province_name",
    "region_name",
    "country_code",
    "country_name",
    "latitude",
    "longitude",
    "coordinate_verification",
    "coordinate_accuracy",
    "source_id",
    "source_record_ids",
    "source_reference_date",
    "reconciliation_outcome",
    "reconciliation_method",
    "reconciliation_confidence",
)

POSTAL_CODE_FIELDS = (
    "postal_code_relation_id",
    "location_id",
    "location_kind",
    "postal_code",
    "postal_code_status",
    "province_code",
    "is_primary",
    "source_id",
    "source_record_ids",
    "source_reference_date",
    "match_method",
    "confidence",
    "accuracy",
)

ITALIAN_LOCATION_FIELDS = (
    "location_postal_id",
    "location_id",
    "name",
    "normalized_name",
    "location_kind",
    "municipality_istat_code",
    "parent_municipality_id",
    "candidate_municipality_ids",
    "postal_code",
    "postal_code_status",
    "province_code",
    "province_name",
    "region_name",
    "country_code",
    "country_name",
    "latitude",
    "longitude",
    "coordinate_verification",
    "coordinate_accuracy",
    "reconciliation_outcome",
    "reconciliation_method",
    "reconciliation_confidence",
    "source_ids",
    "source_record_ids",
    "source_reference_dates",
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
        row["location_id"],
        row["location_postal_id"],
    )


def record_digest(rows: Iterable[dict[str, str]]) -> str:
    serialized = json.dumps(
        list(rows),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()
