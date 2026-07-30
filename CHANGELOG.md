# Changelog

## v1.1.0 — pre-release

### Added

- `project.json` come unica fonte per versione dataset, schema, quality gate,
  stato release e baseline precedente.
- Campi `postal_code_status`, `coordinate_verification`,
  `legacy_province_name` e `source_ids`.
- Baseline immutabile e verificata di `v1.0.0` per il diff fra release.
- Avvisi visibili su GitHub Pages e nei risultati di ricerca.
- Documenti separati per licenza del codice, attribuzioni e stato dei diritti
  sui dati.

### Changed

- Nomi delle province normalizzati sullo snapshot ISTAT; il valore originario
  è preservato in `legacy_province_name`.
- I CAP legacy non sono più implicitamente presentati come verificati. I nove
  codici generici noti delle città multi-CAP sono marcati
  `generic_multicap`.
- Le coordinate presenti sono esplicitamente `legacy_unverified` o
  `corrected_legacy_unverified`; nessuna coordinata è dichiarata verificata.
- Report, packaging e workflow usano nomi stabili, metadati centralizzati e
  controlli anti-sovrascrittura.
- Schema dataset `2.1.0`; quality gate `4.0.0`.

### Fixed

- Rimossa la dipendenza circolare che trattava un output canonico come fonte
  della stessa build.
- Eliminata l'affermazione implicita che il dataset legacy fosse interamente
  coperto da CC0.
- Il conteggio dei risultati della Pages distingue il totale dai primi 60
  elementi mostrati.

### Known limitations

- Provenienza e diritti del dataset legacy non sono completamente dimostrati.
- Nessun CAP è verificato contro una fonte postale autorizzata.
- Nessuna coordinata legacy è verificata contro una fonte geografica
  autorevole.
- La release deve rimanere una pre-release finché questi gate non vengono
  risolti.

## v1.0.0 — baseline storica

- Prima distribuzione riproducibile con CSV, JSON, XLSX, SQLite, SQL e
  checksum.
- Pipeline, quality gate, GitHub Pages, issue form e documentazione iniziali.
- La release è conservata per compatibilità e confronto, ma non deve essere
  interpretata come fonte postale ufficiale né come dataset dai diritti
  upstream completamente accertati.
