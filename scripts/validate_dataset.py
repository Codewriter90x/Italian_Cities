#!/usr/bin/env python3
"""Validate clean-room structure, semantics, provenance and formats."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from check_determinism import DEFAULT_REPORT as DETERMINISM_REPORT
from dataset_common import (
    GENERATED_PATHS,
    ITALIAN_LOCATION_FIELDS,
    LOCALITY_FIELDS,
    MUNICIPALITY_FIELDS,
    POSTAL_CODE_FIELDS,
    REPORTS_DIR,
    ROOT,
    canonical_row_sort_key,
    normalize_name,
    read_csv_rows,
    write_json,
)
from project_metadata import (
    OPERATIONAL_DATA_READINESS,
    QUALITY_GATE_VERSION,
    SCHEMA_VERSION,
    STRUCTURAL_QUALITY,
)
from source_data import (
    load_geonames_records,
    load_istat_records,
    load_manifest,
)
from validators.common import (
    add_quality_error,
    completely_blank_record_lines,
)
from validators.coordinates import validate_coordinate_table
from validators.formats import validate_formats
from validators.provenance import validate_verification_and_provenance
from validators.schema import (
    validate_logical_key,
    validate_postal_code_table,
    validate_postal_semantics,
    validate_unique_key,
)
from validators.territory import (
    territorial_names_compatible,
    validate_territories,
)

DEFAULT_REPORT = REPORTS_DIR / "quality-validation.json"
QUALITY_CHECK_NAMES = (
    "schema_columns",
    "unique_identifiers",
    "postal_code_format",
    "postal_code_semantics",
    "istat_code_validity",
    "territorial_coherence",
    "numeric_coordinates",
    "coordinate_bounds",
    "coordinate_verification",
    "provenance_completeness",
    "no_empty_rows",
    "no_logical_duplicates",
    "cross_table_integrity",
    "clean_room_isolation",
    "cross_format_equivalence",
    "deterministic_build",
    "operational_readiness",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def _new_checks() -> dict[str, dict[str, object]]:
    return {
        name: {"status": "passed", "violations": 0}
        for name in QUALITY_CHECK_NAMES
    }


def _validate_accuracy_preserved(
    postal_codes: list[dict[str, str]],
    errors: list[str],
    checks: dict[str, dict[str, object]],
) -> None:
    geonames = {
        row["source_record_id"]: row for row in load_geonames_records()
    }
    for line_number, relation in enumerate(postal_codes, start=2):
        if relation["source_id"] != "geonames_postal_codes":
            continue
        source_records = [
            geonames.get(source_id)
            for source_id in relation["source_record_ids"].split(";")
        ]
        if any(record is None for record in source_records):
            add_quality_error(
                errors,
                checks,
                "provenance_completeness",
                f"data/postal_codes.csv:{line_number}: unknown GeoNames "
                "source_record_id",
            )
            continue
        expected = max(
            (record["accuracy"] for record in source_records if record),
            key=lambda value: int(value or "0"),
        )
        if relation["accuracy"] != expected:
            add_quality_error(
                errors,
                checks,
                "provenance_completeness",
                f"data/postal_codes.csv:{line_number}: accuracy differs "
                "from GeoNames",
            )


def validate() -> dict[str, object]:
    errors: list[str] = []
    warnings = [
        "GeoNames is not Poste Italiane.",
        "CAP and coordinates are experimental, non-official and without warranty.",
        "GeoNames coordinates may be algorithmically estimated.",
    ]
    checks = _new_checks()
    municipalities = read_csv_rows(
        GENERATED_PATHS["municipalities"], MUNICIPALITY_FIELDS
    )
    localities = read_csv_rows(
        GENERATED_PATHS["localities"], LOCALITY_FIELDS
    )
    postal_codes = read_csv_rows(
        GENERATED_PATHS["postal_codes"], POSTAL_CODE_FIELDS
    )
    locations = read_csv_rows(
        GENERATED_PATHS["italian_locations"], ITALIAN_LOCATION_FIELDS
    )
    tables = {
        "data/municipalities.csv": municipalities,
        "data/localities.csv": localities,
        "data/postal_codes.csv": postal_codes,
        "data/italian_locations.csv": locations,
    }
    for dataset, rows in tables.items():
        for line_number in completely_blank_record_lines(ROOT / dataset):
            add_quality_error(
                errors,
                checks,
                "no_empty_rows",
                f"{dataset}:{line_number}: completely empty row",
            )
        for line_number, row in enumerate(rows, start=2):
            if all(not value.strip() for value in row.values()):
                add_quality_error(
                    errors,
                    checks,
                    "no_empty_rows",
                    f"{dataset}:{line_number}: completely empty record",
                )

    for rows, dataset, unique_fields in (
        (
            municipalities,
            "data/municipalities.csv",
            ("municipality_id",),
        ),
        (municipalities, "data/municipalities.csv", ("istat_code",)),
        (localities, "data/localities.csv", ("locality_id",)),
        (
            postal_codes,
            "data/postal_codes.csv",
            ("postal_code_relation_id",),
        ),
        (
            locations,
            "data/italian_locations.csv",
            ("location_postal_id",),
        ),
    ):
        validate_unique_key(
            rows=rows,
            fields=unique_fields,
            dataset=dataset,
            errors=errors,
            checks=checks,
        )
    for rows, dataset, logical_fields in (
        (
            postal_codes,
            "data/postal_codes.csv",
            ("location_id", "postal_code"),
        ),
        (
            locations,
            "data/italian_locations.csv",
            ("location_id", "postal_code"),
        ),
        (
            localities,
            "data/localities.csv",
            (
                "normalized_name",
                "province_code",
                "latitude",
                "longitude",
                "reconciliation_outcome",
            ),
        ),
    ):
        validate_logical_key(
            rows=rows,
            fields=logical_fields,
            dataset=dataset,
            errors=errors,
            checks=checks,
        )

    for rows, dataset in (
        (postal_codes, "data/postal_codes.csv"),
        (locations, "data/italian_locations.csv"),
    ):
        validate_postal_code_table(
            rows=rows,
            dataset=dataset,
            errors=errors,
            checks=checks,
        )
        validate_postal_semantics(
            rows=rows,
            dataset=dataset,
            errors=errors,
            checks=checks,
        )
    for rows, dataset in (
        (municipalities, "data/municipalities.csv"),
        (localities, "data/localities.csv"),
        (locations, "data/italian_locations.csv"),
    ):
        validate_coordinate_table(
            rows=rows,
            dataset=dataset,
            errors=errors,
            checks=checks,
        )
        validate_verification_and_provenance(
            rows=rows,
            dataset=dataset,
            errors=errors,
            checks=checks,
        )
    validate_verification_and_provenance(
        rows=postal_codes,
        dataset="data/postal_codes.csv",
        errors=errors,
        checks=checks,
    )

    official = load_istat_records()
    validate_territories(
        municipalities=municipalities,
        localities=localities,
        official_records=official,
        errors=errors,
        checks=checks,
    )
    _validate_accuracy_preserved(postal_codes, errors, checks)

    municipality_ids = {row["municipality_id"] for row in municipalities}
    locality_ids = {row["locality_id"] for row in localities}
    all_location_ids = municipality_ids | locality_ids
    relation_ids = {
        row["postal_code_relation_id"] for row in postal_codes
    }
    if {row["location_id"] for row in postal_codes} != all_location_ids:
        add_quality_error(
            errors,
            checks,
            "cross_table_integrity",
            "postal relations do not cover every municipality and locality",
        )
    if any(
        row["location_id"] not in all_location_ids for row in locations
    ):
        add_quality_error(
            errors,
            checks,
            "cross_table_integrity",
            "canonical locations contain an orphan location_id",
        )
    if {row["location_postal_id"] for row in locations} != relation_ids:
        add_quality_error(
            errors,
            checks,
            "cross_table_integrity",
            "canonical rows and postal relation ids differ",
        )
    if locations != sorted(locations, key=canonical_row_sort_key):
        add_quality_error(
            errors,
            checks,
            "cross_table_integrity",
            "italian_locations.csv is not deterministically sorted",
        )
    for row in (*municipalities, *localities, *locations):
        if row["normalized_name"] != normalize_name(row["name"]):
            add_quality_error(
                errors,
                checks,
                "schema_columns",
                f"{row.get('location_id', row.get('municipality_id', 'row'))}: "
                "normalized_name is not reproducible",
            )

    manifest = load_manifest()
    if set(manifest["canonical_source_ids"]) != {
        "istat_municipalities",
        "geonames_postal_codes",
    }:
        add_quality_error(
            errors,
            checks,
            "clean_room_isolation",
            "canonical source manifest contains unexpected sources",
        )
    if any(
        "legacy_csv" in row["source_ids"] for row in locations
    ):
        add_quality_error(
            errors,
            checks,
            "clean_room_isolation",
            "legacy contributes to canonical rows",
        )
    if STRUCTURAL_QUALITY != "passed":
        add_quality_error(
            errors,
            checks,
            "operational_readiness",
            "structural_quality metadata must be passed",
        )
    if OPERATIONAL_DATA_READINESS != "experimental_non_official":
        add_quality_error(
            errors,
            checks,
            "operational_readiness",
            "operational readiness must remain experimental_non_official",
        )

    equivalence = validate_formats(
        locations=locations,
        determinism_report_path=DETERMINISM_REPORT,
        errors=errors,
        checks=checks,
    )
    for check in checks.values():
        check["status"] = (
            "passed" if check["violations"] == 0 else "failed"
        )
    coordinate_counts = Counter(
        row["coordinate_verification"] for row in locations
    )
    accuracy_counts = Counter(
        row["coordinate_accuracy"] or "missing" for row in locations
    )
    return {
        "structural_quality": "passed" if not errors else "failed",
        "operational_data_readiness": OPERATIONAL_DATA_READINESS,
        "schema_version": SCHEMA_VERSION,
        "quality_gate_version": QUALITY_GATE_VERSION,
        "errors": errors,
        "warnings": warnings,
        "quality_checks": checks,
        "counts": {
            "municipalities": len(municipalities),
            "localities": len(localities),
            "postal_code_relations": len(postal_codes),
            "canonical_rows": len(locations),
            "municipalities_without_postal_code": sum(
                row["postal_code_status"] == "missing"
                for row in postal_codes
            ),
        },
        "coordinate_verification_counts": dict(
            sorted(coordinate_counts.items())
        ),
        "coordinate_accuracy_counts": dict(sorted(accuracy_counts.items())),
        "cross_format_equivalence": equivalence,
    }


def main() -> None:
    args = parse_args()
    try:
        report = validate()
    except (
        FileNotFoundError,
        KeyError,
        ValueError,
        json.JSONDecodeError,
    ) as error:
        report = {
            "structural_quality": "failed",
            "operational_data_readiness": OPERATIONAL_DATA_READINESS,
            "errors": [str(error)],
        }
    write_json(args.report, report)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    if report["structural_quality"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()


__all__ = [
    "QUALITY_CHECK_NAMES",
    "completely_blank_record_lines",
    "territorial_names_compatible",
    "validate_coordinate_table",
    "validate_logical_key",
    "validate_postal_code_table",
    "validate_postal_semantics",
    "validate_unique_key",
    "validate_verification_and_provenance",
]
