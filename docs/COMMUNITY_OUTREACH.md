# Community outreach kit

Data di preparazione: 2026-07-29

Questo documento prepara il lancio di Italian Cities senza pubblicare
automaticamente messaggi su community esterne. Prima dell'invio occorre
leggere regole, canali corretti e disclosure richieste dalla singola community.

## Link canonici

- Repository: <https://github.com/Codewriter90x/Italian_Cities>
- Ricerca web: <https://codewriter90x.github.io/Italian_Cities/>
- Release: <https://github.com/Codewriter90x/Italian_Cities/releases/tag/v1.0.0>
- Discussioni: <https://github.com/Codewriter90x/Italian_Cities/discussions>

## Messaggio generale

**Titolo**

> Italian Cities v1.0.0: dataset riproducibile di comuni, località, CAP e coordinate

**Testo**

> Ho pubblicato Italian Cities v1.0.0: 14.480 relazioni luogo–CAP, 7.186
> comuni riconosciuti tramite ISTAT, 4.459 CAP distinti e coordinate per
> l'85,55% dei record. CSV, JSON, XLSX, SQLite e SQL sono generati dalla
> stessa pipeline e verificati con checksum e test di integrità.
>
> La nuova ricerca web permette di filtrare per nome, CAP e provincia e mostra
> la copertura geografica. Il README dichiara anche i limiti: non è un elenco
> postale ufficiale e la provenienza upstream dei valori legacy non è
> interamente dimostrata.
>
> Cerco feedback su correzioni verificabili, fonti compatibili e casi d'uso:
> [ricerca web] · [repository] · [release].

Sostituire i riferimenti fra parentesi con i link canonici.

## Adattamento open data

Punti da evidenziare:

- manifest e checksum delle fonti;
- provenienza e licenze dichiarate, inclusi i limiti del legacy;
- build deterministica e diff machine-readable;
- moduli di correzione basati su evidenze.

Destinazioni da valutare:

- [Spaghetti Open Data](https://spaghettiopendata.org/), dopo lettura della
  netiquette e della mailing list;
- categoria [Dati e open data di Forum Italia](https://forum.italia.it/c/dati/33);
- [onData](https://www.ondata.it/), come possibile interlocutore per feedback
  metodologico e non come canale automatico.

Call to action:

> Mi interessa soprattutto un confronto su provenienza dei CAP legacy,
> riconciliazione delle località e fonti ufficiali riutilizzabili.

## Adattamento .NET

Esempio breve:

> Per chi lavora in .NET ho incluso un esempio C# senza dipendenze esterne e
> asset JSON, SQLite e SQL pronti all'uso. Mi farebbe comodo un feedback sul
> contratto dei dati e sui casi d'uso in applicazioni italiane.

Destinazione da valutare:

- [DotNetCode](https://dotnetcode.it/), verificando prima il canale previsto
  per segnalazioni di progetti community.

## Adattamento Python

Esempio breve:

> La pipeline è Python, riproducibile e coperta da test su schema, integrità,
> coordinate, determinismo e coerenza degli export. Cerco contributi sulle
> regole di normalizzazione e sulle fonti geografiche.

Destinazione da valutare:

- [community Python Italia](https://www.python.it/comunita/), scegliendo forum,
  mailing list o canale indicato e rispettando il codice di condotta.

## Adattamento GIS

Esempio breve:

> La Pages visualizza direttamente i 12.388 punti WGS84 senza geocoding
> massivo né tile provider. Restano 2.092 coordinate mancanti: vorrei
> confrontarmi su centroidi da confini ufficiali, estratti OSM e metodi
> riproducibili con licenza chiara.

Destinazioni da valutare:

- [GFOSS.it](https://gfoss.it/);
- [FOSS4G Italia](https://www.foss4g.it/), per eventuale presentazione o
  confronto con la comunità geo-open source.

## Checklist prima dell'invio

1. Verificare che Pages, release e download siano raggiungibili anonimamente.
2. Dichiarare che l'autore sta presentando il proprio progetto.
3. Non descrivere il dataset come ufficiale o completamente aggiornato.
4. Includere il caveat sulla provenienza legacy.
5. Personalizzare il messaggio per il canale ed evitare cross-post identici.
6. Rispondere ai commenti e riportare le correzioni nelle issue strutturate.
