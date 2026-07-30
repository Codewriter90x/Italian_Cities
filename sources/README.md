# Declared sources

`manifest.json` is the machine-readable contract for every primary input
consumed by the pipeline. Each entry records local path, role, reference date,
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
for conservative exact municipality classification and official province
labels; non-matches are not guessed.

The previous release baseline is not an input source. It is declared separately
in `project.json` and is read only after the new canonical dataset has been
built, to produce `reports/release-diff.json`.

To refresh the source, download a new official file, preserve it under a new
date-stamped filename, update `manifest.json`, document the new reference date
and regenerate all outputs. Never overwrite an existing snapshot.

See `DATA_SOURCES.md` for provenance and licensing analysis.

Before adding a geographic source for missing coordinates, follow
`COORDINATE_ENRICHMENT.md`. In particular, do not query the public Nominatim
service systematically for this dataset.

## GitHub Pages geographic base

The Pages map uses the generalized ISTAT administrative boundaries dated
2026-01-01, region layer only. This is a presentation source: it does not
enrich or verify the dataset coordinates.

| Cache filename | Source | Reference date | SHA-256 |
| --- | --- | --- | --- |
| `cache/Limiti01012026_g.zip` | [ISTAT generalized administrative boundaries 2026](https://www.istat.it/notizia/confini-delle-unita-amministrative-a-fini-statistici-al-1-gennaio-2018-2/) | 2026-01-01 | `b011a590656c3a3ebc297fba80726a376aa843b6f164641cf6a4a990021a81d6` |

ISTAT data are reused under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The committed
`site/assets/italy-regions.geojson` derivative is reprojected to EPSG:4326,
topology-preserving simplified and rounded; its embedded metadata records the
source and modifications.

Regenerate it without committing the cached archive:

```bash
curl -fsS \
  https://www.istat.it/storage/cartografia/confini_amministrativi/generalizzati/2026/Limiti01012026_g.zip \
  -o sources/cache/Limiti01012026_g.zip
python3 -m pip install -r requirements-geography.txt
python3 scripts/build_geography.py
```
