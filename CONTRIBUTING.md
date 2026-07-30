# Contributing

## Regola fondamentale

Non modificare manualmente file sotto `data/`, SQL di release o report
generati. Ogni correzione parte da una fonte dichiarata o da una regola
riproducibile.

Non modificare o eliminare `legacy/`, i tag storici o le baseline di release.

## Correzione dati

Una proposta deve indicare:

1. record e campo interessati;
2. valore corrente e proposto;
3. editore, URL, data di riferimento e data di accesso;
4. licenza e attribuzione;
5. regola riproducibile;
6. conseguenze su ID, riconciliazione e report.

Non usare scraping, Poste “Cerca CAP”, API non autorizzate o il servizio
pubblico Nominatim per bulk geocoding. Non acquistare una fonte per conto del
progetto e non accettare condizioni commerciali senza decisione del
maintainer.

## Regole di riconciliazione

- il codice ISTAT identifica il comune;
- un CAP non identifica un comune;
- il nome simile non basta;
- più candidati restano ambigui;
- una località senza match resta senza comune padre;
- `official_verified` e `official_boundary_derived` non possono essere usati
  senza una nuova fonte ufficiale compatibile e documentata;
- il campo GeoNames `accuracy` va preservato;
- GeoNames non deve essere presentato come Poste Italiane.

## Workflow locale

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

Verificare che:

- `structural_quality` sia `passed`;
- `operational_data_readiness` resti `experimental_non_official`;
- due build siano identiche;
- nessun `source_ids` canonico contenga `legacy_csv`;
- il report legacy sia limitato, deterministico e non affermi provenienza;
- la Pages mostri warning e attribuzione GeoNames.

## Pull request

La PR deve descrivere fonti/licenze, schema, statistiche prima/dopo, rischi
residui e comandi eseguiti. Tutti i check richiesti devono essere verdi prima
del merge.

Per segnalazioni usare gli issue form per località, CAP, coordinate o
variazioni amministrative. Discussioni e casi d'uso possono essere aperti in
GitHub Discussions.

## Release

Il tag deve coincidere con `project.json`. Preparare `release/<versione>.md`,
costruire e validare `dist/<versione>/`, ma non creare tag o release senza
conferma esplicita del maintainer.
