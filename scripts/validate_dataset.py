#!/usr/bin/env python3
"""Validate schema, integrity and cross-format equivalence."""

from __future__ import annotations

import argparse
import json
import math
import re
import uuid
import zipfile
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
    canonical_row_sort_key,
    normalize_name,
    read_csv_rows,
    record_digest,
    sha256_file,
    write_json,
)
from check_determinism import (
    DEFAULT_REPORT as DETERMINISM_REPORT,
)
from normalize_legacy import DEFAULT_ISTAT, load_istat_municipalities
from project_metadata import QUALITY_GATE_VERSION, SCHEMA_VERSION
from validators.common import (
    add_error,
    add_quality_error,
    completely_blank_record_lines,
)
from validators.coordinates import ITALY_BOUNDS, validate_coordinate_table
from validators.formats import validate_formats
from validators.provenance import validate_verification_and_provenance
from validators.schema import (
    expected_locality,
    expected_municipality,
    expected_postal_code,
    validate_logical_key,
    validate_postal_code_table,
    validate_postal_semantics,
    validate_unique_key,
)
from validators.territory import (
    territorial_names_compatible as territorial_names_compatible,
)
from validators.territory import validate_territories


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
    "deterministic_build",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def validate() -> dict[str, object]:
    errors: list[str] = []
    warnings: list[str] = []
    quality_checks: dict[str, dict[str, object]] = {
        name: {"status": "passed", "violations": 0}
        for name in QUALITY_CHECK_NAMES
    }
    locations = read_csv_rows(
        GENERATED_PATHS["italian_locations"],
        ITALIAN_LOCATION_FIELDS,
    )
    municipalities = read_csv_rows(
        GENERATED_PATHS["municipalities"],
        MUNICIPALITY_FIELDS,
    )
    localities = read_csv_rows(GENERATED_PATHS["localities"], LOCALITY_FIELDS)
    postal_codes = read_csv_rows(
        GENERATED_PATHS["postal_codes"],
        POSTAL_CODE_FIELDS,
    )

    table_rows = {
        "data/municipalities.csv": municipalities,
        "data/localities.csv": localities,
        "data/postal_codes.csv": postal_codes,
        "data/italian_locations.csv": locations,
    }
    for dataset, rows in table_rows.items():
        path = ROOT / dataset
        for line_number in completely_blank_record_lines(path):
            add_quality_error(
                errors,
                quality_checks,
                "no_empty_rows",
                f"{dataset}:{line_number}: completely empty row",
            )
        for line_number, row in enumerate(rows, start=2):
            if all(not (value or "").strip() for value in row.values()):
                add_quality_error(
                    errors,
                    quality_checks,
                    "no_empty_rows",
                    f"{dataset}:{line_number}: completely empty record",
                )
        validate_postal_code_table(
            rows=rows,
            dataset=dataset,
            errors=errors,
            checks=quality_checks,
        )
        validate_postal_semantics(
            rows=rows,
            dataset=dataset,
            errors=errors,
            checks=quality_checks,
        )

    unique_contracts: tuple[
        tuple[
            list[dict[str, str]],
            str,
            tuple[tuple[str, ...], ...],
        ],
        ...,
    ] = (
        (
            municipalities,
            "data/municipalities.csv",
            (("municipality_id",), ("istat_code",), ("legacy_uuid",)),
        ),
        (
            localities,
            "data/localities.csv",
            (("locality_id",), ("legacy_uuid",)),
        ),
        (
            postal_codes,
            "data/postal_codes.csv",
            (("location_id", "postal_code"),),
        ),
        (
            locations,
            "data/italian_locations.csv",
            (("location_id",), ("legacy_uuid",)),
        ),
    )
    for rows, dataset, keys in unique_contracts:
        for fields in keys:
            validate_unique_key(
                rows=rows,
                fields=fields,
                dataset=dataset,
                errors=errors,
                checks=quality_checks,
            )

    logical_contracts = (
        (
            municipalities,
            "data/municipalities.csv",
            ("normalized_name", "postal_code", "province_code"),
        ),
        (
            localities,
            "data/localities.csv",
            ("normalized_name", "postal_code", "province_code"),
        ),
        (
            postal_codes,
            "data/postal_codes.csv",
            ("location_id", "postal_code", "province_code"),
        ),
        (
            locations,
            "data/italian_locations.csv",
            ("normalized_name", "postal_code", "province_code"),
        ),
    )
    for rows, dataset, fields in logical_contracts:
        validate_logical_key(
            rows=rows,
            fields=fields,
            dataset=dataset,
            errors=errors,
            checks=quality_checks,
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
            checks=quality_checks,
        )
        validate_verification_and_provenance(
            rows=rows,
            dataset=dataset,
            errors=errors,
            checks=quality_checks,
        )

    official_records = load_istat_municipalities(DEFAULT_ISTAT)
    official_by_istat = validate_territories(
        municipalities=municipalities,
        localities=localities,
        locations=locations,
        official_records=official_records,
        errors=errors,
        checks=quality_checks,
    )

    if not locations:
        add_error(errors, "canonical dataset is empty")
    if locations != sorted(locations, key=canonical_row_sort_key):
        add_error(errors, "italian_locations.csv is not deterministically sorted")

    location_ids: set[str] = set()
    legacy_uuids: set[str] = set()
    logical_keys: set[tuple[str, str, str]] = set()
    kind_counts: Counter[str] = Counter()
    coordinate_counts: Counter[str] = Counter()
    coordinate_verification_counts: Counter[str] = Counter()
    postal_code_status_counts: Counter[str] = Counter()

    for line_number, row in enumerate(locations, start=2):
        label = f"data/italian_locations.csv:{line_number}"
        if row["location_id"] in location_ids:
            add_error(errors, f"{label}: duplicate location_id")
        location_ids.add(row["location_id"])
        if row["legacy_uuid"] in legacy_uuids:
            add_error(errors, f"{label}: duplicate legacy_uuid")
        legacy_uuids.add(row["legacy_uuid"])
        try:
            uuid.UUID(row["legacy_uuid"])
        except ValueError:
            add_error(errors, f"{label}: invalid legacy UUID")

        if row["normalized_name"] != normalize_name(row["name"]):
            add_error(errors, f"{label}: normalized_name is not reproducible")
        if not re.fullmatch(r"\d{5}", row["postal_code"]):
            add_error(errors, f"{label}: CAP is not a five-character string")
        if not re.fullmatch(r"[A-Z]{2}", row["province_code"]):
            add_error(errors, f"{label}: invalid province code")
        if row["country_code"] != "IT":
            add_error(errors, f"{label}: country_code must be IT")
        if row["parent_municipality_id"]:
            add_error(
                errors,
                f"{label}: parent municipality must remain empty until sourced",
            )
        if any(value.strip().casefold() == "null" for value in row.values()):
            add_error(errors, f"{label}: literal NULL is forbidden")

        logical_key = (
            row["normalized_name"],
            row["postal_code"],
            row["province_code"],
        )
        if logical_key in logical_keys:
            add_error(errors, f"{label}: duplicate normalized logical key")
        logical_keys.add(logical_key)

        if row["location_kind"] == "municipality":
            if not re.fullmatch(r"\d{6}", row["municipality_istat_code"]):
                add_error(errors, f"{label}: municipality lacks a six-digit ISTAT code")
            if row["location_id"] != f"IT-COM-{row['municipality_istat_code']}":
                add_error(errors, f"{label}: municipality ID and ISTAT code disagree")
        elif row["location_kind"] == "postal_locality_unclassified":
            if row["municipality_istat_code"]:
                add_error(errors, f"{label}: unclassified locality has an ISTAT code")
            if not re.fullmatch(
                r"IT-LOC-[0-9a-f]{8}-[0-9a-f]{4}-5[0-9a-f]{3}-"
                r"[89ab][0-9a-f]{3}-[0-9a-f]{12}",
                row["location_id"],
            ):
                add_error(errors, f"{label}: locality ID is not UUIDv5-based")
        else:
            add_error(errors, f"{label}: unsupported location_kind")

        latitude = row["latitude"]
        longitude = row["longitude"]
        if bool(latitude) != bool(longitude):
            add_error(errors, f"{label}: partial coordinate pair")
        if latitude:
            try:
                lat = float(latitude)
                lon = float(longitude)
            except ValueError:
                add_error(errors, f"{label}: non-numeric coordinates")
            else:
                if not (math.isfinite(lat) and math.isfinite(lon)):
                    add_error(errors, f"{label}: non-finite coordinates")
                if not (35 <= lat <= 48 and 6 <= lon <= 19):
                    add_error(errors, f"{label}: coordinates outside broad Italy bounds")
            if row["coordinate_status"] not in {"available", "corrected"}:
                add_error(errors, f"{label}: populated coordinates have wrong status")
        elif row["coordinate_status"] != "missing":
            add_error(errors, f"{label}: missing coordinates have wrong status")

        kind_counts[row["location_kind"]] += 1
        coordinate_counts[row["coordinate_status"]] += 1
        coordinate_verification_counts[row["coordinate_verification"]] += 1
        postal_code_status_counts[row["postal_code_status"]] += 1

    expected_municipalities = [
        expected_municipality(row)
        for row in locations
        if row["location_kind"] == "municipality"
    ]
    expected_localities = [
        expected_locality(row)
        for row in locations
        if row["location_kind"] == "postal_locality_unclassified"
    ]
    expected_postal_codes = sorted(
        [expected_postal_code(row) for row in locations],
        key=lambda row: (
            row["postal_code"],
            row["location_kind"],
            row["location_id"],
        ),
    )
    if municipalities != expected_municipalities:
        add_quality_error(
            errors,
            quality_checks,
            "cross_table_integrity",
            "municipalities.csv diverges from the canonical partition",
        )
    if localities != expected_localities:
        add_quality_error(
            errors,
            quality_checks,
            "cross_table_integrity",
            "localities.csv diverges from the canonical partition",
        )
    if postal_codes != expected_postal_codes:
        add_quality_error(
            errors,
            quality_checks,
            "cross_table_integrity",
            "postal_codes.csv diverges from canonical relations",
        )

    json_payload, sqlite_rows = validate_formats(
        locations=locations,
        determinism_report_path=DETERMINISM_REPORT,
        errors=errors,
        checks=quality_checks,
    )

    if coordinate_counts["missing"]:
        warnings.append(
            f"{coordinate_counts['missing']} records still lack coordinates"
        )
    if kind_counts["postal_locality_unclassified"]:
        warnings.append(
            f"{kind_counts['postal_locality_unclassified']} localities remain unclassified"
        )
    warnings.append(
        "Legacy upstream rights remain unresolved; release status must stay prerelease"
    )

    output_hashes = {
        name: sha256_file(path)
        for name, path in GENERATED_PATHS.items()
        if path.exists() and name != "sqlite"
    }
    for check in quality_checks.values():
        if check["violations"]:
            check["status"] = "failed"
    return {
        "status": "passed" if not errors else "failed",
        "schema_version": SCHEMA_VERSION,
        "quality_gate_version": QUALITY_GATE_VERSION,
        "canonical_rows": len(locations),
        "record_digest": record_digest(locations),
        "record_type_counts": dict(sorted(kind_counts.items())),
        "coordinate_status_counts": dict(sorted(coordinate_counts.items())),
        "coordinate_verification_counts": dict(
            sorted(coordinate_verification_counts.items())
        ),
        "postal_code_status_counts": dict(sorted(postal_code_status_counts.items())),
        "table_rows": {
            "municipalities": len(municipalities),
            "localities": len(localities),
            "postal_codes": len(postal_codes),
        },
        "cross_format_equivalence": {
            "csv": True,
            "json": json_payload.get("rows") == locations,
            "xlsx": not any(error.startswith("XLSX") for error in errors),
            "sqlite": sqlite_rows == locations,
        },
        "output_sha256": output_hashes,
        "output_semantic_sha256": {
            "sqlite": record_digest(sqlite_rows),
        },
        "quality_checks": quality_checks,
        "coordinate_bounds": ITALY_BOUNDS,
        "territorial_reference": {
            "source": str(DEFAULT_ISTAT.relative_to(ROOT)),
            "municipalities": len(official_by_istat),
        },
        "errors": errors,
        "warnings": warnings,
    }


def main() -> None:
    args = parse_args()
    try:
        report = validate()
    except (FileNotFoundError, ValueError, KeyError, zipfile.BadZipFile) as error:
        report = {
            "status": "failed",
            "errors": [str(error)],
            "warnings": [],
        }
    write_json(args.report, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
