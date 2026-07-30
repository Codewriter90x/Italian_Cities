# Dataset pipeline

## Obiettivo

La pipeline rende ogni artefatto dati una conseguenza riproducibile di fonti,
schema e trasformazioni versionate. CSV, JSON, XLSX e SQLite non sono fonti:
non devono essere modificati manualmente.

## Flusso

```text
sources/manifest.json
        |
        +-- legacy CSV immutabile
        +-- riferimento comuni ISTAT
        |
        v
scripts/build_dataset.py
        |
        +-- normalizzazione e partizionamento
        +-- report differenze
        |
        +--> data/municipalities.csv
        +--> data/localities.csv
        +--> data/postal_codes.csv
        +--> data/italian_locations.csv
                          |
                          v
              scripts/export_formats.py
                          |
                          +--> JSON
                          +--> XLSX
                          +--> SQLite
                          |
                          v
              scripts/validate_dataset.py
                          |
                          v
              scripts/check_determinism.py
                    (due build)
                          |
                          v
               scripts/build_release.py
                          |
                          +--> CSV / JSON / XLSX
                          +--> SQLite / SQL
                          +--> SHA256SUMS
                          |
                          v
              scripts/validate_release.py

project.json
        |
        +-- versione dataset e schema
        +-- stato della release
        +-- baseline della release precedente
```

## Contratti

1. Tutte le fonti richieste sono dichiarate in `sources/manifest.json` con
   percorso, ruolo, data, licenza e SHA-256.
2. Il build termina con errore se un checksum non coincide.
3. `name` conserva la rappresentazione legacy; `normalized_name` è una chiave
   di ricerca deterministica, senza differenze di accento, apostrofo,
   punteggiatura o maiuscole/minuscole.
4. `postal_code` è sempre testo conforme a `^[0-9]{5}$`.
5. Le righe sono ordinate per chiavi esplicite e mai per ordine accidentale
   della fonte o del database.
6. Gli output vengono scritti prima su file temporanei e poi sostituiti.
7. `reports/release-diff.json` confronta i record tramite `legacy_uuid`
   contro la baseline della release precedente dichiarata in `project.json`
   e separa cambi di schema da cambi semantici.
8. Il validatore carica ogni formato e confronta campo per campo tutti i
   record.
9. La GitHub Action esegue il job bloccante `Data quality gate` su ogni pull
   request e fallisce per violazioni di schema, identità, CAP, ISTAT,
   gerarchia territoriale, coordinate, righe vuote, duplicati o integrità.
10. SQLite viene confrontato semanticamente: il layout binario delle pagine
    può cambiare tra versioni della libreria, mentre schema, metadati e record
    devono essere identici. Gli artefatti committati vengono validati prima
    della rigenerazione, quindi una modifica manuale non viene nascosta.
11. `scripts/check_determinism.py` esegue due build consecutive e richiede
    hash byte-per-byte identici per CSV, JSON, XLSX e report; per SQLite
    confronta il digest ordinato dei record.
12. Il bundle release copia gli output canonici, genera uno script SQL
    SQLite-compatible e registra il checksum binario di ogni asset.
13. Il validatore release importa il SQL in un database temporaneo, verifica
    schema, righe e digest e rifiuta file mancanti, aggiuntivi o alterati.

## Comandi

Build completo:

```bash
python3 scripts/build_dataset.py
```

Solo tabelle CSV e report differenze:

```bash
python3 scripts/build_dataset.py --no-exports
```

Rigenerazione dei soli formati derivati:

```bash
python3 scripts/export_formats.py
```

Validazione e test:

```bash
python3 scripts/check_determinism.py
python3 scripts/validate_dataset.py
python3 -m unittest discover -s tests -v
python3 scripts/build_release.py
python3 scripts/validate_release.py
```

I risultati machine-readable sono:

- `reports/release-diff.json`;
- `reports/export-manifest.json`;
- `reports/determinism.json`;
- `reports/quality-validation.json`.

## XLSX

La pipeline è interamente orchestrata in Python. `export_formats.py` usa
`XlsxWriter`, dichiarato in `requirements.txt`, esclusivamente per creare il
workbook.

Nel workbook:

- il CAP è testo;
- latitudine e longitudine sono celle numeriche;
- intestazione, filtri e righe bloccate rendono il dataset esplorabile;
- il foglio `Dataset Info` contiene conteggi, checksum e riferimenti;
- metadati ZIP e timestamp sono normalizzati per consentire build
  deterministiche.

## Modificare i dati

Una modifica valida parte da una fonte dichiarata o da una regola nello script.
Il contributore aggiorna manifest e trasformazione, rigenera tutto, esamina il
diff report e infine esegue validatore e test. Una modifica diretta a un file
generato è incompleta e deve essere rigenerata.

## Release

`dist/<versione>/` è temporaneo e non versionato. La versione deve coincidere
con `dataset_version` in `project.json`. Il bundle contiene:

- `municipalities.csv`;
- `localities.csv`;
- `postal_codes.csv`;
- `italian_locations.csv`;
- `italian_locations.json`;
- `italian_locations.xlsx`;
- `italian_locations.sqlite`;
- `italian_locations.sql`;
- `SHA256SUMS`.

Il dump SQL Server preservato sotto `legacy/` non viene letto dal packaging
come formato distribuibile. Rimane soltanto una delle baseline storiche da cui
la pipeline ricostruisce e verifica il canonico.

Il workflow rifiuta un tag diverso dalla versione dichiarata e non sovrascrive
una release già esistente. Quando `release_status` è `prerelease`, la release
GitHub viene creata come pre-release: non è una promozione a dataset stabile.
