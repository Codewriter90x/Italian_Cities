#!/usr/bin/env python3
"""Build a deterministic, evidence-first reconciliation backlog."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from dataset_common import (
    GENERATED_PATHS,
    LOCALITY_FIELDS,
    MUNICIPALITY_FIELDS,
    REPORTS_DIR,
    read_csv_rows,
    write_json,
)
from project_metadata import DATASET_VERSION, SCHEMA_VERSION

DEFAULT_OUTPUT = REPORTS_DIR / "reconciliation-backlog.json"


def ranked(counter: Counter[str]) -> list[dict[str, object]]:
    return [
        {"name": name, "records": count}
        for name, count in sorted(
            counter.items(),
            key=lambda item: (-item[1], item[0]),
        )
    ]


def build_backlog(
    municipalities: list[dict[str, str]],
    localities: list[dict[str, str]],
) -> dict[str, object]:
    municipality_province_codes = {
        row["province_code"] for row in municipalities
    }
    noncurrent_codes = sorted(
        {
            row["province_code"]
            for row in localities
            if row["province_code"] not in municipality_province_codes
        }
    )
    missing_postal = [
        row
        for row in municipalities
        if row["coordinate_verification"] == "missing"
    ]
    outcomes = Counter(row["reconciliation_outcome"] for row in localities)
    return {
        "dataset_version": DATASET_VERSION,
        "schema_version": SCHEMA_VERSION,
        "status": "review_required",
        "policy": {
            "automatic_fuzzy_promotion": False,
            "public_nominatim_bulk_geocoding": False,
            "evidence_required": [
                "source",
                "reference_date",
                "license",
                "reproducible_transformation",
            ],
        },
        "summary": {
            "municipalities": len(municipalities),
            "unreconciled_localities": len(localities),
            "municipalities_without_geonames_postal_match": len(missing_postal),
            "noncurrent_source_province_codes": noncurrent_codes,
            "reconciliation_outcomes": dict(sorted(outcomes.items())),
        },
        "unreconciled_by_region": ranked(
            Counter(row["region_name"] for row in localities)
        ),
        "unreconciled_by_province": ranked(
            Counter(
                f"{row['province_name']} ({row['province_code']})"
                for row in localities
            )
        ),
        "missing_municipality_match_by_region": ranked(
            Counter(row["region_name"] for row in missing_postal)
        ),
        "review_order": [
            {
                "priority": 1,
                "segment": "noncurrent_source_province_codes",
                "reason": "Historical source codes need explicit aliases.",
            },
            {
                "priority": 2,
                "segment": "municipalities_without_geonames_postal_match",
                "reason": "Municipalities remain canonical but lack CAP/coordinates.",
            },
            {
                "priority": 3,
                "segment": "highest_unreconciled_regions",
                "reason": "Review high-volume segments using licensed evidence.",
            },
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_backlog(
        read_csv_rows(GENERATED_PATHS["municipalities"], MUNICIPALITY_FIELDS),
        read_csv_rows(GENERATED_PATHS["localities"], LOCALITY_FIELDS),
    )
    write_json(args.output, report)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
