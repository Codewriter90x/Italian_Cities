# Example: source-backed data correction

Generated CSV, JSON, XLSX, SQLite and SQL files are never edited directly.
This example shows the evidence and review trail required for a correction.
It is procedural and does not assert that a real Italian Cities record is
wrong.

## 1. Identify the canonical record

Record the stable identifier and current values from the generated CSV:

```text
location_id: IT-COM-000000
field: postal_code
current value: 00000
proposed value: 00001
```

Do not use row numbers: sorting and source snapshots can change them.

## 2. Attach reusable evidence

The issue must provide:

- a public source URL or exact official publication reference;
- the source publisher;
- its reference date;
- the licence and required attribution;
- the exact source record, page or table supporting the change;
- whether the old value is wrong, obsolete or merely incomplete.

A search result, personal observation or another generated aggregator is not
sufficient evidence. Public Nominatim must not be queried systematically.

## 3. Reproduce the correction in the pipeline

The pull request updates a declared source snapshot or a narrowly scoped,
reviewable transformation. It must not patch `data/*.csv` directly.

For an upstream snapshot change:

```bash
python scripts/update_sources.py \
  --download geonames_postal_codes \
  --output sources/cache/IT-YYYY-MM-DD.zip
```

After inspecting the staged file, update `sources/manifest.json` explicitly
with its dated path, SHA-256, reference date, licence and attribution. Then:

```bash
python scripts/build_dataset.py
python scripts/check_determinism.py
python scripts/validate_dataset.py
```

## 4. Review the complete impact

The pull request must explain:

- which source records changed;
- all generated rows affected by the transformation;
- changes in `reports/release-diff.json`;
- changes in `reports/reconciliation-backlog.json`;
- whether coverage or operational-readiness claims changed.

A correction is rejected if it silently promotes an ambiguous match, removes
provenance, changes unrelated records or cannot be reproduced from the
declared evidence.

## 5. Acceptance checklist

- [ ] issue form includes source, date, licence and attribution;
- [ ] no generated file was manually edited;
- [ ] source checksum validation passes;
- [ ] schema, integrity, territory and coordinate tests pass;
- [ ] two builds are deterministic;
- [ ] all export formats remain semantically equivalent;
- [ ] reviewer can trace the canonical row back to source record IDs.
