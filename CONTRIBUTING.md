# Contributing

## Principi

Ogni modifica ai dati deve essere verificabile, attribuibile e riproducibile.
Non modificare manualmente `data/italian_postal_localities.csv`: è un artefatto
generato.

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

1. Scaricare il riferimento descritto in `sources/README.md`.
2. Modificare la trasformazione, non il CSV generato.
3. Rigenerare e validare:

   ```bash
   python3 scripts/normalize_legacy.py
   python3 scripts/validate_milestone1.py
   ```

4. Verificare la baseline:

   ```bash
   cd legacy/2023-05-02-original
   shasum -a 256 -c SHA256SUMS
   ```

5. Controllare che `reports/milestone1-validation.json` abbia
   `"status": "passed"` e un array `errors` vuoto.

I warning non vanno nascosti: descrivono debito dati o gate di pubblicazione
ancora aperti.

## Regole sugli identificativi

- Non cambiare `legacy_uuid`.
- Non assegnare manualmente un codice ISTAT.
- Una riconciliazione deve essere basata su una fonte e deve conservare alias
  se cambia un `location_id`.
- Nuovi tipi di record richiedono prima un aggiornamento a `SCHEMA.md` e ai
  controlli automatici.

## Licenze

Non incorporare dati finché la loro licenza non è documentata e compatibile
con il modo in cui il dataset sarà distribuito. L'attribuzione ISTAT e il gate
descritto in `DATA_SOURCES.md` devono accompagnare ogni futura release.
