#!/usr/bin/env python3
"""Assemble the deterministic release asset directory."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from dataset_common import (
    GENERATED_PATHS,
    ITALIAN_LOCATION_FIELDS,
    ROOT,
    read_csv_rows,
    sha256_file,
)
from export_sql import export_sql
from project_metadata import DATASET_VERSION

RELEASE_VERSION = DATASET_VERSION
DEFAULT_OUTPUT = ROOT / "dist" / RELEASE_VERSION
RELEASE_ASSETS = {
    "municipalities.csv": GENERATED_PATHS["municipalities"],
    "localities.csv": GENERATED_PATHS["localities"],
    "postal_codes.csv": GENERATED_PATHS["postal_codes"],
    "italian_locations.csv": GENERATED_PATHS["italian_locations"],
    "italian_locations.json": GENERATED_PATHS["json"],
    "italian_locations.xlsx": GENERATED_PATHS["xlsx"],
    "italian_locations.sqlite": GENERATED_PATHS["sqlite"],
}
SQL_ASSET = "italian_locations.sql"
CHECKSUM_ASSET = "SHA256SUMS"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default=RELEASE_VERSION)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def build_release(output: Path, version: str = RELEASE_VERSION) -> list[str]:
    if version != RELEASE_VERSION:
        raise ValueError(
            f"unsupported release version {version!r}; expected {RELEASE_VERSION!r}"
        )
    output.mkdir(parents=True, exist_ok=True)

    for name, source in RELEASE_ASSETS.items():
        if not source.exists():
            raise FileNotFoundError(f"missing generated release input: {source}")
        shutil.copyfile(source, output / name)

    canonical_rows = read_csv_rows(
        GENERATED_PATHS["italian_locations"],
        ITALIAN_LOCATION_FIELDS,
    )
    export_sql(canonical_rows, output / SQL_ASSET)

    asset_names = [*RELEASE_ASSETS, SQL_ASSET]
    checksums = "".join(
        f"{sha256_file(output / name)}  {name}\n" for name in asset_names
    )
    (output / CHECKSUM_ASSET).write_text(checksums, encoding="utf-8")
    return [*asset_names, CHECKSUM_ASSET]


def main() -> None:
    args = parse_args()
    output = args.output or ROOT / "dist" / args.version
    assets = build_release(output, args.version)
    for name in assets:
        print(output / name)


if __name__ == "__main__":
    main()
