#!/usr/bin/env python3
"""Build twice and fail when generated outputs are not deterministic."""

from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

from dataset_common import (
    GENERATED_PATHS,
    ITALIAN_LOCATION_FIELDS,
    REPORTS_DIR,
    ROOT,
    record_digest,
    sha256_file,
    write_json,
)
from project_metadata import QUALITY_GATE_VERSION

DEFAULT_REPORT = REPORTS_DIR / "determinism.json"
BYTE_STABLE_PATHS = {
    "municipalities_csv": GENERATED_PATHS["municipalities"],
    "localities_csv": GENERATED_PATHS["localities"],
    "postal_codes_csv": GENERATED_PATHS["postal_codes"],
    "italian_locations_csv": GENERATED_PATHS["italian_locations"],
    "italian_locations_json": GENERATED_PATHS["json"],
    "italian_locations_xlsx": GENERATED_PATHS["xlsx"],
    "build_metadata": REPORTS_DIR / "build-metadata.json",
    "release_diff_report": REPORTS_DIR / "release-diff.json",
    "reconciliation_backlog": REPORTS_DIR / "reconciliation-backlog.json",
    "export_manifest": REPORTS_DIR / "export-manifest.json",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def sqlite_semantic_digest(path: Path) -> str:
    connection = sqlite3.connect(path)
    try:
        quoted_fields = ", ".join(f'"{field}"' for field in ITALIAN_LOCATION_FIELDS)
        rows = [
            dict(zip(ITALIAN_LOCATION_FIELDS, values, strict=True))
            for values in connection.execute(
                f'SELECT {quoted_fields} FROM "italian_locations" '
                'ORDER BY "normalized_name", "province_code", "postal_code", '
                '"location_id", "location_postal_id"'
            )
        ]
    finally:
        connection.close()
    return record_digest(rows)


def collect_signatures() -> dict[str, dict[str, str]]:
    return {
        "byte_sha256": {
            name: sha256_file(path)
            for name, path in sorted(BYTE_STABLE_PATHS.items())
        },
        "semantic_sha256": {
            "italian_locations_sqlite": sqlite_semantic_digest(
                GENERATED_PATHS["sqlite"]
            )
        },
    }


def run_build() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_dataset.py")],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"dataset build failed: {detail}")


def main() -> None:
    args = parse_args()
    try:
        run_build()
        first = collect_signatures()
        run_build()
        second = collect_signatures()
        mismatches = {
            signature_type: sorted(
                name
                for name in first[signature_type]
                if first[signature_type][name] != second[signature_type][name]
            )
            for signature_type in first
        }
        mismatches = {
            signature_type: names
            for signature_type, names in mismatches.items()
            if names
        }
        report: dict[str, object] = {
            "status": "passed" if not mismatches else "failed",
            "quality_gate_version": QUALITY_GATE_VERSION,
            "runs": 2,
            "comparison": {
                "byte_identical": not bool(mismatches.get("byte_sha256")),
                "sqlite_semantically_identical": not bool(
                    mismatches.get("semantic_sha256")
                ),
            },
            "signatures": second,
            "mismatches": mismatches,
        }
    except (FileNotFoundError, KeyError, RuntimeError, sqlite3.DatabaseError) as error:
        report = {
            "status": "failed",
            "quality_gate_version": QUALITY_GATE_VERSION,
            "runs": 2,
            "comparison": {},
            "signatures": {},
            "mismatches": {},
            "errors": [str(error)],
        }

    write_json(args.report, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
