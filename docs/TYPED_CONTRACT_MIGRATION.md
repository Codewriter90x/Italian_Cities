# Typed export contract migration

The published v2.0.0 assets remain byte-for-byte unchanged. In schema 3.0.0,
CSV, JSON, SQLite and SQL expose source columns as strings and use an empty
string for missing values.

The next major schema is designed as `4.0.0`:

| Field | Schema 3 | Schema 4 |
| --- | --- | --- |
| `latitude`, `longitude` | string, `""` when missing | number or `null` |
| `coordinate_accuracy` | string, `""` when missing | integer or `null` |
| identifiers and CAP | string | string |

Consumers can test the preview without changing committed release assets:

```bash
python scripts/export_typed_json.py \
  --output dist/italian_locations.typed.json \
  --sqlite-output dist/italian_locations.typed.sqlite
```

The generated JSON is validated against
`schemas/italian_locations-v4.schema.json` with a Draft 2020-12 validator:

```bash
python scripts/validate_typed_contract.py
```

The schema fixes the exact field order, numeric/null types, enums, Italian
coordinate bounds and the consistency rules for missing CAP and coordinates.
A negative regression test proves that string coordinates are rejected.

The preview SQLite table uses `REAL`, `INTEGER` and `NULL` directly. The
original v2 JSON, SQLite table and SQL script stay unchanged.

The default JSON/table contract will switch only in a new major release. That
release must include a migration note, cross-format type assertions and a new
immutable release bundle; v2 assets must never be overwritten.
