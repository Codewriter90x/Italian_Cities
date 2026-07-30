"""Shared validation primitives."""

from __future__ import annotations

import csv
from pathlib import Path


QualityChecks = dict[str, dict[str, object]]


def add_error(errors: list[str], message: str, limit: int = 200) -> None:
    if len(errors) < limit:
        errors.append(message)


def add_quality_error(
    errors: list[str],
    checks: QualityChecks,
    check_name: str,
    message: str,
) -> None:
    violations = checks[check_name]["violations"]
    if not isinstance(violations, int):
        raise TypeError(f"{check_name}: violations counter must be an integer")
    checks[check_name]["violations"] = violations + 1
    add_error(errors, f"[{check_name}] {message}")


def completely_blank_record_lines(path: Path) -> list[int]:
    """Return physical or delimiter-only blank data rows, excluding the header."""

    lines = path.read_text(encoding="utf-8-sig").splitlines()
    blank_lines: list[int] = []
    for line_number, line in enumerate(lines[1:], start=2):
        if not line.strip():
            blank_lines.append(line_number)
            continue
        values = next(csv.reader([line]))
        if values and all(not value.strip() for value in values):
            blank_lines.append(line_number)
    return blank_lines
