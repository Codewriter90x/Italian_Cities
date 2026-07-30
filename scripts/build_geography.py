#!/usr/bin/env python3
"""Build the simplified Pages map from the official ISTAT region boundaries."""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "sources" / "cache" / "Limiti01012026_g.zip"
DEFAULT_OUTPUT = ROOT / "site" / "assets" / "italy-regions.geojson"
SOURCE_URL = (
    "https://www.istat.it/storage/cartografia/confini_amministrativi/"
    "generalizzati/2026/Limiti01012026_g.zip"
)
SOURCE_SHA256 = "b011a590656c3a3ebc297fba80726a376aa843b6f164641cf6a4a990021a81d6"
SOURCE_REFERENCE_DATE = "2026-01-01"
SHAPEFILE_ROOT = "Reg01012026_g/Reg01012026_g_WGS84"
SHAPEFILE_SUFFIXES = (".dbf", ".prj", ".shp", ".shx")
SIMPLIFY_TOLERANCE_DEGREES = 0.01


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rounded(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, 5)
    if isinstance(value, (list, tuple)):
        return [rounded(item) for item in value]
    if isinstance(value, dict):
        return {key: rounded(item) for key, item in value.items()}
    return value


def extract_region_layer(source: Path, destination: Path) -> Path:
    required = {f"{SHAPEFILE_ROOT}{suffix}" for suffix in SHAPEFILE_SUFFIXES}
    with zipfile.ZipFile(source) as archive:
        missing = required - set(archive.namelist())
        if missing:
            raise ValueError(f"ISTAT archive is missing: {sorted(missing)}")
        for member in sorted(required):
            archive.extract(member, destination)
    return destination / SHAPEFILE_ROOT


def build_geography(source: Path, output: Path) -> dict[str, Any]:
    import shapefile
    from pyproj import Transformer
    from shapely.geometry import mapping, shape
    from shapely.ops import transform

    source = source.resolve()
    output = output.resolve()
    if not source.is_file():
        raise FileNotFoundError(
            f"{source} is missing; download the declared ISTAT archive first"
        )
    actual_sha256 = sha256(source)
    if actual_sha256 != SOURCE_SHA256:
        raise ValueError(
            f"{source}: SHA-256 mismatch: {actual_sha256} != {SOURCE_SHA256}"
        )

    with tempfile.TemporaryDirectory() as directory:
        layer = extract_region_layer(source, Path(directory))
        projection = layer.with_suffix(".prj").read_text(encoding="utf-8")
        transformer = Transformer.from_crs(projection, "EPSG:4326", always_xy=True)
        reader = shapefile.Reader(str(layer.with_suffix(".shp")))
        features: list[dict[str, Any]] = []
        for shape_record in reader.iterShapeRecords():
            properties = shape_record.record.as_dict()
            geometry = shape(shape_record.shape.__geo_interface__)
            geometry = transform(transformer.transform, geometry)
            geometry = geometry.simplify(
                SIMPLIFY_TOLERANCE_DEGREES,
                preserve_topology=True,
            )
            features.append(
                {
                    "type": "Feature",
                    "properties": {
                        "region_code": f"{int(properties['COD_REG']):02d}",
                        "region_name": properties["DEN_REG"],
                    },
                    "geometry": rounded(mapping(geometry)),
                }
            )

    features.sort(key=lambda feature: feature["properties"]["region_code"])
    payload = {
        "type": "FeatureCollection",
        "source": {
            "publisher": "Istituto nazionale di statistica (ISTAT)",
            "reference_date": SOURCE_REFERENCE_DATE,
            "url": SOURCE_URL,
            "archive_sha256": SOURCE_SHA256,
            "layer": f"{SHAPEFILE_ROOT}.shp",
            "license": "CC BY 4.0",
            "modifications": (
                "Reprojected to EPSG:4326, simplified with topology preserved "
                f"at {SIMPLIFY_TOLERANCE_DEGREES} degrees, coordinates rounded "
                "to five decimals."
            ),
        },
        "features": features,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    return {
        "output": str(output.relative_to(ROOT)),
        "features": len(features),
        "sha256": sha256(output),
        "source_sha256": actual_sha256,
    }


def check_geography(
    source: Path,
    output: Path,
    *,
    require_rebuild: bool = False,
) -> dict[str, Any]:
    if not output.is_file():
        raise FileNotFoundError(f"committed geography is missing: {output}")
    payload = json.loads(output.read_text(encoding="utf-8"))
    if payload.get("type") != "FeatureCollection":
        raise ValueError(f"{output}: expected a GeoJSON FeatureCollection")
    provenance = payload.get("source", {})
    expected_provenance = {
        "reference_date": SOURCE_REFERENCE_DATE,
        "url": SOURCE_URL,
        "archive_sha256": SOURCE_SHA256,
        "layer": f"{SHAPEFILE_ROOT}.shp",
        "license": "CC BY 4.0",
    }
    for field, expected in expected_provenance.items():
        if provenance.get(field) != expected:
            raise ValueError(
                f"{output}: source.{field} is {provenance.get(field)!r}; "
                f"expected {expected!r}"
            )
    features = payload.get("features")
    if not isinstance(features, list) or len(features) != 20:
        raise ValueError(f"{output}: expected exactly 20 region features")
    region_codes = [
        feature.get("properties", {}).get("region_code")
        for feature in features
    ]
    if region_codes != sorted(region_codes) or len(set(region_codes)) != 20:
        raise ValueError(f"{output}: region codes must be unique and sorted")

    rebuild_status = "skipped_cache_not_present"
    if source.is_file():
        try:
            with tempfile.TemporaryDirectory() as directory:
                candidate = Path(directory) / output.name
                build_geography(source, candidate)
                if candidate.read_bytes() != output.read_bytes():
                    raise ValueError(
                        f"{output}: committed geography differs from a clean rebuild"
                    )
                rebuild_status = "passed"
        except ModuleNotFoundError:
            if require_rebuild:
                raise
            rebuild_status = "skipped_geography_dependencies_not_installed"
    return {
        "status": "passed",
        "output": str(output.resolve().relative_to(ROOT)),
        "features": len(features),
        "sha256": sha256(output),
        "source_rebuild": rebuild_status,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--check",
        action="store_true",
        help=(
            "Validate the committed GeoJSON and compare it with a clean "
            "rebuild when the declared source archive is available."
        ),
    )
    parser.add_argument(
        "--require-rebuild",
        action="store_true",
        help="Fail unless --check can rebuild from the declared source archive.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = (
        check_geography(
            args.source,
            args.output,
            require_rebuild=args.require_rebuild,
        )
        if args.check
        else build_geography(args.source, args.output)
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
