# Milestone 2 report

Data dell'esecuzione: 2026-07-29

Baseline Git: `86d0165b47ee3fa33df333b421880a33a84fbb61`

Schema: `2.0.0`

## Risultati

| Requisito | Esito | Evidenza |
| --- | --- | --- |
| Nessuna modifica manuale agli artefatti | completato | output generati atomicamente da script |
| Fonti dichiarate e importate | completato | `sources/manifest.json` con checksum obbligatori |
| Normalizzazione | completato | `normalized_name`, nome di visualizzazione preservato |
| CAP con zeri iniziali | completato | stringa a cinque cifre in ogni formato |
| Ordine deterministico | completato | chiavi di sort esplicite e test |
| Quattro tabelle CSV | completato | comuni, località, CAP e vista unificata |
| CSV, JSON, XLSX e SQLite | completato | export dalla stessa vista canonica |
| Report differenze | completato | `reports/milestone2-diff.json` |
| Prevenzione divergenze | completato | confronto record per record dei quattro formati |
| Test richiesti | completato | schema, integrità e coordinate |

## Conteggi

- 14.480 località canoniche;
- 7.186 comuni;
- 7.294 località postali non classificate;
- 14.480 relazioni luogo-CAP;
- 12.387 coordinate preservate;
- 1 coordinata corretta già nella baseline M1;
- 2.092 coppie di coordinate mancanti;
- 0 record aggiunti, rimossi o modificati semanticamente rispetto a M1.

## Gate ancora aperti

- provenienza originaria e licenza del legacy non dimostrate;
- attribuzione ISTAT necessaria per una release;
- 7.294 località ancora non riconciliate con un comune padre;
- 2.092 coordinate ancora mancanti.

Questi elementi sono debito dati dichiarato e non vengono risolti tramite
inferenze o geocoding non autorizzato.

## Verifiche eseguite

- doppia rigenerazione completa con hash identici per tutti gli output;
- 16 test automatici superati;
- validazione schema 2.0.0 con zero errori;
- equivalenza record per record confermata per CSV, JSON, XLSX e SQLite;
- checksum delle fonti dichiarate e delle baseline verificati;
- baseline canonica M1 e tre artefatti originali invariati;
- workbook ispezionato e renderizzato: due fogli leggibili, formule senza
  errori, CAP preservati come testo e coordinate come numeri;
- report differenze: 14.480 record invariati, zero aggiunti, rimossi o
  modificati semanticamente;
- GitHub Action predisposta per rifiutare output obsoleti o modificati
  manualmente.

## Checksum finali

| Artefatto | SHA-256 |
| --- | --- |
| `data/municipalities.csv` | `815cef2ee41d5a6e734b7512667155188934866e72c45023f74baec43b29a662` |
| `data/localities.csv` | `67a6bad9fbfcb87cf7654c96ced75394734317113e98e52bafd2c2e9e42d066c` |
| `data/postal_codes.csv` | `058507df59c003f8043ef7f463b8b6b9abcb806fcd21d7b972b61bdd24f3b28a` |
| `data/italian_locations.csv` | `7f166a1247067d07e67b628e797241d101481de742be5bf826b0b46aa97ae619` |
| `data/italian_locations.json` | `0b33ac6f8f7e82c6a545ea2eb0c2a03f73562e092d5d0f3979fbed09a9cd4504` |
| `data/italian_locations.xlsx` | `b8bacc51ea7c34ce684fe0e2e16d513696edf2d99f470387cccb658491e2bcbb` |
| `data/italian_locations.sqlite` | `eccfc182374714eb18be775cccd9861fdb12863e460ab462b6a6d7e74d94648d` |
