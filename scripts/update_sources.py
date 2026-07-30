#!/usr/bin/env python3
"""Check canonical upstream snapshots and stage explicit source downloads."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import ssl
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, BinaryIO
from urllib.request import Request, urlopen

import truststore
from dataset_common import ROOT, SOURCE_MANIFEST, sha256_file, write_json
from source_data import CANONICAL_SOURCE_IDS, load_manifest, source_by_id

USER_AGENT = (
    "Italian_Cities source freshness checker "
    "(https://github.com/Codewriter90x/Italian_Cities)"
)
TLS_CONTEXT = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)


def download(url: str, destination: Path) -> dict[str, str]:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    digest = hashlib.sha256()
    with urlopen(
        request,
        timeout=90,
        context=TLS_CONTEXT,
    ) as response:  # noqa: S310
        last_modified = response.headers.get("Last-Modified", "")
        etag = response.headers.get("ETag", "")
        with destination.open("wb") as output:
            stream: BinaryIO = response
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
                output.write(chunk)
    if destination.stat().st_size == 0:
        raise ValueError(f"{url}: upstream returned an empty artifact")
    return {
        "sha256": digest.hexdigest(),
        "last_modified": last_modified,
        "etag": etag,
    }


def inspect_source(source: dict[str, Any]) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="italian-cities-source-") as folder:
        candidate = Path(folder) / "candidate"
        remote = download(str(source["url"]), candidate)
    declared_sha256 = str(source["sha256"])
    return {
        "id": source["id"],
        "url": source["url"],
        "declared_path": source["path"],
        "declared_sha256": declared_sha256,
        "remote_sha256": remote["sha256"],
        "remote_last_modified": remote["last_modified"],
        "remote_etag": remote["etag"],
        "status": (
            "current"
            if remote["sha256"] == declared_sha256
            else "update_available"
        ),
    }


def check_sources(manifest_path: Path = SOURCE_MANIFEST) -> dict[str, Any]:
    manifest = load_manifest(manifest_path)
    sources = [
        inspect_source(source_by_id(manifest, source_id))
        for source_id in CANONICAL_SOURCE_IDS
    ]
    changed = [source["id"] for source in sources if source["status"] != "current"]
    return {
        "checked_at": datetime.now(UTC).isoformat(),
        "manifest": str(manifest_path.resolve().relative_to(ROOT)),
        "status": "updates_available" if changed else "current",
        "updates_available": changed,
        "sources": sources,
    }


def stage_download(
    source_id: str,
    output: Path,
    manifest_path: Path = SOURCE_MANIFEST,
) -> dict[str, Any]:
    manifest = load_manifest(manifest_path)
    if source_id not in CANONICAL_SOURCE_IDS:
        raise ValueError(
            f"{source_id!r} is not a canonical source: {CANONICAL_SOURCE_IDS}"
        )
    if output.exists():
        raise FileExistsError(
            f"refusing to overwrite {output}; choose a new dated path"
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    source = source_by_id(manifest, source_id)
    with tempfile.NamedTemporaryFile(
        prefix=f"{source_id}-",
        dir=output.parent,
        delete=False,
    ) as handle:
        temporary = Path(handle.name)
    try:
        remote = download(str(source["url"]), temporary)
        os.replace(temporary, output)
    finally:
        if temporary.exists():
            temporary.unlink()
    return {
        "status": "staged",
        "source_id": source_id,
        "output": str(output),
        "sha256": sha256_file(output),
        "remote_last_modified": remote["last_modified"],
        "remote_etag": remote["etag"],
        "next_steps": [
            "inspect the staged artifact",
            "update sources/manifest.json explicitly",
            "rebuild and review every generated diff",
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument(
        "--check",
        action="store_true",
        help="Download canonical upstream artifacts to a temporary directory.",
    )
    action.add_argument(
        "--download",
        choices=CANONICAL_SOURCE_IDS,
        metavar="SOURCE_ID",
        help="Stage one upstream artifact without editing the manifest.",
    )
    parser.add_argument("--manifest", type=Path, default=SOURCE_MANIFEST)
    parser.add_argument(
        "--output",
        type=Path,
        help="New, non-existing path required by --download.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        help="Optional JSON report path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.download:
        if args.output is None:
            raise SystemExit("--output is required with --download")
        report = stage_download(args.download, args.output, args.manifest)
    else:
        report = check_sources(args.manifest)
    if args.report:
        write_json(args.report, report)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
