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
        +-- baseline canonica Milestone 1
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
7. `reports/milestone2-diff.json` confronta i record tramite `legacy_uuid`
   contro la baseline M1 e separa cambi schema da cambi semantici.
8. Il validatore carica ogni formato e confronta campo per campo gli stessi
   14.480 record.
9. La GitHub Action ricostruisce gli output e fallisce se il diff Git rileva
   un file generato obsoleto o modificato manualmente.

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
python3 scripts/validate_dataset.py
python3 -m unittest discover -s tests -v
```

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
