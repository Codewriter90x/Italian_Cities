#!/usr/bin/env python3
"""Build all tabular datasets from declared source snapshots."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from dataset_common import (
    GENERATED_PATHS,
    ITALIAN_LOCATION_FIELDS,
    LOCALITY_FIELDS,
    MUNICIPALITY_FIELDS,
    POSTAL_CODE_FIELDS,
    REPORTS_DIR,
    ROOT,
    SOURCE_MANIFEST,
    V1_ITALIAN_LOCATION_FIELDS,
    canonical_row_sort_key,
    normalize_name,
    read_csv_rows,
    sha256_file,
    write_csv_rows,
    write_json,
)
from project_metadata import (
    BUILD_DATE,
    DATASET_VERSION,
    PREVIOUS_RELEASE,
    SCHEMA_VERSION,
)
from normalize_legacy import (
    DEFAULT_ISTAT,
    DEFAULT_LEGACY,
    canonicalize,
    load_istat_municipalities,
    load_legacy_rows,
)


DEFAULT_DIFF_REPORT = REPORTS_DIR / "release-diff.json"
DEFAULT_PREVIOUS_RELEASE = ROOT / PREVIOUS_RELEASE["canonical_path"]
GENERIC_MULTICAP_POSTAL_CODES = {
    ("bari", "BA", "70100"),
    ("bologna", "BO", "40100"),
    ("firenze", "FI", "50100"),
    ("genova", "GE", "16100"),
    ("milano", "MI", "20100"),
    ("napoli", "NA", "80100"),
    ("roma", "RM", "00100"),
    ("torino", "TO", "10100"),
    ("venezia", "VE", "30100"),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--legacy", type=Path, default=DEFAULT_LEGACY)
    parser.add_argument("--istat", type=Path, default=DEFAULT_ISTAT)
    parser.add_argument(
        "--previous-release",
        type=Path,
        default=DEFAULT_PREVIOUS_RELEASE,
    )
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
) -> dict[str, object]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    declared = {source["id"]: source for source in manifest["sources"]}
    actual_paths = {
        "legacy_csv": legacy_path,
        "istat_municipalities": istat_path,
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


def validate_previous_release(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"previous release baseline is missing: {path}")
    actual_sha256 = sha256_file(path)
    expected_sha256 = PREVIOUS_RELEASE["canonical_sha256"]
    if actual_sha256 != expected_sha256:
        raise ValueError(
            "previous release baseline checksum mismatch: "
            f"{actual_sha256} != {expected_sha256}"
        )


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
    official_province_names: dict[str, str],
) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    for row in milestone1_rows:
        province_code = row["province_code"]
        official_province_name = official_province_names[province_code]
        postal_key = (
            normalize_name(row["name"]),
            province_code,
            row["postal_code"],
        )
        postal_code_status = (
            "generic_multicap"
            if postal_key in GENERIC_MULTICAP_POSTAL_CODES
            else "legacy_unverified"
        )
        coordinate_verification = {
            "available": "legacy_unverified",
            "corrected": "corrected_legacy_unverified",
            "missing": "missing",
        }[row["coordinate_status"]]
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
                "postal_code_status": postal_code_status,
                "province_code": province_code,
                "province_name": official_province_name,
                "legacy_province_name": row["province_name"],
                "region_name": row["region_name"],
                "country_code": row["country_code"],
                "country_name": row["country_name"],
                "latitude": row["latitude"],
                "longitude": row["longitude"],
                "coordinate_status": row["coordinate_status"],
                "coordinate_verification": coordinate_verification,
                "source_snapshot": row["source_snapshot"],
                "source_ids": "legacy_csv;istat_municipalities",
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
            "postal_code_status": row["postal_code_status"],
            "province_code": row["province_code"],
            "province_name": row["province_name"],
            "legacy_province_name": row["legacy_province_name"],
            "region_name": row["region_name"],
            "country_code": row["country_code"],
            "country_name": row["country_name"],
            "latitude": row["latitude"],
            "longitude": row["longitude"],
            "coordinate_status": row["coordinate_status"],
            "coordinate_verification": row["coordinate_verification"],
            "source_snapshot": row["source_snapshot"],
            "source_ids": row["source_ids"],
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
                    "postal_code_status": row["postal_code_status"],
                    "province_code": row["province_code"],
                    "province_name": row["province_name"],
                    "legacy_province_name": row["legacy_province_name"],
                    "region_name": row["region_name"],
                    "country_code": row["country_code"],
                    "country_name": row["country_name"],
                    "latitude": row["latitude"],
                    "longitude": row["longitude"],
                    "coordinate_status": row["coordinate_status"],
                    "coordinate_verification": row["coordinate_verification"],
                    "source_snapshot": row["source_snapshot"],
                    "source_ids": row["source_ids"],
                }
            )

        postal_codes.append(
            {
                "location_id": row["location_id"],
                "location_kind": row["location_kind"],
                "postal_code": row["postal_code"],
                "postal_code_status": row["postal_code_status"],
                "province_code": row["province_code"],
                "is_primary": "true",
                "source_snapshot": row["source_snapshot"],
                "source_ids": row["source_ids"],
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
        before = baseline_by_uuid[legacy_uuid]
        after = current_by_uuid[legacy_uuid]
        changed_fields = [
            field
            for field in V1_ITALIAN_LOCATION_FIELDS
            if before[field] != after[field]
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
    coordinate_verification = Counter(
        row["coordinate_verification"] for row in current_rows
    )
    postal_code_status = Counter(row["postal_code_status"] for row in current_rows)
    return {
        "comparison": {
            "from": PREVIOUS_RELEASE["version"],
            "to": DATASET_VERSION,
        },
        "schema_version": SCHEMA_VERSION,
        "build_date": BUILD_DATE,
        "baseline": {
            "path": str(baseline_path.relative_to(ROOT)),
            "sha256": sha256_file(baseline_path),
            "rows": len(baseline_rows),
            "fields": list(V1_ITALIAN_LOCATION_FIELDS),
        },
        "current": {
            "path": "data/italian_locations.csv",
            "sha256": sha256_file(GENERATED_PATHS["italian_locations"]),
            "rows": len(current_rows),
            "fields": list(ITALIAN_LOCATION_FIELDS),
        },
        "schema_changes": {
            "added_fields": [
                field
                for field in ITALIAN_LOCATION_FIELDS
                if field not in V1_ITALIAN_LOCATION_FIELDS
            ],
            "renamed_fields": {},
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
        "coordinate_verification_counts": dict(
            sorted(coordinate_verification.items())
        ),
        "postal_code_status_counts": dict(sorted(postal_code_status.items())),
    }


def main() -> None:
    args = parse_args()
    manifest = validate_declared_sources(
        args.manifest,
        legacy_path=args.legacy,
        istat_path=args.istat,
    )
    validate_previous_release(args.previous_release)
    current_milestone1 = load_current_milestone1_rows(args.legacy, args.istat)
    baseline_rows = read_csv_rows(
        args.previous_release,
        V1_ITALIAN_LOCATION_FIELDS,
    )
    official_records = load_istat_municipalities(args.istat)
    official_province_names = {
        record["province_code"]: record["province_name"]
        for record in official_records.values()
    }

    locations = build_italian_locations(
        current_milestone1,
        official_province_names,
    )
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
        args.previous_release,
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
        "changes_from_previous_release": diff_report["record_changes"],
        "outputs": {
            name: str(path.relative_to(path.parents[1]))
            for name, path in GENERATED_PATHS.items()
            if path.exists()
        },
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
