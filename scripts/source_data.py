#!/usr/bin/env python3
"""Read and verify the clean-room ISTAT and GeoNames source snapshots."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any

from dataset_common import ROOT, SOURCE_MANIFEST, normalize_name, sha256_file

DEFAULT_ISTAT = (
    ROOT
    / "sources/snapshots/istat/Elenco-comuni-italiani-2026-02-21.xlsx"
)
DEFAULT_GEONAMES = (
    ROOT / "sources/snapshots/geonames/IT-2026-07-30.zip"
)
DEFAULT_ISTAT_REGIONS = ROOT / "sources/cache/Limiti01012026_g.zip"

CANONICAL_SOURCE_IDS = (
    "istat_municipalities",
    "geonames_postal_codes",
)
AUXILIARY_SOURCE_IDS = ("istat_region_boundaries",)
ISTAT_NS = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
GEONAMES_FIELDS = (
    "country_code",
    "postal_code",
    "place_name",
    "admin_name1",
    "admin_code1",
    "admin_name2",
    "admin_code2",
    "admin_name3",
    "admin_code3",
    "latitude",
    "longitude",
    "accuracy",
)


def load_manifest(path: Path = SOURCE_MANIFEST) -> dict[str, Any]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("manifest_version") != "3.0.0":
        raise ValueError(f"{path}: manifest_version must be 3.0.0")
    if tuple(manifest.get("canonical_source_ids", ())) != CANONICAL_SOURCE_IDS:
        raise ValueError(
            f"{path}: canonical_source_ids must be {CANONICAL_SOURCE_IDS!r}"
        )
    sources = manifest.get("sources")
    if not isinstance(sources, list):
        raise ValueError(f"{path}: sources must be a list")
    source_ids = [source.get("id") for source in sources]
    if len(source_ids) != len(set(source_ids)):
        raise ValueError(f"{path}: duplicate source id")
    for source_id in (
        *CANONICAL_SOURCE_IDS,
        *AUXILIARY_SOURCE_IDS,
    ):
        if source_id not in source_ids:
            raise ValueError(f"{path}: missing source {source_id}")
    return manifest


def source_by_id(
    manifest: dict[str, Any],
    source_id: str,
) -> dict[str, Any]:
    return next(
        source for source in manifest["sources"] if source["id"] == source_id
    )


def validate_source(
    manifest: dict[str, Any],
    source_id: str,
    path: Path,
) -> dict[str, Any]:
    source = source_by_id(manifest, source_id)
    if not path.is_file():
        raise FileNotFoundError(f"declared source {source_id} is missing: {path}")
    expected_path = ROOT / source["path"]
    if path.resolve() == expected_path.resolve() and not source.get("sha256"):
        raise ValueError(f"declared source {source_id} has no SHA-256")
    actual = sha256_file(path)
    if actual != source["sha256"]:
        raise ValueError(
            f"declared source {source_id} checksum mismatch: "
            f"{actual} != {source['sha256']}"
        )
    return source


def validate_declared_sources(
    manifest_path: Path = SOURCE_MANIFEST,
    *,
    istat_path: Path = DEFAULT_ISTAT,
    geonames_path: Path = DEFAULT_GEONAMES,
    geography_path: Path = DEFAULT_ISTAT_REGIONS,
) -> dict[str, Any]:
    manifest = load_manifest(manifest_path)
    validate_source(manifest, "istat_municipalities", istat_path)
    validate_source(manifest, "geonames_postal_codes", geonames_path)
    validate_source(manifest, "istat_region_boundaries", geography_path)
    return manifest


def _column_index(cell_reference: str) -> int:
    letters = "".join(
        character for character in cell_reference if character.isalpha()
    )
    index = 0
    for character in letters:
        index = index * 26 + ord(character.upper()) - ord("A") + 1
    return index - 1


def _xlsx_rows(path: Path) -> list[list[str]]:
    with zipfile.ZipFile(path) as archive:
        shared_root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
        shared_strings = [
            "".join(
                node.text or "" for node in item.iterfind(".//x:t", ISTAT_NS)
            )
            for item in shared_root.findall("x:si", ISTAT_NS)
        ]
        sheet_root = ET.fromstring(
            archive.read("xl/worksheets/sheet1.xml")
        )

    parsed: list[list[str]] = []
    for row in sheet_root.findall(".//x:sheetData/x:row", ISTAT_NS):
        values = [""] * 27
        for cell in row.findall("x:c", ISTAT_NS):
            index = _column_index(cell.get("r", ""))
            value_node = cell.find("x:v", ISTAT_NS)
            if value_node is None or value_node.text is None:
                value = ""
            elif cell.get("t") == "s":
                value = shared_strings[int(value_node.text)]
            else:
                value = value_node.text
            values[index] = value.strip()
        parsed.append(values)
    return parsed


def load_istat_records(path: Path = DEFAULT_ISTAT) -> list[dict[str, str]]:
    parsed = _xlsx_rows(path)
    records: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in parsed[1:]:
        istat_code = row[4]
        if not re.fullmatch(r"\d{6}", istat_code):
            raise ValueError(f"{path}: invalid ISTAT code {istat_code!r}")
        if istat_code in seen:
            raise ValueError(f"{path}: duplicate ISTAT code {istat_code}")
        seen.add(istat_code)
        name = row[6] or row[5]
        records.append(
            {
                "region_code": row[0].zfill(2),
                "istat_code": istat_code,
                "name": name,
                "bilingual_name": row[5],
                "normalized_name": normalize_name(name),
                "region_name": row[10],
                "province_name": row[11],
                "province_code": row[14],
            }
        )
    records.sort(key=lambda row: row["istat_code"])
    return records


def _geonames_record_id(values: list[str]) -> str:
    digest = hashlib.sha256("\t".join(values).encode("utf-8")).hexdigest()
    return f"GNPC-{digest[:24]}"


def load_geonames_records(
    path: Path = DEFAULT_GEONAMES,
) -> list[dict[str, str]]:
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        if {"IT.txt", "readme.txt"} - names:
            raise ValueError(f"{path}: expected IT.txt and readme.txt")
        with archive.open("IT.txt") as raw:
            reader = csv.reader(
                io.TextIOWrapper(raw, encoding="utf-8", newline=""),
                delimiter="\t",
            )
            records: list[dict[str, str]] = []
            seen: set[str] = set()
            for line_number, values in enumerate(reader, start=1):
                if len(values) != len(GEONAMES_FIELDS):
                    raise ValueError(
                        f"{path}!IT.txt:{line_number}: expected "
                        f"{len(GEONAMES_FIELDS)} fields, found {len(values)}"
                    )
                record = dict(zip(GEONAMES_FIELDS, values, strict=True))
                record_id = _geonames_record_id(values)
                if record_id in seen:
                    raise ValueError(
                        f"{path}!IT.txt:{line_number}: duplicate source record"
                    )
                seen.add(record_id)
                if record["country_code"] != "IT":
                    raise ValueError(
                        f"{path}!IT.txt:{line_number}: country must be IT"
                    )
                if not re.fullmatch(r"\d{5}", record["postal_code"]):
                    raise ValueError(
                        f"{path}!IT.txt:{line_number}: invalid postal code"
                    )
                if record["accuracy"] and not re.fullmatch(
                    r"[1-6]", record["accuracy"]
                ):
                    raise ValueError(
                        f"{path}!IT.txt:{line_number}: invalid accuracy"
                    )
                record["source_record_id"] = record_id
                record["normalized_name"] = normalize_name(
                    record["place_name"]
                )
                records.append(record)
    records.sort(
        key=lambda row: (
            row["normalized_name"],
            row["admin_code2"],
            row["postal_code"],
            row["source_record_id"],
        )
    )
    return records


def manifest_digest(path: Path = SOURCE_MANIFEST) -> str:
    return sha256_file(path)
