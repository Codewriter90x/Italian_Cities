# Source cache

`sources/cache/` is intentionally ignored. It contains downloaded reference
files used to reproduce the Milestone 1 normalization, but those files are not
the historical source of the legacy dataset.

Required reference:

| Local filename | Source | Reference date | SHA-256 |
| --- | --- | --- | --- |
| `Elenco-comuni-italiani-2026-02-21.xlsx` | <https://www.istat.it/storage/codici-unita-amministrative/Elenco-comuni-italiani.xlsx> | 2026-02-21 | `83842076860450f7e482daecea6b7a769f5f93d0bf5b0d48802b44896d7a26d5` |

Download the file without renaming it, verify the checksum, then run:

```bash
python3 scripts/normalize_legacy.py
python3 scripts/validate_milestone1.py
```

The ISTAT file is used only to make conservative, exact matches by current
Italian municipality name and province code. Non-matches are not guessed.

See `DATA_SOURCES.md` for provenance and licensing details.
