#!/usr/bin/env python3
"""Require every third-party GitHub Action to use an immutable commit SHA."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from dataset_common import ROOT

WORKFLOWS = ROOT / ".github/workflows"
USES_PATTERN = re.compile(
    r"^\s*(?:-\s*)?uses:\s*([^#\s]+)",
    re.MULTILINE,
)
PIN_PATTERN = re.compile(r"^[^@\s]+@[0-9a-fA-F]{40}$")


def find_unpinned_actions(workflows: Path = WORKFLOWS) -> list[str]:
    errors: list[str] = []
    for path in sorted(workflows.glob("*.y*ml")):
        source = path.read_text(encoding="utf-8")
        for match in USES_PATTERN.finditer(source):
            reference = match.group(1).strip("\"'")
            if reference.startswith("./"):
                continue
            if not PIN_PATTERN.fullmatch(reference):
                line = source.count("\n", 0, match.start()) + 1
                display_path = (
                    path.relative_to(ROOT)
                    if path.is_relative_to(ROOT)
                    else path
                )
                errors.append(
                    f"{display_path}:{line}: {reference} is not "
                    "pinned to a 40-character commit SHA"
                )
    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workflows", type=Path, default=WORKFLOWS)
    return parser.parse_args()


def main() -> None:
    errors = find_unpinned_actions(parse_args().workflows)
    report = {
        "status": "passed" if not errors else "failed",
        "errors": errors,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
