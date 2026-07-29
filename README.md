# Italian Cities

Dataset riproducibile di comuni e località italiane associate a un CAP.

> **Stato:** Milestone 3. Gli artefatti sotto `data/` sono generati: non
> modificarli manualmente. La pubblicazione del dataset resta subordinata al
> gate di provenienza e licenza descritto in
> [`DATA_SOURCES.md`](DATA_SOURCES.md).

## Output

La pipeline produce quattro tabelle CSV:

| File | Grana | Righe |
| --- | --- | ---: |
| `data/municipalities.csv` | comune riconosciuto nel dataset | 7.186 |
| `data/localities.csv` | località postale non classificata | 7.294 |
| `data/postal_codes.csv` | relazione luogo-CAP | 14.480 |
| `data/italian_locations.csv` | vista canonica unificata | 14.480 |

La vista canonica è esportata anche come:

- `data/italian_locations.json`;
- `data/italian_locations.xlsx`;
- `data/italian_locations.sqlite`.

CSV, JSON, XLSX e SQLite sono verificati record per record contro lo stesso
contratto. I CAP restano stringhe di cinque caratteri, compresi gli zeri
iniziali.

## Build

Prerequisiti:

- Python 3.11 o successivo;
- `XlsxWriter` per l'export XLSX.
- il riferimento ISTAT dichiarato in [`sources/README.md`](sources/README.md).

```bash
python3 -m pip install -r requirements.txt
python3 scripts/build_dataset.py
python3 scripts/check_determinism.py
python3 scripts/validate_dataset.py
python3 -m unittest discover -s tests -v
```

`build_dataset.py` è l'orchestratore: verifica i checksum delle fonti,
normalizza, costruisce le quattro tabelle, richiama gli exporter e produce
`reports/milestone2-diff.json`.

Il workflow completo è documentato in
[`DATASET_PIPELINE.md`](DATASET_PIPELINE.md).

Ogni pull request esegue il check bloccante `Data quality gate`: schema,
identificativi, CAP, codici ISTAT, gerarchia territoriale, coordinate,
duplicati, integrità fra tabelle e doppia build deterministica devono passare.

## Qualità e limiti

- 7.186 record sono comuni riconosciuti tramite corrispondenza esatta con
  ISTAT 2026-02-21;
- 7.294 record restano località postali non classificate;
- 2.092 record restano senza coordinate;
- nessuna classificazione, relazione padre o coordinata viene inventata;
- il Nominatim pubblico non viene usato per il bulk geocoding; la strategia
  ammessa è descritta in
  [`COORDINATE_ENRICHMENT.md`](COORDINATE_ENRICHMENT.md);
- la baseline della Milestone 1 è preservata sotto
  `legacy/milestone-1-canonical/`.

## English summary

This repository now uses a generated-data pipeline. Do not edit CSV, JSON,
XLSX, SQLite or legacy exports by hand. Run `scripts/build_dataset.py`, validate
all formats with `scripts/validate_dataset.py`, and include a declared,
checksummed source for every data change.
