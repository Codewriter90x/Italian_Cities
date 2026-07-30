# Changelog

## v2.0.0 — clean-room prerelease

### Breaking

- Replaced the legacy-derived canonical dataset with a clean-room build from
  ISTAT municipalities and GeoNames Postal Codes IT.
- Raised the dataset schema to `3.0.0` and the quality gate to `5.0.0`.
- Changed the canonical grain to one row per location–postal-code relation.
- Removed `legacy_uuid`, `legacy_province_name`, `coordinate_status` and
  `source_snapshot` from the current schema.

### Added

- All 7,894 municipalities from the declared ISTAT snapshot, including 396
  without a GeoNames postal-code match.
- Many-to-many postal relations, explicit reconciliation outcomes, source
  record identities, source dates, confidence and GeoNames `accuracy`.
- Immutable GeoNames snapshot, checksum gate and attribution.
- Separate `structural_quality=passed` and
  `operational_data_readiness=experimental_non_official`.
- Clean-room warnings and GeoNames attribution in JSON, XLSX, SQLite, Pages
  and release notes.

### Changed

- Pre-clean-room material with unresolved redistribution rights was withdrawn
  from the current tree, public history and affected release assets.
- Coordinates are labelled `geonames_place_match`,
  `geonames_estimated` or `missing`; none are official.
- Pages uses absolute counts rather than a potentially misleading coverage
  percentage.

### Known limitations

- GeoNames is not Poste Italiane; CAP and coordinates are non-official and
  provided without warranty.
- 10,320 GeoNames records are not reconciled with a municipality.
- GeoNames still contains 76 records using historical province code `SU`;
  they remain unparented instead of being remapped automatically.
- Release assets remain experimental and non-official.

## v1.1.0 — pre-release

> Withdrawn on 30 July 2026: downloadable data assets were removed because
> provenance and redistribution rights could not be established.

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

> Withdrawn on 30 July 2026 for the same provenance and rights reason.

- Prima distribuzione riproducibile con CSV, JSON, XLSX, SQLite, SQL e
  checksum.
- Pipeline, quality gate, GitHub Pages, issue form e documentazione iniziali.
- La release è conservata per compatibilità e confronto, ma non deve essere
  interpretata come fonte postale ufficiale né come dataset dai diritti
  upstream completamente accertati.
