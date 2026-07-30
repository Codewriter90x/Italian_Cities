# Milestone 4 report

Data dell'esecuzione: 2026-07-29

Baseline Git: `295127fdced9cafd0510db4a40265865bd4fff45`

Release candidate: `v1.0.0`

Schema dataset: `2.0.0`

## Risultato

La Milestone 4 trasforma il repository in una distribuzione documentata e
riproducibile:

- README orientato all'utente e ai download;
- esempi C#, Python, JavaScript e SQL;
- bundle con formati equivalenti e checksum;
- script SQL generato dal canonico;
- validazione dell'import SQL;
- modulo strutturato per le correzioni;
- workflow di release basato su tag.

## Asset

```text
v1.0.0/
├── municipalities.csv
├── localities.csv
├── postal_codes.csv
├── italian_locations.csv
├── italian_locations.json
├── italian_locations.xlsx
├── italian_locations.sqlite
├── italian_locations.sql
└── SHA256SUMS
```

Il dump SQL Server non era incluso nel bundle. Il successivo audit sui diritti
ha portato al ritiro completo del materiale pre-clean-room e degli asset
derivati.

## Gate di pubblicazione

Il bundle e il tag possono essere preparati automaticamente. La GitHub Release
viene creata come draft perché il repository continua a dichiarare non
dimostrata la provenienza upstream completa dei valori legacy.

La pubblicazione della draft richiede una conferma maintainer consapevole
dell'avviso in `DATA_SOURCES.md` e nelle release notes.

## Verifiche locali

- 30 test automatici superati;
- quality gate dataset superato con zero errori;
- doppia build del dataset superata;
- nove asset esatti nel bundle;
- `SHA256SUMS` verificato per tutti gli otto asset dati/formato;
- script SQL importato sia dal validatore Python sia dalla CLI `sqlite3`;
- 14.480 righe SQL e digest canonico
  `3875b5080718139ba353ba229f4913faf926f5eb9968ed569642c4cedfab00dc`;
- nessuna modifica ai file sotto `data/`.

## Checksum release candidate

| Asset | SHA-256 |
| --- | --- |
| `municipalities.csv` | `815cef2ee41d5a6e734b7512667155188934866e72c45023f74baec43b29a662` |
| `localities.csv` | `67a6bad9fbfcb87cf7654c96ced75394734317113e98e52bafd2c2e9e42d066c` |
| `postal_codes.csv` | `058507df59c003f8043ef7f463b8b6b9abcb806fcd21d7b972b61bdd24f3b28a` |
| `italian_locations.csv` | `7f166a1247067d07e67b628e797241d101481de742be5bf826b0b46aa97ae619` |
| `italian_locations.json` | `0b33ac6f8f7e82c6a545ea2eb0c2a03f73562e092d5d0f3979fbed09a9cd4504` |
| `italian_locations.xlsx` | `b8bacc51ea7c34ce684fe0e2e16d513696edf2d99f470387cccb658491e2bcbb` |
| `italian_locations.sqlite` | `eccfc182374714eb18be775cccd9861fdb12863e460ab462b6a6d7e74d94648d` |
| `italian_locations.sql` | `f7c55075324f3029e5aaee387a01ee32d485cbcc4afd9fc2edf62018f12bb29e` |
