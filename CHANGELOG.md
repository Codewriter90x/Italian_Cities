# Changelog

## Unreleased — Milestone 2 working copy

### Added

- Pipeline Python riproducibile orchestrata da `scripts/build_dataset.py`.
- Tabelle separate per comuni, località, relazioni CAP e vista unificata.
- Export equivalenti in JSON, XLSX e SQLite.
- Manifest machine-readable delle fonti con checksum obbligatori.
- Snapshot ISTAT versionato con attribuzione CC BY 4.0.
- Chiave `normalized_name` per confronti senza differenze di accento,
  apostrofo, punteggiatura o maiuscole.
- Report strutturato delle differenze rispetto alla baseline Milestone 1.
- Validazione incrociata dei formati e 16 test automatici di schema, integrità
  e coordinate.
- GitHub Action che rigenera e rifiuta artefatti divergenti.

### Changed

- `record_type` è rinominato `location_kind` nella vista schema 2.0.0.
- Aggiunto `parent_municipality_id`, volutamente vuoto finché una fonte non
  documenta la relazione.
- Il canonico M1 è preservato sotto `legacy/milestone-1-canonical/`.
- CSV, JSON, XLSX e SQLite sono ora artefatti generati, non file da modificare.
- Rimossi dalla radice i tre export legacy duplicati; le copie byte-per-byte
  restano preservate e verificabili sotto `legacy/2023-05-02-original/`.

### Data comparison

- 14.480 record invariati semanticamente rispetto alla Milestone 1.
- 0 aggiunti, 0 rimossi, 0 modificati.

## Unreleased — Milestone 1 working copy

### Added

- Baseline immutabile dei tre artefatti originali con inventario e checksum.
- Dataset canonico CSV con intestazione esplicita e schema documentato.
- Corrispondenza conservativa con l'elenco ISTAT del 21 febbraio 2026.
- Identificativi deterministici basati su codice ISTAT o UUIDv5.
- Script ripetibili di normalizzazione e validazione.
- Documentazione di provenienza, licenze, contribuzione e questioni aperte.

### Changed

- Valori di coordinate mancanti rappresentati da campi vuoti anziché `NULL`.
- Aggiunti `country_code`, `record_type`, `municipality_istat_code`,
  `coordinate_status` e `source_snapshot`.
- Rimosso dal canonico il campo costante `visible`; resta nei file legacy.

### Fixed

- Rimossa una riga completamente `NULL` senza identità o contenuto.
- Corretta la longitudine di `Brovello Carpugnino`, UUID legacy
  `a8aec4c6-ab9e-49ae-becf-fd111125f56a`, da `539621684096616` a
  `8.539621684096616`, ripristinando il prefisso decimale mancante.
- Registrato che `NA` è una sigla valida di Napoli e non un dato mancante;
  nessuna sigla di provincia è stata modificata.

### Known limitations

- 2.092 record restano senza coordinate.
- 7.294 record restano località postali non classificate.
- Provenienza originaria e licenza del legacy non sono dimostrate; nessuna
  release deve essere effettuata finché il gate non è chiuso.
