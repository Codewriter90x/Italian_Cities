# Community outreach kit

Aggiornato: 2026-07-30

Questo documento prepara il lancio di Italian Cities senza pubblicare
automaticamente messaggi su community esterne. Prima dell'invio occorre
leggere regole, canali corretti e disclosure richieste dalla singola community.

> **Gate:** non promuovere il dataset come banca dati postale ufficiale.
> GeoNames non è Poste Italiane e la v2 resta una prerelease sperimentale.

## Link canonici

- Repository: <https://github.com/Codewriter90x/Italian_Cities>
- Ricerca web: <https://codewriter90x.github.io/Italian_Cities/>
- Working dataset: <https://github.com/Codewriter90x/Italian_Cities/tree/main/data>
- Discussioni: <https://github.com/Codewriter90x/Italian_Cities/discussions>

## Messaggio generale

**Titolo**

> Italian Cities v2.0.0 clean-room prerelease: revisione aperta

**Testo**

> Sto revisionando Italian Cities v2.0.0 prerelease: 7.894 comuni dallo
> snapshot ISTAT e 18.811 relazioni costruite dal dump GeoNames Postal Codes
> IT. CSV, JSON, XLSX, SQLite e SQL sono generati dalla stessa pipeline e
> verificati con checksum e test di integrità.
>
> La nuova ricerca web permette di filtrare per nome, CAP e provincia e mostra
> la copertura geografica. Il README dichiara anche i limiti: non è un elenco
> postale ufficiale; GeoNames non è Poste Italiane e CAP e coordinate non sono
> dichiarati ufficialmente verificati. Il legacy è escluso dal canonico.
>
> Cerco soprattutto revisione su fonti compatibili, licenze e correzioni
> verificabili: [ricerca web] · [repository] · [working dataset].

Sostituire i riferimenti fra parentesi con i link canonici.

## Adattamento open data

Punti da evidenziare:

- manifest e checksum delle fonti;
- provenienza e licenze dichiarate per ISTAT e GeoNames;
- build deterministica e diff machine-readable;
- moduli di correzione basati su evidenze.

Destinazioni da valutare:

- [Spaghetti Open Data](https://spaghettiopendata.org/), dopo lettura della
  netiquette e della mailing list;
- categoria [Dati e open data di Forum Italia](https://forum.italia.it/c/dati/33);
- [onData](https://www.ondata.it/), come possibile interlocutore per feedback
  metodologico e non come canale automatico.

Call to action:

> Mi interessa soprattutto un confronto sulla riconciliazione conservativa
> delle località e su fonti postali ufficiali riutilizzabili.

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

> La Pages visualizza direttamente coordinate GeoNames senza geocoding
> runtime né tile provider. Restano 396 comuni senza coordinate: vorrei
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
4. Dichiarare che il legacy non contribuisce più al canonico.
5. Dichiarare che GeoNames non è Poste Italiane e che CAP e coordinate non
   sono ufficialmente verificati.
6. Personalizzare il messaggio per il canale ed evitare cross-post identici.
7. Rispondere ai commenti e riportare le correzioni nelle issue strutturate.
