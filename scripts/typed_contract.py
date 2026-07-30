"""Typed next-major representation for consumer-facing exports."""

from __future__ import annotations

from typing import Any

from dataset_common import ITALIAN_LOCATION_FIELDS

TYPED_CONTRACT_VERSION = "4.0.0"
NULLABLE_NUMBER_FIELDS = frozenset({"latitude", "longitude"})
NULLABLE_INTEGER_FIELDS = frozenset({"coordinate_accuracy"})


def typed_row(row: dict[str, str]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for field in ITALIAN_LOCATION_FIELDS:
        value = row[field]
        if field in NULLABLE_NUMBER_FIELDS:
            result[field] = float(value) if value else None
        elif field in NULLABLE_INTEGER_FIELDS:
            result[field] = int(value) if value else None
        else:
            result[field] = value
    return result


def sqlite_column_definition(field: str) -> str:
    quoted = f'"{field}"'
    if field in NULLABLE_NUMBER_FIELDS:
        return f"{quoted} REAL"
    if field in NULLABLE_INTEGER_FIELDS:
        return f"{quoted} INTEGER"
    return f"{quoted} TEXT NOT NULL"
