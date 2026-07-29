# Coordinate enrichment policy

## Regola operativa

Le coordinate mancanti non devono essere ottenute interrogando in massa
`nominatim.openstreetmap.org`.

La [Nominatim Usage Policy](https://operations.osmfoundation.org/policies/nominatim/)
stabilisce che:

- il servizio pubblico ha capacità limitata e non è destinato a carichi
  pesanti;
- il bulk geocoding di grandi quantità di dati è scoraggiato;
- le interrogazioni sistematiche per ottenere elenchi completi di CAP,
  località o punti di interesse sono vietate;
- per esigenze regolari o ampie occorre usare estratti OpenStreetMap, un
  provider appropriato oppure una propria istanza.

Questa pipeline non contiene né deve introdurre un client verso il Nominatim
pubblico.

## Strategia raccomandata

### 1. Comuni riconosciuti

Usare i
[confini amministrativi ISTAT](https://www.istat.it/notizia/confini-delle-unita-amministrative-a-fini-statistici-al-1-gennaio-2018-2/)
della stessa epoca dello snapshot anagrafico.

Il join deve avvenire tramite il codice ISTAT di sei cifre. Per i comuni senza
coordinate si può calcolare un punto rappresentativo interno al poligono
(`point_on_surface`), evitando di assumere che un centroide cada sempre
all'interno di territori multipoligonali.

Per ogni coordinata derivata vanno registrati almeno:

- codice ISTAT;
- snapshot e checksum del confine;
- metodo di calcolo;
- sistema di riferimento;
- licenza e attribuzione;
- data della trasformazione.

### 2. Località postali non classificate

Prima di geocodificare occorre riconciliare la località con un comune padre.
Le alternative accettabili sono:

- elaborazione locale di un
  [estratto OpenStreetMap per l'Italia](https://download.geofabrik.de/europe/italy.html);
- un'istanza Nominatim gestita dal progetto;
- un provider che autorizzi esplicitamente il bulk geocoding e la
  redistribuzione dei risultati.

Qualunque processo deve essere riproducibile, cache-first e separare i match
certi da quelli ambigui. Un match basato soltanto sul nome non è sufficiente:
vanno considerati almeno CAP, provincia, comune padre e tipo dell'oggetto.

### 3. Gate prima dell'import

Una nuova fonte di coordinate può entrare nel dataset soltanto se:

1. è dichiarata in `sources/manifest.json` con snapshot e checksum;
2. la licenza è compatibile e l'attribuzione è documentata;
3. la trasformazione è automatizzata e deterministica;
4. le coordinate sono numeriche, finite e dentro limiti plausibili;
5. per i comuni, il punto è coerente con il confine ufficiale;
6. i match ambigui restano fuori dal canonico e vengono riportati per revisione.
