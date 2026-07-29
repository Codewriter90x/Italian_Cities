# Milestone 5 report

Data dell'esecuzione: 2026-07-29

Baseline Git: `1f8e7f600ac11dbea08d6402bbe420e1d9d844b5`

Release dati: `v1.0.0`

Schema dataset: `2.0.0`

## Risultato atteso

La Milestone 5 rende il progetto più facile da trovare, esplorare e
correggere:

- topic GitHub mirati;
- Discussions abilitate;
- social preview 1280×640;
- quattro moduli di segnalazione specifici;
- GitHub Pages con ricerca, mappa e statistiche;
- kit di lancio per community italiane open data, .NET, Python e GIS.

## GitHub Pages

La Pages è costruita da `scripts/build_pages.py` e non contiene una copia
modificabile a mano dei dati. Ogni deploy:

1. legge `data/italian_locations.csv`;
2. conserva soltanto i campi necessari alla consultazione;
3. calcola le statistiche dal dataset;
4. scrive un JSON deterministico e un manifest con checksum;
5. esegue test Python e JavaScript;
6. pubblica l'artifact tramite GitHub Actions.

La mappa usa direttamente le coordinate del dataset. Non invia richieste a
Nominatim, provider di geocoding o tile server.

## Copertura mostrata

- 14.480 relazioni luogo–CAP;
- 7.186 comuni riconosciuti;
- 7.294 località non classificate;
- 4.459 CAP distinti;
- 12.388 record con coordinate;
- 2.092 record senza coordinate;
- 85,55% di copertura coordinate.

## Community

Le correzioni sono instradate in moduli distinti per:

- denominazione o classificazione della località;
- CAP;
- coordinate mancanti;
- variazioni amministrative.

Domande, idee e casi d'uso vengono indirizzati alle Discussions. I testi per
community esterne sono preparati in `docs/COMMUNITY_OUTREACH.md`; la
pubblicazione richiede una scelta esplicita del canale e il rispetto delle
relative regole.

## Invarianti

- nessuna modifica ai 14.480 record;
- nessun cambio allo schema `2.0.0`;
- nessun geocoding massivo;
- nessun analytics o cookie;
- nessuna dipendenza da una mappa esterna;
- release `v1.0.0` invariata.
