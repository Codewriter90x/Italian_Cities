# Italian Cities

Dataset italiano di comuni e località associate a un CAP.

> **Stato:** Milestone 1, working copy non pubblicata. La provenienza completa
> del dataset legacy e l'applicabilità della licenza CC0 presente alla radice
> non sono dimostrate. Prima di una release è necessario chiudere il gate
> descritto in [`DATA_SOURCES.md`](DATA_SOURCES.md).

## Dataset canonico

Il file canonico è [`data/italian_postal_localities.csv`](data/italian_postal_localities.csv).
Contiene 14.480 record:

- 7.186 corrispondenze esatte con comuni presenti nell'elenco ISTAT di
  riferimento del 21 febbraio 2026;
- 7.294 località postali non classificate, che possono comprendere frazioni,
  località, denominazioni storiche o comuni non riconciliati;
- 12.388 record con coordinate, di cui uno corretto e documentato;
- 2.092 record senza coordinate, rappresentate da campi vuoti.

Il CAP è conservato come stringa di cinque cifre e non è usato come
identificatore. I file storici originali restano invariati sotto
[`legacy/2023-05-02-original/`](legacy/2023-05-02-original/).

## Riproduzione

Scaricare il riferimento ISTAT indicato in
[`sources/README.md`](sources/README.md), quindi eseguire:

```bash
python3 scripts/normalize_legacy.py
python3 scripts/validate_milestone1.py
```

La validazione controlla schema, conteggi, identificativi, formati, coordinate,
corrispondenze ISTAT e invarianti di migrazione rispetto alla baseline.

## Documentazione

- [`DATA_SOURCES.md`](DATA_SOURCES.md): provenienza, date e licenze;
- [`SCHEMA.md`](SCHEMA.md): perimetro semantico, campi e identificativi;
- [`CONTRIBUTING.md`](CONTRIBUTING.md): regole per modifiche riproducibili;
- [`CHANGELOG.md`](CHANGELOG.md): modifiche alla working copy;
- [`MILESTONE1_REPORT.md`](MILESTONE1_REPORT.md): esito e questioni aperte.

## English summary

The canonical file contains Italian municipalities and postal localities. Only
exact current ISTAT name/province matches are classified as municipalities;
all other records remain explicitly unclassified. The original files are
preserved unchanged. This working copy is not release-ready until the legacy
source and data-licensing questions documented in `DATA_SOURCES.md` are
resolved.
