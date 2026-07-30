#!/usr/bin/env python3
"""Produce a bounded, deterministic comparison with the historical dataset."""

from __future__ import annotations

import csv
import math
from collections import defaultdict
from pathlib import Path

from dataset_common import normalize_name, sha256_file


LEGACY_FIELDS = (
    "legacy_uuid",
    "name",
    "postal_code",
    "province_code",
    "province_name",
    "region_name",
    "country_name",
    "latitude",
    "longitude",
    "visible",
)
NULL_VALUES = {"", "null", "none", "n/a"}
SAMPLE_LIMIT = 25


def load_legacy_records(path: Path) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    with path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.reader(source, delimiter=";")
        for line_number, values in enumerate(reader, start=1):
            if len(values) != len(LEGACY_FIELDS):
                raise ValueError(
                    f"{path}:{line_number}: expected {len(LEGACY_FIELDS)} "
                    f"fields, found {len(values)}"
                )
            if all(value.strip().casefold() in NULL_VALUES for value in values):
                continue
            row = dict(zip(LEGACY_FIELDS, values, strict=True))
            row = {
                key: "" if value.strip().casefold() in NULL_VALUES else value.strip()
                for key, value in row.items()
            }
            records.append(row)
    records.sort(
        key=lambda row: (
            normalize_name(row["name"]),
            row["province_code"],
            row["postal_code"],
            row["legacy_uuid"],
        )
    )
    return records


def _key(row: dict[str, str]) -> tuple[str, str, str]:
    return (
        normalize_name(row["name"]),
        row["province_code"],
        row["postal_code"],
    )


def _sample_keys(keys: set[tuple[str, str, str]]) -> list[dict[str, str]]:
    return [
        {
            "normalized_name": name,
            "province_code": province,
            "postal_code": postal_code,
        }
        for name, province, postal_code in sorted(keys)[:SAMPLE_LIMIT]
    ]


def _sample_name_cap(keys: set[tuple[str, str]]) -> list[dict[str, str]]:
    return [
        {
            "normalized_name": name,
            "postal_code": postal_code,
        }
        for name, postal_code in sorted(keys)[:SAMPLE_LIMIT]
    ]


