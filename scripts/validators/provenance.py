"""Clean-room source provenance and reconciliation validators."""

from __future__ import annotations

from validators.common import QualityChecks, add_quality_error

CANONICAL_SOURCES = {
    "istat_municipalities",
    "geonames_postal_codes",
}


def validate_verification_and_provenance(
    *,
    rows: list[dict[str, str]],
    dataset: str,
    errors: list[str],
    checks: QualityChecks,
) -> None:
    for line_number, row in enumerate(rows, start=2):
        label = f"{dataset}:{line_number}"
        source_ids = set(
            filter(None, row.get("source_ids", "").split(";"))
        )
        if not source_ids:
            source_id = row.get("source_id", "")
            source_ids = {source_id} if source_id else set()
        if not source_ids or not source_ids.issubset(CANONICAL_SOURCES):
            add_quality_error(
                errors,
                checks,
                "provenance_completeness",
                f"{label}: source ids must reference only clean-room sources",
            )
        if "legacy_csv" in source_ids:
            add_quality_error(
                errors,
                checks,
                "clean_room_isolation",
                f"{label}: legacy source is forbidden in canonical data",
            )
        source_records = row.get(
            "source_record_ids",
            row.get(
                "source_record_id",
                row.get("administrative_source_record_id", ""),
            ),
        )
        if not source_records:
            add_quality_error(
                errors,
                checks,
                "provenance_completeness",
                f"{label}: source record identity is missing",
            )
        if row.get("reconciliation_outcome") == "multiple_candidates":
            if row.get("parent_municipality_id"):
                add_quality_error(
                    errors,
                    checks,
                    "clean_room_isolation",
                    f"{label}: ambiguous match was promoted automatically",
                )
            if not row.get("candidate_municipality_ids"):
                add_quality_error(
                    errors,
                    checks,
                    "provenance_completeness",
                    f"{label}: ambiguous match lacks candidate ids",
                )
        if (
            row.get("reconciliation_outcome") == "unmatched_no_parent"
            and row.get("parent_municipality_id")
        ):
            add_quality_error(
                errors,
                checks,
                "clean_room_isolation",
                f"{label}: unmatched locality has a parent municipality",
            )
