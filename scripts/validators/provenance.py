"""Coordinate verification and source-provenance validators."""

from __future__ import annotations

from validators.common import QualityChecks, add_quality_error


def validate_verification_and_provenance(
    *,
    rows: list[dict[str, str]],
    dataset: str,
    errors: list[str],
    checks: QualityChecks,
) -> None:
    verification_by_status = {
        "available": {"legacy_unverified", "verified"},
        "corrected": {"corrected_legacy_unverified", "verified"},
        "missing": {"missing"},
    }
    for line_number, row in enumerate(rows, start=2):
        label = f"{dataset}:{line_number}"
        expected_verification = verification_by_status.get(row["coordinate_status"])
        if expected_verification is None:
            add_quality_error(
                errors,
                checks,
                "coordinate_verification",
                f"{label}: unsupported coordinate_status",
            )
        elif row["coordinate_verification"] not in expected_verification:
            add_quality_error(
                errors,
                checks,
                "coordinate_verification",
                f"{label}: coordinate verification must be one of "
                f"{sorted(expected_verification)!r}",
            )

        source_ids = {
            source_id for source_id in row["source_ids"].split(";") if source_id
        }
        required_sources = {"legacy_csv", "istat_municipalities"}
        if not required_sources.issubset(source_ids):
            add_quality_error(
                errors,
                checks,
                "provenance_completeness",
                f"{label}: source_ids must identify legacy and ISTAT inputs",
            )
        has_authoritative_source = bool(source_ids - required_sources)
        if (
            row["coordinate_verification"] == "verified"
            or row.get("postal_code_status") in {"verified", "obsolete"}
        ) and not has_authoritative_source:
            add_quality_error(
                errors,
                checks,
                "provenance_completeness",
                f"{label}: verified or obsolete values require an additional source",
            )