def build_legacy_comparison(
    legacy_path: Path,
    current_rows: list[dict[str, str]],
) -> dict[str, object]:
    legacy_rows = load_legacy_records(legacy_path)
    geonames_rows = [
        row
        for row in current_rows
        if "geonames_postal_codes" in row["source_ids"] and row["postal_code"]
    ]
    legacy_keys = {_key(row) for row in legacy_rows}
    geonames_keys = {_key(row) for row in geonames_rows}
    exact = legacy_keys & geonames_keys
    only_legacy = legacy_keys - geonames_keys
    only_geonames = geonames_keys - legacy_keys
    legacy_name_cap = {
        (normalize_name(row["name"]), row["postal_code"])
        for row in legacy_rows
    }
    geonames_name_cap = {
        (normalize_name(row["name"]), row["postal_code"])
        for row in geonames_rows
    }
    exact_name_cap = legacy_name_cap & geonames_name_cap

    legacy_caps: dict[tuple[str, str], set[str]] = defaultdict(set)
    geonames_caps: dict[tuple[str, str], set[str]] = defaultdict(set)
    for row in legacy_rows:
        legacy_caps[(normalize_name(row["name"]), row["province_code"])].add(
            row["postal_code"]
        )
    for row in geonames_rows:
        geonames_caps[(normalize_name(row["name"]), row["province_code"])].add(
            row["postal_code"]
        )
    cap_disagreements = []
    for name_province in sorted(set(legacy_caps) & set(geonames_caps)):
        if legacy_caps[name_province] != geonames_caps[name_province]:
            cap_disagreements.append(
                {
                    "normalized_name": name_province[0],
                    "province_code": name_province[1],
                    "legacy_postal_codes": sorted(legacy_caps[name_province]),
                    "geonames_postal_codes": sorted(
                        geonames_caps[name_province]
                    ),
                }
            )

    current_by_key = {_key(row): row for row in geonames_rows}
    coordinate_disagreements = []
    for legacy in legacy_rows:
        current = current_by_key.get(_key(legacy))
        if (
            current is None
            or not legacy["latitude"]
            or not legacy["longitude"]
            or not current["latitude"]
            or not current["longitude"]
        ):
            continue
        try:
            distance = math.hypot(
                float(legacy["latitude"]) - float(current["latitude"]),
                float(legacy["longitude"]) - float(current["longitude"]),
            )
        except ValueError:
            continue
        if distance > 0.01:
            coordinate_disagreements.append(
                {
                    "normalized_name": normalize_name(legacy["name"]),
                    "province_code": legacy["province_code"],
                    "postal_code": legacy["postal_code"],
                    "legacy_coordinates": [
                        legacy["latitude"],
                        legacy["longitude"],
                    ],
                    "geonames_coordinates": [
                        current["latitude"],
                        current["longitude"],
                    ],
                    "angular_distance_degrees": round(distance, 6),
                }
            )
    coordinate_disagreements.sort(
        key=lambda row: (
            row["normalized_name"],
            row["province_code"],
            row["postal_code"],
        )
    )

    legacy_total = len(legacy_keys)
    geonames_total = len(geonames_keys)
    return {
        "report_type": "historical_investigative_comparison",
        "provenance_warning": (
            "A match is only a similarity between snapshots and is not proof "
            "of the legacy dataset's original source."
        ),
        "legacy_role": "historical_comparison_only",
        "legacy": {
            "path": "legacy/2023-05-02-original/Italian Cities.csv",
            "sha256": sha256_file(legacy_path),
            "records": len(legacy_rows),
            "logical_name_cap_records": legacy_total,
        },
        "current_geonames": {
            "logical_name_cap_records": geonames_total,
        },
        "counts": {
            "exact_name_postal_code": len(exact_name_cap),
            "exact_name_province_postal_code": len(exact),
            "only_legacy": len(only_legacy),
            "only_geonames": len(only_geonames),
            "postal_code_disagreements": len(cap_disagreements),
            "coordinate_disagreements_over_0_01_degrees": len(
                coordinate_disagreements
            ),
        },
        "percentages": {
            "legacy_exact_name_postal_code_percent": round(
                len(exact_name_cap) / len(legacy_name_cap) * 100, 2
            )
            if legacy_name_cap
            else 0,
            "legacy_exact_match_percent": round(
                len(exact) / legacy_total * 100, 2
            )
            if legacy_total
            else 0,
            "geonames_exact_match_percent": round(
                len(exact) / geonames_total * 100, 2
            )
            if geonames_total
            else 0,
        },
        "samples": {
            "exact_name_postal_code": _sample_name_cap(exact_name_cap),
            "exact_name_province_postal_code": _sample_keys(exact),
            "only_legacy": _sample_keys(only_legacy),
            "only_geonames": _sample_keys(only_geonames),
            "postal_code_disagreements": cap_disagreements[:SAMPLE_LIMIT],
            "coordinate_disagreements": coordinate_disagreements[
                :SAMPLE_LIMIT
            ],
        },
        "samples_truncated": {
            "exact_name_postal_code": len(exact_name_cap) > SAMPLE_LIMIT,
            "exact_name_province_postal_code": len(exact) > SAMPLE_LIMIT,
            "only_legacy": len(only_legacy) > SAMPLE_LIMIT,
            "only_geonames": len(only_geonames) > SAMPLE_LIMIT,
            "postal_code_disagreements": len(cap_disagreements) > SAMPLE_LIMIT,
            "coordinate_disagreements": (
                len(coordinate_disagreements) > SAMPLE_LIMIT
            ),
        },
        "possible_source_clues": {
            "shared_name_cap_pairs": len(exact),
            "interpretation": (
                "Shared values may indicate common upstream facts or later "
                "reuse, but cannot establish the legacy source."
            ),
        },
    }
