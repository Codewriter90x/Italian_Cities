# Milestone 3 report

Data dell'esecuzione: 2026-07-29

Baseline Git: `8ceea7a60066ca0f7c03a207b12131edfd46ed10`

Schema dataset: `2.0.0`

Quality gate: `3.0.0`

## Obiettivo

Impedire che una pull request introduca regressioni di schema, identità,
validità, geografia, integrità o riproducibilità nei dataset generati.

## Controlli bloccanti

| Controllo | Evidenza automatica |
| --- | --- |
| Numero e nomi delle colonne | header confrontato con i quattro contratti dichiarati |
| Identificativi unici | ID e UUID verificati per tabella; relazione CAP con chiave composta |
| CAP a cinque cifre | espressione regolare `^[0-9]{5}$` su tutti i dataset |
| Codici ISTAT validi | sei cifre, presenza nello snapshot ISTAT dichiarato e ID coerente |
| Comune–provincia–regione | provincia confrontata con ISTAT, regione compatibile e mappatura interna univoca |
| Coordinate numeriche | coppie complete, conversione numerica e valori finiti |
| Limiti geografici | latitudine 35–48 e longitudine 6–19 |
| Righe vuote | controllo di righe fisiche vuote, delimitatori vuoti e record senza valori |
| Duplicati logici | nome normalizzato + CAP + provincia; chiave relazione per i CAP |
| Integrità fra tabelle | comuni e località devono ricostruire il canonico; CAP senza orfani |
| Build deterministica | due build consecutive con hash binari uguali e digest SQLite uguale |

Il report machine-readable è `reports/milestone3-validation.json`. La prova
della doppia build è `reports/milestone3-determinism.json`.

## Merge gate

`.github/workflows/data-pipeline.yml` esegue il job denominato
`Data quality gate` su ogni pull request. Qualunque violazione termina il job
con codice diverso da zero.

Il branch `main` richiede questo status check tramite branch protection; una
pull request non può quindi essere unita se il controllo manca, è in corso o
fallisce.

## Coordinate mancanti

Il progetto non usa il Nominatim pubblico per il bulk geocoding. Le ragioni e
le alternative approvate sono documentate in `COORDINATE_ENRICHMENT.md`.

Le opzioni preferite sono confini amministrativi ISTAT, elaborazione locale di
estratti OpenStreetMap, un'istanza propria o un provider che autorizzi il
carico e la redistribuzione.

## Verifiche eseguite

- 26 test automatici superati, inclusi casi negativi che dimostrano il rifiuto
  di CAP, identificativi, duplicati e coordinate non validi;
- 11 categorie del quality gate superate con zero violazioni;
- 7.894 codici comunali caricati dal riferimento ISTAT e 7.186 comuni del
  dataset verificati;
- equivalenza record per record confermata per CSV, JSON, XLSX e SQLite;
- due build consecutive con output byte-identici e SQLite semanticamente
  identico;
- digest canonico invariato:
  `3875b5080718139ba353ba229f4913faf926f5eb9968ed569642c4cedfab00dc`;
- zero modifiche ai file dati rispetto alla Milestone 2.
