# Changelog

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
