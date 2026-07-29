# Data sources and licensing

## Stato della provenienza

La provenienza completa del dataset legacy non è ricostruibile dai materiali
presenti nel repository.

La baseline è il contenuto del branch `main` al commit
`09986a059cdf9ff8920a944faf6fa8e2f9cb88ac`. I metadati disponibili indicano:

- export SQL Server: `2023-05-01 11:54:55`;
- creazione del workbook Excel: `2023-05-02T06:33:52Z`;
- ultima modifica del workbook Excel: `2023-05-02T06:51:41Z`.

Queste date descrivono gli artefatti, non la data di aggiornamento dei dati
sottostanti. La data di riferimento della raccolta originaria rimane ignota.
Nella storia Git non risultano import script, URL sorgente o dichiarazioni di
attribuzione anteriori.

## Inventario delle fonti

La dichiarazione machine-readable consumata dalla pipeline è
`sources/manifest.json`. Il build verifica il checksum di ogni input prima di
generare dati.

| Fonte | Ruolo | Data di riferimento | Licenza | Stato |
| --- | --- | --- | --- | --- |
| File legacy del repository | Baseline e contenuto originario | artefatti del 1-2 maggio 2023; dati sottostanti ignoti | `LICENSE` dichiara CC0 1.0, ma la titolarità sui dati importati non è provata | preservata, non considerata fonte certa |
| Elenco dei comuni italiani ISTAT | Classificazione conservativa e codici stabili dei comuni | 2026-02-21 | CC BY 4.0 secondo le note legali/open data ISTAT | usata nella trasformazione |
| GeoNames postal codes, Italia | Confronto investigativo di provenienza, non incorporato nel canonico | snapshot storico 2022-12-28 e controllo 2026-07-29 | CC BY 4.0 | somiglianza parziale, fonte diretta non dimostrata |
| OpenStreetMap/Nominatim | Ipotesi investigativa per alcune coordinate, non incorporata né interrogata dalla trasformazione | ignota | ODbL 1.0 e obblighi di attribuzione applicabili | origine non dimostrata; rischio da chiarire |

Riferimenti:

- ISTAT, [Codici delle unità amministrative](https://www.istat.it/classificazione/codici-dei-comuni-delle-province-e-delle-regioni/);
- ISTAT, [Note legali](https://www.istat.it/note-legali/) e
  [Open data](https://www.istat.it/dati/open-data/);
- GeoNames, [Postal codes](https://download.geonames.org/export/zip/) e
  [licenza](https://www.geonames.org/export/);
- OpenStreetMap Foundation,
  [geocoding guideline](https://osmfoundation.org/wiki/Licence/Community_Guidelines/Geocoding_-_Guideline),
  [attribution guideline](https://osmfoundation.org/wiki/Licence/Attribution_Guidelines)
  e [Nominatim usage policy](https://operations.osmfoundation.org/policies/nominatim/).

## Risultati dell'indagine

Un confronto normalizzato tra nome e CAP ha trovato 10.882 corrispondenze
esatte su 14.480 record (75,15%) sia nello snapshot GeoNames del 28 dicembre
2022 sia in quello controllato il 29 luglio 2026. Non sono state trovate
corrispondenze esatte sistematiche delle coppie di coordinate. Questo rende
GeoNames un riferimento plausibile o sovrapposto, ma non prova che sia la
fonte del dataset.

Alcune coordinate pubblicamente reperibili coincidono con risultati
geocodificati basati su OpenStreetMap. Anche questo è un indizio, non una
catena di provenienza. La Milestone 1 non aggiunge dati da GeoNames,
OpenStreetMap o Nominatim.

Per l'unica correzione numerica, la coppia legacy di Brovello Carpugnino
conteneva una longitudine fuori da qualsiasi intervallo geografico:
`539621684096616`. Una
[verifica pubblica puntuale](https://www.coordinatesfinder.com/coordinates/1174714-brovello-carpugnino)
riporta la stessa latitudine legacy e la longitudine
`8.53962168409662`; il
[sito ufficiale del Comune](https://comune.brovellocarpugnino.vb.it/Ilcomuneinbreve)
conferma inoltre che la longitudine comunale è nell'ordine degli 8 gradi est.
La trasformazione si limita quindi a ripristinare `8.` e marca il record come
`corrected`; non presenta quel punto come confine o centroide ufficiale.

L'elenco ISTAT del 21 febbraio 2026 contiene 7.894 comuni. La trasformazione
riconosce soltanto le 7.186 righe legacy che corrispondono esattamente per nome
normalizzato e sigla di provincia. I restanti 7.294 record non vengono
classificati per inferenza.

## Compatibilità delle licenze e gate di pubblicazione

CC0 può rinunciare soltanto ai diritti posseduti da chi effettua la rinuncia.
La presenza del testo CC0 nel repository non dimostra che eventuali dati
provenienti da terzi fossero rilicenziabili in questo modo.

I codici e la classificazione ISTAT aggiunti al canonico richiedono
attribuzione CC BY 4.0. Se l'origine delle coordinate fosse OpenStreetMap,
andrebbero inoltre valutati e rispettati gli obblighi ODbL relativi a
attribuzione, database derivati e condivisione alle stesse condizioni.

Di conseguenza:

1. la working copy canonica è **provvisoria e non pronta per la release**;
2. non deve essere presentata come interamente CC0;
3. prima della pubblicazione occorre scegliere una delle seguenti strade:
   documentare la fonte e i diritti originari; sostituire i campi senza
   provenienza con fonti compatibili e attribuite; oppure pubblicare insiemi
   separati con licenze e attribuzioni corrette;
4. la decisione finale sulla licenza deve essere verificata dal maintainer e,
   se il dataset è destinato a uso rilevante, da una persona competente in
   materia legale.

## Riproducibilità del riferimento ISTAT

Il file richiesto è descritto in `sources/README.md`. La copia locale è esclusa
da Git; la trasformazione ne verifica indirettamente l'identità attraverso il
checksum registrato nei report:

```text
83842076860450f7e482daecea6b7a769f5f93d0bf5b0d48802b44896d7a26d5
```

Data della trasformazione Milestone 1: 2026-07-29.

## Milestone 2

La Milestone 2 non incorpora nuove fonti geografiche e non modifica
semanticamente i 14.480 record. Importa le fonti già dichiarate, verifica che
riproducano la baseline M1 e costruisce nuovi schemi ed export.

Data build: 2026-07-29. Schema: `2.0.0`.
