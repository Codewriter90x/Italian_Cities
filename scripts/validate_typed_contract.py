#!/usr/bin/env python3
"""Validate the opt-in schema 4 typed JSON preview."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any

from dataset_common import GENERATED_PATHS, ROOT
from export_typed_json import export_typed_json
from jsonschema.validators import validator_for

DEFAULT_SCHEMA = ROOT / "schemas/italian_locations-v4.schema.json"


def validate_payload(
    payload: dict[str, Any],
    schema: dict[str, Any],
) -> list[str]:
    validator_class = validator_for(schema)
    validator_class.check_schema(schema)
    validator = validator_class(schema)
    errors = sorted(
        validator.iter_errors(payload),
        key=lambda error: [str(part) for part in error.absolute_path],
    )
    return [
        f"{'/'.join(str(part) for part in error.absolute_path) or '<root>'}: "
        f"{error.message}"
        for error in errors
    ]


def validate_typed_contract(
    *,
    schema_path: Path = DEFAULT_SCHEMA,
    input_path: Path | None = None,
) -> dict[str, Any]:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    if input_path is None:
        with tempfile.TemporaryDirectory(prefix="italian-cities-schema4-") as folder:
            generated = Path(folder) / "italian_locations.typed.json"
            export_typed_json(
                GENERATED_PATHS["italian_locations"],
                generated,
            )
            payload = json.loads(generated.read_text(encoding="utf-8"))
    else:
        payload = json.loads(input_path.read_text(encoding="utf-8"))
    errors = validate_payload(payload, schema)
    return {
        "status": "passed" if not errors else "failed",
        "schema": str(schema_path),
        "rows": len(payload.get("rows", [])),
        "errors": errors,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--input", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = validate_typed_contract(
        schema_path=args.schema,
        input_path=args.input,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    if report["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
