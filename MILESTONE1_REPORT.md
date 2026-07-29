# Milestone 1 report

Data dell'esecuzione: 2026-07-29

Baseline Git: `09986a059cdf9ff8920a944faf6fa8e2f9cb88ac`

Stato: completata come working copy locale; pubblicazione bloccata.

## Risultati

| Requisito | Esito | Evidenza |
| --- | --- | --- |
| Inventario e preservazione legacy | completato | tre file byte-per-byte, checksum in `legacy/2023-05-02-original/SHA256SUMS` |
| Perimetro semantico | completato | definizioni e classificazione prudenziale in `SCHEMA.md` |
| Provenienza, date e licenze | documentato con limite esplicito | `DATA_SOURCES.md`; origine completa non ricostruibile |
| Schema canonico | completato | `SCHEMA.md` e intestazione del CSV |
| Correzione anomalie accertate | completato | una riga nulla rimossa, una longitudine corretta, coordinate mancanti esplicite |
| Sigle provincia | verificato | nessuna sigla vuota; `NA` confermata come valore valido |
| Identificativi stabili | completato | codici ISTAT o UUIDv5 deterministico; UUID legacy conservati |
| Documentazione richiesta | completato | `DATA_SOURCES.md`, `SCHEMA.md`, `CHANGELOG.md`, `CONTRIBUTING.md` |
| Controlli ripetibili | completato | `scripts/normalize_legacy.py` e `scripts/validate_milestone1.py` |

## Esito quantitativo

- 14.480 righe canoniche, tutte riconducibili a un UUID legacy;
- 7.186 comuni riconosciuti mediante match esatto ISTAT;
- 7.294 località postali non classificate;
- 12.387 coppie di coordinate preservate senza modifica;
- 1 coppia con longitudine corretta e marcata `corrected`;
- 2.092 coppie mancanti, rappresentate esplicitamente;
- 1 riga completamente nulla rimossa;
- 0 errori nel report di validazione.

SHA-256 del canonico:

```text
735a7e9a1e7fb4eab005022478772ceab73d0034120f4f243ca68d4c64668a3d
```

## Verifiche eseguite

- normalizzazione eseguita due volte con lo stesso checksum del canonico;
- validazione finale `passed`, con zero errori;
- checksum dei tre file legacy verificati con `shasum -a 256 -c`;
- confronto byte-per-byte tra file originali alla radice e copie legacy;
- compilazione sintattica di entrambi gli script Python;
- verifica di 14.481 righe fisiche nel CSV canonico: intestazione più 14.480
  record;
- verifica di assenza di `NULL` letterali, ID duplicati, CAP non conformi,
  sigle di provincia mancanti, coordinate parziali o modifiche non
  documentate.

## Questioni irrisolte

1. La fonte originaria di nomi, CAP e coordinate non è provata.
2. Non è provato che la licenza CC0 alla radice copra legittimamente tutti i
   dati legacy; il canonico include inoltre classificazioni ISTAT CC BY 4.0.
3. Un'eventuale origine OpenStreetMap delle coordinate richiede indagine e
   potrebbe introdurre obblighi ODbL.
4. Le 7.294 località non classificate richiedono una fonte autorevole per
   distinguere frazioni, località, denominazioni storiche e comuni non
   riconciliati.
5. Le 2.092 coordinate mancanti non sono state inventate o ottenute tramite
   geocoding non autorizzato.
6. I cambi amministrativi successivi al legacy possono impedire match esatti;
   non è stato applicato fuzzy matching.

## Gate

La Milestone 1 tecnica è riproducibile, ma la pubblicazione resta bloccata
finché non viene presa e documentata una decisione sulla provenienza e sulla
licenza. In questa attività non sono stati eseguiti commit, push, release o
altre modifiche su GitHub.
