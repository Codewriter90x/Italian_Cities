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
```

Il modello canonico è creato da `build_clean_room(istat_path, geonames_path)`.
Il digest canonico dipende soltanto dagli identificativi ISTAT e GeoNames
riconciliati. Il materiale storico a provenienza irrisolta è stato ritirato e
non è presente tra input, baseline o report.

## Acquisizione e checksum

`sources/manifest.json` registra URL, percorso, timestamp, checksum, licenza,
attribuzione, ruolo e versione del formato. `scripts/source_data.py` verifica
SHA-256 prima di aprire il workbook ISTAT o `IT.zip`.

Lo snapshot GeoNames è committato come file originale; non viene modificato o
estratto manualmente nel repository.

L'archivio dei confini regionali generalizzati ISTAT è dichiarato come fonte
ausiliaria non canonica. È committato con checksum e la CI ricostruisce
obbligatoriamente `site/assets/italy-regions.geojson`; un cache assente o
dipendenze geografiche mancanti fanno fallire il gate.

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
- `reports/release-diff.json`: confronto logico con la baseline clean-room
  `v2.0.0`;
- `reports/reconciliation-backlog.json`: segmenti da revisionare per regione,
  provincia e codice territoriale sorgente;
- `reports/export-manifest.json`: digest degli export;
- `reports/determinism.json`: firme di due build;
- `reports/quality-validation.json`: gate strutturali separati dalla readiness.

Quest'ultimo include anche la distribuzione dei riusi esatti di coordinate,
alla grana del luogo univoco. I cluster grandi sono marcati
`review_required`: non rendono strutturalmente invalido il dump sorgente, ma
impediscono di descrivere `geonames_place_match` come verifica geografica.

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
python -m pip install \
  -r requirements.txt \
  -r requirements-dev.txt \
  -r requirements-geography.txt
python scripts/build_dataset.py
python scripts/check_determinism.py
python scripts/validate_dataset.py
ruff check scripts tests
mypy
coverage run -m unittest discover -s tests
coverage report
python scripts/validate_typed_contract.py
python scripts/build_geography.py --check --require-rebuild
python scripts/check_workflow_pins.py
node --test tests/pages_core.test.mjs
python scripts/build_pages.py
python scripts/build_release.py
python scripts/validate_release.py
git diff --check
```

La CI esegue questi gate su Python 3.11, 3.12, 3.13 e 3.14. Le Actions sono
fissate a commit SHA immutabili e un test impedisce regressioni a tag o branch.
`pip-audit` controlla le dipendenze dichiarate.

## Aggiornamento fonti

Controllare senza modificare il repository:

```bash
python scripts/update_sources.py --check
```

Per preparare esplicitamente un nuovo snapshot in un percorso datato:

```bash
python scripts/update_sources.py \
  --download geonames_postal_codes \
  --output sources/cache/IT-new.zip
```

Lo script rifiuta di sovrascrivere file esistenti e non modifica il manifest.
Il workflow settimanale `Source freshness` apre una sola issue quando rileva
un checksum upstream differente; non esegue commit né rigenera il dataset.

1. acquisire o preparare un nuovo snapshot dalla stessa origine autorizzata;
2. conservarlo sotto un percorso datato;
3. aggiornare manifest, checksum, timestamp e riferimento;
4. modificare la trasformazione se il formato cambia;
5. rigenerare tutto;
6. esaminare report e statistiche;
7. aprire una PR e attendere tutti i gate.

CSV, JSON, XLSX, SQLite e SQL non devono mai essere corretti a mano.
