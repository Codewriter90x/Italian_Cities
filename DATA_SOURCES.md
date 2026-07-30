# Data sources

La dichiarazione machine-readable è [`sources/manifest.json`](sources/manifest.json).
La pipeline verifica il checksum prima di leggere ogni snapshot.

## Fonti canoniche v2

### ISTAT — comuni

- ruolo: elenco completo dei comuni, codici e gerarchia amministrativa;
- snapshot: `sources/snapshots/istat/Elenco-comuni-italiani-2026-02-21.xlsx`;
- riferimento: 2026-02-21;
- SHA-256:
  `83842076860450f7e482daecea6b7a769f5f93d0bf5b0d48802b44896d7a26d5`;
- origine:
  <https://www.istat.it/storage/codici-unita-amministrative/Elenco-comuni-italiani.xlsx>;
- licenza/attribuzione: ISTAT, CC BY 4.0.

### GeoNames — Postal Codes IT

- ruolo: relazioni luogo–CAP e coordinate WGS84 non ufficiali;
- snapshot: `sources/snapshots/geonames/IT-2026-07-30.zip`;
- URL esatto: <https://download.geonames.org/export/zip/IT.zip>;
- indice e README: <https://download.geonames.org/export/zip/>;
- acquisito: `2026-07-30T09:36:42Z`;
- `Last-Modified` dichiarato: `2026-07-30T01:44:40Z`;
- SHA-256:
  `08cf5625f70952ba9c0a126b0af20a048a0e4dad8f6ca60deda5b612d100e7bc`;
- formato: dodici campi TSV UTF-8 descritti nel `readme.txt` incluso;
- licenza: CC BY 4.0;
- attribuzione: “GeoNames — <https://www.geonames.org/>”.

GeoNames dichiara che molte coordinate sono trovate o stimate
algoritmicamente e fornisce i dati “as is”. Il campo `accuracy` originale è
preservato. GeoNames non è Poste Italiane e non è descritto come tale.

### ISTAT — confini regionali generalizzati

- ruolo: sola base cartografica riproducibile della GitHub Pages, non input del
  dataset canonico;
- data di riferimento: 1 gennaio 2026;
- archivio: `sources/cache/Limiti01012026_g.zip`;
- SHA-256:
  `b011a590656c3a3ebc297fba80726a376aa843b6f164641cf6a4a990021a81d6`;
- licenza/attribuzione: ISTAT, CC BY 4.0.

La CI ricostruisce il GeoJSON semplificato dal file originale e confronta i
byte con l'asset committato. Il controllo non può più risultare verde saltando
la ricostruzione.

## Materiale storico ritirato

Il materiale usato dalle versioni anteriori alla ricostruzione clean-room non
aveva una provenienza e un diritto di redistribuzione dimostrabili. È stato
quindi rimosso dal branch corrente, dagli asset delle release interessate e
dalla cronologia Git pubblica. Non è dichiarato nel manifest e non viene
usato per confronti o baseline.

## Fonti escluse

- Poste “Cerca CAP” e altre interfacce non autorizzate;
- scraping;
- API commerciali o con condizioni non accettate;
- servizio pubblico Nominatim per geocoding massivo;
- qualsiasi dato non dichiarato e non verificato nel manifest.

I confini regionali usati come base visiva della Pages sono un asset
separato, derivato dai confini generalizzati ISTAT 2026 e non contribuiscono a
CAP o coordinate del dataset.
