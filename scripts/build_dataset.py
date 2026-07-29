#!/usr/bin/env python3
"""Build all Milestone 2 tabular datasets from declared source snapshots."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from dataset_common import (
    GENERATED_PATHS,
    ITALIAN_LOCATION_FIELDS,
    LOCALITY_FIELDS,
    MILESTONE1_BASELINE,
    MUNICIPALITY_FIELDS,
    POSTAL_CODE_FIELDS,
    REPORTS_DIR,
    SOURCE_MANIFEST,
    canonical_row_sort_key,
    normalize_name,
    read_csv_rows,
    sha256_file,
    write_csv_rows,
    write_json,
)
from normalize_legacy import (
    CANONICAL_FIELDS as MILESTONE1_FIELDS,
    DEFAULT_ISTAT,
    DEFAULT_LEGACY,
    canonicalize,
    load_istat_municipalities,
    load_legacy_rows,
)


BUILD_DATE = "2026-07-29"
SCHEMA_VERSION = "2.0.0"
DEFAULT_DIFF_REPORT = REPORTS_DIR / "milestone2-diff.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--legacy", type=Path, default=DEFAULT_LEGACY)
    parser.add_argument("--istat", type=Path, default=DEFAULT_ISTAT)
    parser.add_argument("--baseline", type=Path, default=MILESTONE1_BASELINE)
    parser.add_argument("--manifest", type=Path, default=SOURCE_MANIFEST)
    parser.add_argument("--diff-report", type=Path, default=DEFAULT_DIFF_REPORT)
    parser.add_argument(
        "--no-exports",
        action="store_true",
        help="Build CSV tables and diff report without JSON/XLSX/SQLite exports.",
    )
    return parser.parse_args()


def validate_declared_sources(
    manifest_path: Path,
    *,
    legacy_path: Path,
    istat_path: Path,
    baseline_path: Path,
) -> dict[str, object]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    declared = {source["id"]: source for source in manifest["sources"]}
    actual_paths = {
        "legacy_csv": legacy_path,
        "istat_municipalities": istat_path,
        "milestone1_baseline": baseline_path,
    }
    for source_id, path in actual_paths.items():
        if source_id not in declared:
            raise ValueError(f"{manifest_path}: missing source declaration {source_id}")
        if not path.exists():
            raise FileNotFoundError(
                f"declared source {source_id} is missing at {path}; "
                "see sources/README.md"
            )
        actual_sha256 = sha256_file(path)
        expected_sha256 = declared[source_id]["sha256"]
        if actual_sha256 != expected_sha256:
            raise ValueError(
                f"declared source {source_id} checksum mismatch: "
                f"{actual_sha256} != {expected_sha256}"
            )
    return manifest


def load_current_milestone1_rows(
    legacy_path: Path,
    istat_path: Path,
) -> list[dict[str, str]]:
    legacy_rows, removed_all_null = load_legacy_rows(legacy_path)
    if removed_all_null != 1:
        raise ValueError(
            f"expected one all-NULL legacy row, found {removed_all_null}"
        )
    municipalities = load_istat_municipalities(istat_path)
    rows, _ = canonicalize(legacy_rows, municipalities)
    return rows


def build_italian_locations(
    milestone1_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    for row in milestone1_rows:
        output.append(
            {
                "location_id": row["location_id"],
                "legacy_uuid": row["legacy_uuid"],
                "name": row["name"],
                "normalized_name": normalize_name(row["name"]),
                "location_kind": row["record_type"],
                "municipality_istat_code": row["municipality_istat_code"],
                "parent_municipality_id": "",
                "postal_code": row["postal_code"],
                "province_code": row["province_code"],
                "province_name": row["province_name"],
                "region_name": row["region_name"],
                "country_code": row["country_code"],
                "country_name": row["country_name"],
                "latitude": row["latitude"],
                "longitude": row["longitude"],
                "coordinate_status": row["coordinate_status"],
                "source_snapshot": row["source_snapshot"],
            }
        )
    output.sort(key=canonical_row_sort_key)
    return output


def split_tables(
    locations: list[dict[str, str]],
) -> tuple[
    list[dict[str, str]],
    list[dict[str, str]],
    list[dict[str, str]],
]:
    municipalities: list[dict[str, str]] = []
    localities: list[dict[str, str]] = []
    postal_codes: list[dict[str, str]] = []

    for row in locations:
        common = {
            "legacy_uuid": row["legacy_uuid"],
            "name": row["name"],
            "normalized_name": row["normalized_name"],
            "postal_code": row["postal_code"],
            "province_code": row["province_code"],
            "province_name": row["province_name"],
            "region_name": row["region_name"],
            "country_code": row["country_code"],
            "country_name": row["country_name"],
            "latitude": row["latitude"],
            "longitude": row["longitude"],
            "coordinate_status": row["coordinate_status"],
            "source_snapshot": row["source_snapshot"],
        }
        if row["location_kind"] == "municipality":
            municipalities.append(
                {
                    "municipality_id": row["location_id"],
                    "istat_code": row["municipality_istat_code"],
                    **common,
                }
            )
        else:
            localities.append(
                {
                    "locality_id": row["location_id"],
                    "legacy_uuid": row["legacy_uuid"],
                    "name": row["name"],
                    "normalized_name": row["normalized_name"],
                    "locality_type": row["location_kind"],
                    "parent_municipality_id": row["parent_municipality_id"],
                    "postal_code": row["postal_code"],
                    "province_code": row["province_code"],
                    "province_name": row["province_name"],
                    "region_name": row["region_name"],
                    "country_code": row["country_code"],
                    "country_name": row["country_name"],
                    "latitude": row["latitude"],
                    "longitude": row["longitude"],
                    "coordinate_status": row["coordinate_status"],
                    "source_snapshot": row["source_snapshot"],
                }
            )

        postal_codes.append(
            {
                "location_id": row["location_id"],
                "location_kind": row["location_kind"],
                "postal_code": row["postal_code"],
                "province_code": row["province_code"],
                "is_primary": "true",
                "source_snapshot": row["source_snapshot"],
            }
        )

    municipalities.sort(
        key=lambda row: (
            row["normalized_name"],
            row["province_code"],
            row["postal_code"],
            row["municipality_id"],
        )
    )
    localities.sort(
        key=lambda row: (
            row["normalized_name"],
            row["province_code"],
            row["postal_code"],
            row["locality_id"],
        )
    )
    postal_codes.sort(
        key=lambda row: (
            row["postal_code"],
            row["location_kind"],
            row["location_id"],
        )
    )
    return municipalities, localities, postal_codes


def comparable_milestone1_row(row: dict[str, str]) -> dict[str, str]:
    return {
        "location_id": row["location_id"],
        "legacy_uuid": row["legacy_uuid"],
        "name": row["name"],
        "location_kind": row["record_type"],
        "municipality_istat_code": row["municipality_istat_code"],
        "postal_code": row["postal_code"],
        "province_code": row["province_code"],
        "province_name": row["province_name"],
        "region_name": row["region_name"],
        "country_code": row["country_code"],
        "country_name": row["country_name"],
        "latitude": row["latitude"],
        "longitude": row["longitude"],
        "coordinate_status": row["coordinate_status"],
        "source_snapshot": row["source_snapshot"],
    }


def comparable_milestone2_row(row: dict[str, str]) -> dict[str, str]:
    return {
        field: row[field]
        for field in (
            "location_id",
            "legacy_uuid",
            "name",
            "location_kind",
            "municipality_istat_code",
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
    }


def build_diff_report(
    baseline_path: Path,
    baseline_rows: list[dict[str, str]],
    current_rows: list[dict[str, str]],
) -> dict[str, object]:
    baseline_by_uuid = {row["legacy_uuid"]: row for row in baseline_rows}
    current_by_uuid = {row["legacy_uuid"]: row for row in current_rows}
    added = sorted(set(current_by_uuid) - set(baseline_by_uuid))
    removed = sorted(set(baseline_by_uuid) - set(current_by_uuid))
    changed: list[dict[str, object]] = []

    for legacy_uuid in sorted(set(baseline_by_uuid) & set(current_by_uuid)):
        before = comparable_milestone1_row(baseline_by_uuid[legacy_uuid])
        after = comparable_milestone2_row(current_by_uuid[legacy_uuid])
        changed_fields = [
            field for field in before if before[field] != after[field]
        ]
        if changed_fields:
            changed.append(
                {
                    "legacy_uuid": legacy_uuid,
                    "changed_fields": changed_fields,
                    "before": {field: before[field] for field in changed_fields},
                    "after": {field: after[field] for field in changed_fields},
                }
            )

    kinds = Counter(row["location_kind"] for row in current_rows)
    coordinates = Counter(row["coordinate_status"] for row in current_rows)
    return {
        "milestone": 2,
        "schema_version": SCHEMA_VERSION,
        "build_date": BUILD_DATE,
        "baseline": {
            "path": str(baseline_path.relative_to(baseline_path.parents[2])),
            "sha256": sha256_file(baseline_path),
            "rows": len(baseline_rows),
            "fields": list(MILESTONE1_FIELDS),
        },
        "current": {
            "path": "data/italian_locations.csv",
            "sha256": sha256_file(GENERATED_PATHS["italian_locations"]),
            "rows": len(current_rows),
            "fields": list(ITALIAN_LOCATION_FIELDS),
        },
        "schema_changes": {
            "added_fields": ["normalized_name", "parent_municipality_id"],
            "renamed_fields": {"record_type": "location_kind"},
            "removed_fields": [],
        },
        "record_changes": {
            "added": len(added),
            "removed": len(removed),
            "changed": len(changed),
            "unchanged": len(current_rows) - len(added) - len(changed),
            "added_legacy_uuids": added[:25],
            "removed_legacy_uuids": removed[:25],
            "changed_samples": changed[:25],
            "samples_truncated": any(
                count > 25 for count in (len(added), len(removed), len(changed))
            ),
        },
        "record_type_counts": dict(sorted(kinds.items())),
        "coordinate_status_counts": dict(sorted(coordinates.items())),
    }


def main() -> None:
    args = parse_args()
    manifest = validate_declared_sources(
        args.manifest,
        legacy_path=args.legacy,
        istat_path=args.istat,
        baseline_path=args.baseline,
    )
    current_milestone1 = load_current_milestone1_rows(args.legacy, args.istat)
    baseline_rows = read_csv_rows(args.baseline, MILESTONE1_FIELDS)
    if current_milestone1 != baseline_rows:
        raise SystemExit(
            "Declared source snapshots no longer reproduce the Milestone 1 baseline"
        )

    locations = build_italian_locations(current_milestone1)
    municipalities, localities, postal_codes = split_tables(locations)

    write_csv_rows(
        GENERATED_PATHS["municipalities"],
        MUNICIPALITY_FIELDS,
        municipalities,
    )
    write_csv_rows(GENERATED_PATHS["localities"], LOCALITY_FIELDS, localities)
    write_csv_rows(
        GENERATED_PATHS["postal_codes"],
        POSTAL_CODE_FIELDS,
        postal_codes,
    )
    write_csv_rows(
        GENERATED_PATHS["italian_locations"],
        ITALIAN_LOCATION_FIELDS,
        locations,
    )

    diff_report = build_diff_report(
        args.baseline,
        baseline_rows,
        locations,
    )
    diff_report["source_manifest"] = {
        "path": str(args.manifest.relative_to(args.manifest.parents[1])),
        "version": manifest["manifest_version"],
        "sha256": sha256_file(args.manifest),
    }
    args.diff_report.parent.mkdir(parents=True, exist_ok=True)
    write_json(args.diff_report, diff_report)

    if not args.no_exports:
        from export_formats import export_all

        export_all()

    summary = {
        "status": "built",
        "schema_version": SCHEMA_VERSION,
        "rows": len(locations),
        "municipalities": len(municipalities),
        "localities": len(localities),
        "postal_code_relations": len(postal_codes),
        "semantic_changes_from_milestone1": diff_report["record_changes"],
        "outputs": {
            name: str(path.relative_to(path.parents[1]))
            for name, path in GENERATED_PATHS.items()
            if path.exists()
        },
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
