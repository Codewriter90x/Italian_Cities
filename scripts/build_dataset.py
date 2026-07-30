#!/usr/bin/env python3
"""Build the v2 clean-room dataset from ISTAT and GeoNames snapshots."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, cast

from dataset_common import (
    GENERATED_PATHS,
    ITALIAN_LOCATION_FIELDS,
    LOCALITY_FIELDS,
    MUNICIPALITY_FIELDS,
    POSTAL_CODE_FIELDS,
    REPORTS_DIR,
    ROOT,
    SOURCE_MANIFEST,
    read_csv_rows,
    sha256_file,
    write_csv_rows,
    write_json,
)
from legacy_comparison import build_legacy_comparison
from project_metadata import (
    BUILD_DATE,
    DATASET_VERSION,
    GEONAMES_REFERENCE_DATE,
    ISTAT_REFERENCE_DATE,
    OPERATIONAL_DATA_READINESS,
    PREVIOUS_RELEASE,
    SCHEMA_VERSION,
    STRUCTURAL_QUALITY,
)
from reconcile_sources import reconcile
from reconciliation_backlog import build_backlog
from source_data import (
    DEFAULT_GEONAMES,
    DEFAULT_ISTAT,
    DEFAULT_LEGACY,
    load_geonames_records,
    load_istat_records,
    validate_declared_sources,
)

DEFAULT_PREVIOUS_RELEASE = ROOT / PREVIOUS_RELEASE["canonical_path"]
DEFAULT_DIFF_REPORT = REPORTS_DIR / "release-diff.json"
DEFAULT_LEGACY_REPORT = REPORTS_DIR / "legacy-comparison.json"
DEFAULT_BUILD_REPORT = REPORTS_DIR / "build-metadata.json"
DEFAULT_RECONCILIATION_REPORT = REPORTS_DIR / "reconciliation-backlog.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--istat", type=Path, default=DEFAULT_ISTAT)
    parser.add_argument("--geonames", type=Path, default=DEFAULT_GEONAMES)
    parser.add_argument("--legacy", type=Path, default=DEFAULT_LEGACY)
    parser.add_argument("--manifest", type=Path, default=SOURCE_MANIFEST)
    parser.add_argument(
        "--previous-release",
        type=Path,
        default=DEFAULT_PREVIOUS_RELEASE,
    )
    parser.add_argument("--diff-report", type=Path, default=DEFAULT_DIFF_REPORT)
    parser.add_argument(
        "--legacy-report", type=Path, default=DEFAULT_LEGACY_REPORT
    )
    parser.add_argument(
        "--build-report", type=Path, default=DEFAULT_BUILD_REPORT
    )
    parser.add_argument(
        "--reconciliation-report",
        type=Path,
        default=DEFAULT_RECONCILIATION_REPORT,
    )
    parser.add_argument(
        "--no-exports",
        action="store_true",
        help="Build CSV tables and reports without JSON/XLSX/SQLite exports.",
    )
    return parser.parse_args()


def validate_previous_release(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"previous release baseline is missing: {path}")
    actual = sha256_file(path)
    if actual != PREVIOUS_RELEASE["canonical_sha256"]:
        raise ValueError(
            f"previous release baseline checksum mismatch: {actual} != "
            f"{PREVIOUS_RELEASE['canonical_sha256']}"
        )


def build_release_diff(
    baseline_path: Path,
    current_rows: list[dict[str, str]],
) -> dict[str, object]:
    baseline_rows = read_csv_rows(baseline_path)

    def logical_key(row: dict[str, str]) -> tuple[str, str, str]:
        return (
            row.get("normalized_name", ""),
            row.get("province_code", ""),
            row.get("postal_code", ""),
        )

    before = {logical_key(row) for row in baseline_rows}
    after = {logical_key(row) for row in current_rows}
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
            "fields": list(baseline_rows[0]) if baseline_rows else [],
        },
        "current": {
            "path": "data/italian_locations.csv",
            "sha256": sha256_file(GENERATED_PATHS["italian_locations"]),
            "rows": len(current_rows),
            "fields": list(ITALIAN_LOCATION_FIELDS),
        },
        "schema_changes": {
            "breaking": True,
            "schema_version": SCHEMA_VERSION,
            "added_fields": sorted(
                set(ITALIAN_LOCATION_FIELDS)
                - set(baseline_rows[0] if baseline_rows else {})
            ),
            "removed_fields": sorted(
                set(baseline_rows[0] if baseline_rows else {})
                - set(ITALIAN_LOCATION_FIELDS)
            ),
        },
        "logical_record_changes": {
            "added": len(after - before),
            "removed": len(before - after),
            "shared": len(before & after),
        },
        "interpretation": (
            "The v2 source and schema change makes row identity incomparable "
            "to v1; logical name/province/CAP keys are reported for context."
        ),
    }


def build_clean_room(
    *,
    istat_path: Path = DEFAULT_ISTAT,
    geonames_path: Path = DEFAULT_GEONAMES,
) -> dict[str, object]:
    return reconcile(
        load_istat_records(istat_path),
        load_geonames_records(geonames_path),
        istat_reference_date=ISTAT_REFERENCE_DATE,
        geonames_reference_date=GEONAMES_REFERENCE_DATE,
    )


def write_canonical_outputs(model: dict[str, object]) -> None:
    write_csv_rows(
        GENERATED_PATHS["municipalities"],
        MUNICIPALITY_FIELDS,
        model["municipalities"],  # type: ignore[arg-type]
    )
    write_csv_rows(
        GENERATED_PATHS["localities"],
        LOCALITY_FIELDS,
        model["localities"],  # type: ignore[arg-type]
    )
    write_csv_rows(
        GENERATED_PATHS["postal_codes"],
        POSTAL_CODE_FIELDS,
        model["postal_codes"],  # type: ignore[arg-type]
    )
    write_csv_rows(
        GENERATED_PATHS["italian_locations"],
        ITALIAN_LOCATION_FIELDS,
        model["italian_locations"],  # type: ignore[arg-type]
    )


def build_all(args: argparse.Namespace) -> dict[str, Any]:
    manifest = validate_declared_sources(
        args.manifest,
        istat_path=args.istat,
        geonames_path=args.geonames,
        legacy_path=args.legacy,
    )
    validate_previous_release(args.previous_release)
    model = build_clean_room(
        istat_path=args.istat,
        geonames_path=args.geonames,
    )
    write_canonical_outputs(model)
    current_rows = model["italian_locations"]
    assert isinstance(current_rows, list)

    release_diff = build_release_diff(args.previous_release, current_rows)
    write_json(args.diff_report, release_diff)
    write_json(
        args.legacy_report,
        build_legacy_comparison(args.legacy, current_rows),
    )

    coordinate_counts = Counter(
        row["coordinate_verification"] for row in current_rows
    )
    accuracy_counts = Counter(
        row["coordinate_accuracy"] or "missing" for row in current_rows
    )
    unique_location_rows = [
        *cast(list[dict[str, str]], model["municipalities"]),
        *cast(list[dict[str, str]], model["localities"]),
    ]
    unique_coordinate_counts = Counter(
        row["coordinate_verification"] for row in unique_location_rows
    )
    unique_accuracy_counts = Counter(
        row["coordinate_accuracy"] or "missing"
        for row in unique_location_rows
    )
    write_json(
        args.reconciliation_report,
        build_backlog(
            cast(list[dict[str, str]], model["municipalities"]),
            cast(list[dict[str, str]], model["localities"]),
        ),
    )
    build_report = {
        "dataset_version": DATASET_VERSION,
        "schema_version": SCHEMA_VERSION,
        "build_date": BUILD_DATE,
        "structural_quality": STRUCTURAL_QUALITY,
        "operational_data_readiness": OPERATIONAL_DATA_READINESS,
        "postal_use_warning": (
            "Experimental, non-official data. GeoNames is not Poste Italiane."
        ),
        "attribution": {
            "istat": "Istituto nazionale di statistica (ISTAT), CC BY 4.0",
            "geonames": (
                "GeoNames postal code dump, CC BY 4.0, "
                "https://www.geonames.org/"
            ),
        },
        "canonical_source_ids": manifest["canonical_source_ids"],
        "source_manifest_sha256": sha256_file(args.manifest),
        "canonical_source_digest": model["canonical_source_digest"],
        "statistics": model["statistics"],
        "coordinate_verification_counts": dict(
            sorted(coordinate_counts.items())
        ),
        "coordinate_accuracy_counts": dict(sorted(accuracy_counts.items())),
        "coordinate_count_grain": "canonical_location_postal_rows",
        "unique_location_coordinate_verification_counts": dict(
            sorted(unique_coordinate_counts.items())
        ),
        "unique_location_coordinate_accuracy_counts": dict(
            sorted(unique_accuracy_counts.items())
        ),
        "legacy_contributes_to_canonical": False,
    }
    write_json(args.build_report, build_report)

    if not args.no_exports:
        from export_formats import export_all

        export_all()
    return build_report


def main() -> None:
    report = build_all(parse_args())
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
