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

5. Esaminare `reports/milestone2-diff.json`: cambi aggiunti, rimossi o
   modificati devono essere intenzionali e spiegati.
6. Verificare le baseline:

   ```bash
   cd legacy/2023-05-02-original
   shasum -a 256 -c SHA256SUMS
   ```

7. Controllare che `reports/milestone3-determinism.json` e
   `reports/milestone3-validation.json` abbiano `"status": "passed"` e che
   ogni voce `quality_checks` sia superata.

I warning non vanno nascosti: descrivono debito dati o gate di pubblicazione
ancora aperti.

La pull request deve superare il check richiesto `Data quality gate`. Il check
viene eseguito su ogni PR e il branch `main` non accetta merge quando manca o
fallisce.

Per una correzione dati è preferibile aprire il modulo GitHub
`Data correction`, indicando identificativo, campo, valore precedente e
proposto, fonte, data e licenza.

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

Il tag deve corrispondere alla versione supportata dal packaging. Il workflow
`.github/workflows/release.yml`:

1. valida dataset e test sul commit taggato;
2. costruisce e valida `dist/<versione>/`;
3. conserva il bundle come artifact CI;
4. crea o aggiorna una GitHub Release **draft**.

La pubblicazione della draft è un gate maintainer separato. Richiede il
controllo di note, checksum, asset e stato di provenienza/licenze.

## Licenze

Non incorporare dati finché la loro licenza non è documentata e compatibile
con il modo in cui il dataset sarà distribuito. L'attribuzione ISTAT e il gate
descritto in `DATA_SOURCES.md` devono accompagnare ogni futura release.
