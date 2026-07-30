"""Schema, identifier, logical-key and postal-code validators."""

from __future__ import annotations

import re

from validators.common import QualityChecks, add_quality_error


POSTAL_CODE_STATUSES = {
    "geonames_matched",
    "geonames_ambiguous",
    "official_verified",
    "obsolete",
    "missing",
}


def validate_unique_key(
    *,
    rows: list[dict[str, str]],
    fields: tuple[str, ...],
    dataset: str,
    errors: list[str],
    checks: QualityChecks,
) -> None:
    seen: set[tuple[str, ...]] = set()
    for line_number, row in enumerate(rows, start=2):
        key = tuple(row[field] for field in fields)
        if any(not value for value in key):
            add_quality_error(
                errors,
                checks,
                "unique_identifiers",
                f"{dataset}:{line_number}: empty identifier in {fields}",
            )
        elif key in seen:
            add_quality_error(
                errors,
                checks,
                "unique_identifiers",
                f"{dataset}:{line_number}: duplicate identifier "
                f"{fields}={key}",
            )
        seen.add(key)


def validate_logical_key(
    *,
    rows: list[dict[str, str]],
    fields: tuple[str, ...],
    dataset: str,
    errors: list[str],
    checks: QualityChecks,
) -> None:
    seen: set[tuple[str, ...]] = set()
    for line_number, row in enumerate(rows, start=2):
        key = tuple(row[field] for field in fields)
        if key in seen:
            add_quality_error(
                errors,
                checks,
                "no_logical_duplicates",
                f"{dataset}:{line_number}: duplicate logical key "
                f"{fields}={key}",
            )
        seen.add(key)


def validate_postal_code_table(
    *,
    rows: list[dict[str, str]],
    dataset: str,
    errors: list[str],
    checks: QualityChecks,
) -> None:
    for line_number, row in enumerate(rows, start=2):
        postal_code = row["postal_code"]
        status = row["postal_code_status"]
        if status == "missing":
            if postal_code:
                add_quality_error(
                    errors,
                    checks,
                    "postal_code_semantics",
                    f"{dataset}:{line_number}: missing status requires "
                    "an empty CAP",
                )
        elif not re.fullmatch(r"\d{5}", postal_code):
            add_quality_error(
                errors,
                checks,
                "postal_code_format",
                f"{dataset}:{line_number}: CAP must contain exactly five digits",
            )


def validate_postal_semantics(
    *,
    rows: list[dict[str, str]],
    dataset: str,
    errors: list[str],
    checks: QualityChecks,
) -> None:
    for line_number, row in enumerate(rows, start=2):
        status = row["postal_code_status"]
        if status not in POSTAL_CODE_STATUSES:
            add_quality_error(
                errors,
                checks,
                "postal_code_semantics",
                f"{dataset}:{line_number}: unsupported postal_code_status "
                f"{status!r}",
            )
        if status in {"official_verified", "obsolete"}:
            add_quality_error(
                errors,
                checks,
                "postal_code_semantics",
                f"{dataset}:{line_number}: {status} is reserved until an "
                "authoritative compatible source is declared",
            )
