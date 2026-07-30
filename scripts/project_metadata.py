#!/usr/bin/env python3
"""Load and validate the repository-wide dataset metadata contract."""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROJECT_METADATA_PATH = ROOT / "project.json"
SEMVER = re.compile(r"^v\d+\.\d+\.\d+$")
SCHEMA_VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")


def load_project_metadata(path: Path = PROJECT_METADATA_PATH) -> dict[str, Any]:
    metadata = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "build_date",
        "dataset_version",
        "geonames_reference_date",
        "istat_reference_date",
        "legacy_reference_date",
        "license_status",
        "operational_data_readiness",
        "previous_release",
        "quality_gate_version",
        "release_status",
        "schema_version",
        "structural_quality",
    }
    missing = required - set(metadata)
    if missing:
        raise ValueError(f"{path}: missing metadata keys {sorted(missing)}")
    if not SEMVER.fullmatch(metadata["dataset_version"]):
        raise ValueError(f"{path}: dataset_version must be vMAJOR.MINOR.PATCH")
    if not SCHEMA_VERSION_PATTERN.fullmatch(metadata["schema_version"]):
        raise ValueError(f"{path}: schema_version must be MAJOR.MINOR.PATCH")
    if not SCHEMA_VERSION_PATTERN.fullmatch(metadata["quality_gate_version"]):
        raise ValueError(f"{path}: quality_gate_version must be MAJOR.MINOR.PATCH")
    if metadata["release_status"] not in {"prerelease", "stable"}:
        raise ValueError(f"{path}: release_status must be prerelease or stable")
    for key in (
        "build_date",
        "geonames_reference_date",
        "istat_reference_date",
        "legacy_reference_date",
    ):
        try:
            date.fromisoformat(metadata[key])
        except (TypeError, ValueError) as error:
            raise ValueError(f"{path}: {key} must use YYYY-MM-DD") from error
    if not metadata["license_status"].strip():
        raise ValueError(f"{path}: license_status must not be empty")
    if metadata["structural_quality"] != "passed":
        raise ValueError(f"{path}: structural_quality must be passed")
    if (
        metadata["operational_data_readiness"]
        != "experimental_non_official"
    ):
        raise ValueError(
            f"{path}: operational_data_readiness must remain "
            "experimental_non_official"
        )

    previous = metadata["previous_release"]
    previous_required = {"canonical_path", "canonical_sha256", "version"}
    previous_missing = previous_required - set(previous)
    if previous_missing:
        raise ValueError(
            f"{path}: missing previous_release keys {sorted(previous_missing)}"
        )
    if not SEMVER.fullmatch(previous["version"]):
        raise ValueError(f"{path}: previous release version is invalid")
    if not re.fullmatch(r"[0-9a-f]{64}", previous["canonical_sha256"]):
        raise ValueError(f"{path}: previous release SHA-256 is invalid")
    baseline_path = Path(previous["canonical_path"])
    try:
        (ROOT / baseline_path).resolve().relative_to(ROOT.resolve())
    except ValueError as error:
        raise ValueError(
            f"{path}: previous release path must stay inside the repository"
        ) from error
    if baseline_path.is_absolute() or ".." in baseline_path.parts:
        raise ValueError(f"{path}: previous release path must be repository-relative")
    return metadata


def version_number(version: str) -> int:
    """Encode MAJOR.MINOR.PATCH for SQLite PRAGMA user_version."""

    major, minor, patch = (int(part) for part in version.split("."))
    if any(part > 99 for part in (major, minor, patch)):
        raise ValueError("schema version parts must be between 0 and 99")
    return major * 10_000 + minor * 100 + patch


PROJECT = load_project_metadata()
BUILD_DATE = PROJECT["build_date"]
DATASET_VERSION = PROJECT["dataset_version"]
GEONAMES_REFERENCE_DATE = PROJECT["geonames_reference_date"]
ISTAT_REFERENCE_DATE = PROJECT["istat_reference_date"]
LEGACY_REFERENCE_DATE = PROJECT["legacy_reference_date"]
OPERATIONAL_DATA_READINESS = PROJECT["operational_data_readiness"]
PREVIOUS_RELEASE = PROJECT["previous_release"]
QUALITY_GATE_VERSION = PROJECT["quality_gate_version"]
RELEASE_STATUS = PROJECT["release_status"]
SCHEMA_VERSION = PROJECT["schema_version"]
STRUCTURAL_QUALITY = PROJECT["structural_quality"]
