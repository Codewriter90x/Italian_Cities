# Generated data

Everything in this directory is generated. Do not edit CSV, JSON, XLSX or
SQLite files manually.

Run:

```bash
python3 scripts/build_dataset.py
python3 scripts/check_determinism.py
python3 scripts/validate_dataset.py
```

The v2 canonical inputs are only the declared ISTAT and GeoNames snapshots.
Legacy files never contribute to this directory. The canonical grain and
fields are documented in `SCHEMA.md`.

Release assets are assembled outside this directory:

```bash
python3 scripts/build_release.py
python3 scripts/validate_release.py
```

The historical SQL Server dump and all other files under `legacy/` are not
release sources.
