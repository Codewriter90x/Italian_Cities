# Contributing

## Principi

Ogni modifica ai dati deve essere verificabile, attribuibile e riproducibile.
Non modificare manualmente alcun CSV, JSON, XLSX, SQLite o SQL generato.
`data/` è interamente prodotto dalla pipeline.

I file sotto `legacy/2023-05-02-original/` sono una baseline immutabile. Non
correggerli, rinominarli o rigenerarli.

## Correzioni e nuove fonti

Una proposta che modifica un valore deve includere:

1. record interessato e campo;
2. valore precedente e valore proposto;
3. URL o artefatto sorgente, editore, data di riferimento e data di accesso;
4. licenza e attribuzione richiesta;
5. regola riproducibile implementata nello script;
6. eventuali conseguenze sugli identificativi.

Non inferire una frazione, un comune padre o una coordinata dalla sola
somiglianza del nome. Non usare il CAP come chiave univoca. Conservare i CAP
come stringhe di cinque cifre.

Le coordinate devono essere una coppia WGS84 completa e provenire da una
fonte autorizzata. Non eseguire geocoding massivo contro il servizio pubblico
Nominatim; rispettare sempre termini, limiti e attribuzione della fonte scelta.

## Workflow locale

1. Dichiarare o aggiornare la fonte in `sources/manifest.json`.
2. Scaricare il riferimento descritto in `sources/README.md`.
3. Modificare la trasformazione o lo schema, non gli output generati.
4. Rigenerare e validare:

   ```bash
   python3 scripts/build_dataset.py
   python3 scripts/check_determinism.py
   python3 scripts/validate_dataset.py
   python3 -m unittest discover -s tests -v
   python3 scripts/build_release.py
   python3 scripts/validate_release.py
   ```

5. Esaminare `reports/release-diff.json`: cambi aggiunti, rimossi o
   modificati devono essere intenzionali e spiegati.
6. Verificare le baseline:

   ```bash
   cd legacy/2023-05-02-original
   shasum -a 256 -c SHA256SUMS
   ```

7. Controllare che `reports/determinism.json` e
   `reports/quality-validation.json` abbiano `"status": "passed"` e che
   ogni voce `quality_checks` sia superata.

I warning non vanno nascosti: descrivono debito dati o gate di pubblicazione
ancora aperti.

La pull request deve superare il check richiesto `Data quality gate`. Il check
viene eseguito su ogni PR e il branch `main` non accetta merge quando manca o
fallisce.

Per una correzione dati aprire il modulo GitHub più specifico:

- `Località errata`;
- `CAP errato`;
- `Coordinata mancante`;
- `Variazione amministrativa`.

Il modulo generico `Data correction` resta disponibile per casi che non
rientrano nelle categorie precedenti. Domande, proposte e casi d'uso vanno
invece nelle GitHub Discussions.

## Regole sugli identificativi

- Non cambiare `legacy_uuid`.
- Non assegnare manualmente un codice ISTAT.
- Una riconciliazione deve essere basata su una fonte e deve conservare alias
  se cambia un `location_id`.
- Nuovi tipi di record richiedono prima un aggiornamento a `SCHEMA.md` e ai
  controlli automatici.

## Export

`scripts/export_formats.py` genera JSON, XLSX e SQLite esclusivamente da
`data/italian_locations.csv`. Non correggere un formato derivato: correggere
fonte o trasformazione e rigenerare tutti gli export.

`scripts/export_sql.py` genera lo script SQL SQLite-compatible.
`scripts/build_release.py` copia esclusivamente gli artefatti generati, crea lo
script SQL e scrive `SHA256SUMS`. Il dump SQL Server sotto `legacy/` non entra
mai nel bundle.

## Release

Il tag deve corrispondere a `dataset_version` in `project.json`. Il workflow
`.github/workflows/release.yml`:

1. valida dataset e test sul commit taggato;
2. costruisce e valida `dist/<versione>/`;
3. conserva il bundle come artifact CI;
4. crea una GitHub Release senza sovrascrivere asset già pubblicati;
5. usa `release_status` per creare una pre-release finché il gate dati/licenze
   resta aperto.

La promozione da pre-release a release stabile è un gate maintainer separato.
Richiede il controllo di note, checksum, asset e stato di provenienza/licenze.

## GitHub Pages

`scripts/build_pages.py` costruisce il sito statico esclusivamente dal CSV
canonico. La build deve essere deterministica e non deve introdurre:

- geocoding lato client o server;
- analytics o cookie;
- dipendenze da tile provider;
- copie divergenti del dataset;
- HTML generato manualmente contenente dati.

Prima di modificare ricerca o mappa eseguire:

```bash
node --test tests/pages_core.test.mjs
python3 -m unittest discover -s tests -p 'test_pages.py' -v
python3 scripts/build_pages.py
```

## Licenze

Non incorporare dati finché la loro licenza non è documentata e compatibile
con il modo in cui il dataset sarà distribuito. L'attribuzione ISTAT e il gate
descritto in `DATA_SOURCES.md` devono accompagnare ogni futura release.
