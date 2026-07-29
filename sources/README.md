# Declared sources

`manifest.json` is the machine-readable contract for every input consumed by
the Milestone 2 pipeline. Each entry records local path, role, reference date,
checksum, licence status and public URL.

## Versioned ISTAT snapshot

The exact reference consumed by the build is preserved in the repository:

| Local filename | Source | Reference date | SHA-256 |
| --- | --- | --- | --- |
| `snapshots/istat/Elenco-comuni-italiani-2026-02-21.xlsx` | <https://www.istat.it/storage/codici-unita-amministrative/Elenco-comuni-italiani.xlsx> | 2026-02-21 | `83842076860450f7e482daecea6b7a769f5f93d0bf5b0d48802b44896d7a26d5` |

The snapshot is distributed under the terms and attribution described in
`snapshots/istat/README.md`; it is not relicensed under the repository's
historical CC0 file.

Verify and run:

```bash
shasum -a 256 sources/snapshots/istat/Elenco-comuni-italiani-2026-02-21.xlsx
python3 scripts/build_dataset.py
python3 scripts/validate_dataset.py
```

The build refuses missing or checksum-mismatched inputs. The ISTAT file is used
only for conservative exact municipality classification; non-matches are not
guessed.

To refresh the source, download a new official file, preserve it under a new
date-stamped filename, update `manifest.json`, document the new reference date
and regenerate all outputs. Never overwrite an existing snapshot.

See `DATA_SOURCES.md` for provenance and licensing analysis.
