# Clean-room dataset pipeline

## Flusso canonico

```text
ISTAT municipalities snapshot -----+
                                   +--> checksum gate
GeoNames IT.zip snapshot ----------+        |
                                            v
                                  exact conservative reconciliation
                                            |
                 +--------------------------+-----------------------+
                 v                          v                       v
       municipalities.csv           localities.csv          postal_codes.csv
                 +--------------------------+-----------------------+
                                            v
                                  italian_locations.csv
                                            |
                         +------------------+------------------+
                         v                  v                  v
                       JSON               XLSX              SQLite
                                            |
                                            v
                                    Pages / release bundle

legacy CSV --> historical comparison only --> reports/legacy-comparison.json
```

Il modello canonico è creato da `build_clean_room(istat_path, geonames_path)`.
La funzione non accetta un input legacy. Il digest canonico dipende soltanto
dagli identificativi ISTAT e GeoNames riconciliati.

## Acquisizione e checksum

`sources/manifest.json` registra URL, percorso, timestamp, checksum, licenza,
attribuzione, ruolo e versione del formato. `scripts/source_data.py` verifica
SHA-256 prima di aprire il workbook ISTAT o `IT.zip`.

Lo snapshot GeoNames è committato come file originale; non viene modificato o
estratto manualmente nel repository.

## Riconciliazione

`scripts/reconcile_sources.py` usa:

- nome Unicode normalizzato;
- sigla e nome provincia;
- regione/divisione amministrativa;
- CAP per identità e deduplicazione della relazione;
- codici amministrativi disponibili.

Un solo candidato coerente produce `exact_unambiguous`. Più candidati
producono `multiple_candidates`. Nessun candidato produce
`unmatched_no_parent`. Non esistono fuzzy matching o scelte automatiche fra
candidati.

Tutti i comuni ISTAT vengono creati prima della riconciliazione. Se non esiste
un CAP GeoNames, il comune riceve una relazione `missing`.

## Output e atomicità

Gli output CSV e JSON sono scritti su un file temporaneo e sostituiti con
`os.replace`. XLSX e SQLite vengono costruiti in file temporanei. L'ordine è
esplicito e indipendente dall'ordine accidentale delle fonti.

`scripts/export_formats.py` genera JSON, XLSX e SQLite soltanto dalla vista
canonica. `scripts/export_sql.py` crea lo script SQLite-compatible.
`scripts/build_release.py` prepara nove asset, incluso `SHA256SUMS`.

## Report

- `reports/build-metadata.json`: fonti, qualità, readiness e statistiche;
- `reports/legacy-comparison.json`: confronto storico limitato e deterministico;
- `reports/release-diff.json`: confronto logico con v1.1.0;
- `reports/export-manifest.json`: digest degli export;
- `reports/determinism.json`: firme di due build;
- `reports/quality-validation.json`: gate strutturali separati dalla readiness.

Il report legacy può cambiare se cambia il legacy; gli output canonici no.

## Quality model

Una build valida dichiara separatamente:

```text
structural_quality: passed
operational_data_readiness: experimental_non_official
```

Il primo valore significa che schema, integrità, checksum, determinismo e
formati sono coerenti. Il secondo impedisce di interpretare il risultato come
certificazione postale.

## Comandi

```bash
python -m pip install -r requirements.txt -r requirements-dev.txt
python scripts/build_dataset.py
python scripts/check_determinism.py
python scripts/validate_dataset.py
ruff check scripts tests
mypy
coverage run -m unittest discover -s tests
coverage report
node --test tests/pages_core.test.mjs
python scripts/build_pages.py
python scripts/build_release.py
python scripts/validate_release.py
git diff --check
```

La CI esegue questi gate su Python 3.11, 3.12 e 3.13. Le Actions sono fissate
a commit SHA immutabili.

## Aggiornamento fonti

1. acquisire un nuovo snapshot dalla stessa origine autorizzata;
2. conservarlo sotto un percorso datato;
3. aggiornare manifest, checksum, timestamp e riferimento;
4. modificare la trasformazione se il formato cambia;
5. rigenerare tutto;
6. esaminare report e statistiche;
7. aprire una PR e attendere tutti i gate.

CSV, JSON, XLSX, SQLite e SQL non devono mai essere corretti a mano.
