# Italian Cities

Dataset riproducibile di nomi geografici italiani associati a CAP, con comuni
riconosciuti tramite ISTAT, località postali non classificate e coordinate
quando disponibili.

> **Release:** `v1.0.0` · **Schema:** `2.0.0` · **Build:** 29 luglio 2026
> Gli artefatti sono generati: non modificare manualmente CSV, JSON, XLSX,
> SQLite o SQL.

| Copertura | Record | Note |
| --- | ---: | --- |
| Comuni riconosciuti | 7.186 | codice ISTAT verificato |
| Località non classificate | 7.294 | comune padre non disponibile |
| Relazioni luogo–CAP | 14.480 | 4.459 CAP distinti |
| Coordinate disponibili | 12.388 | 85,55% dei record |
| Coordinate mancanti | 2.092 | campi vuoti, non valori inventati |

## Cosa contiene

- associazioni fra denominazione geografica, CAP e provincia;
- 7.186 comuni riconosciuti conservativamente nello snapshot ISTAT;
- 7.294 località postali non ancora riconciliate con un comune padre;
- CAP conservati come stringhe di cinque cifre;
- coordinate WGS84 legacy, quando presenti;
- identificativi stabili, chiavi normalizzate e provenienza dello snapshot;
- gli stessi 14.480 record in CSV, JSON, XLSX, SQLite e SQL.

## Cosa non contiene

- un elenco postale ufficiale o garantito aggiornato da Poste Italiane;
- tutte e sole le unità amministrative italiane correnti;
- una classificazione affidabile di tutte le frazioni;
- la relazione comune padre per le località non classificate;
- coordinate ufficiali per ogni record o confini geografici;
- una provenienza originaria dimostrata per tutti i campi legacy.

Non usare il CAP come identificatore univoco. Non assumere che una località sia
un comune o una frazione senza verificare `location_kind`.

## Data di riferimento

Il dataset combina riferimenti con date differenti:

| Componente | Data |
| --- | --- |
| Artefatti legacy preservati | 1–2 maggio 2023 |
| Data sottostante dei valori legacy | sconosciuta |
| Elenco comuni e codici ISTAT | 21 febbraio 2026 |
| Build e prima release | 29 luglio 2026 |

La data ISTAT non rende automaticamente aggiornati CAP e coordinate legacy.

## Download v1.0.0

| Formato | Download |
| --- | --- |
| Comuni CSV | [municipalities.csv](https://github.com/Codewriter90x/Italian_Cities/releases/download/v1.0.0/municipalities.csv) |
| Località CSV | [localities.csv](https://github.com/Codewriter90x/Italian_Cities/releases/download/v1.0.0/localities.csv) |
| Relazioni CAP CSV | [postal_codes.csv](https://github.com/Codewriter90x/Italian_Cities/releases/download/v1.0.0/postal_codes.csv) |
| Vista canonica CSV | [italian_locations.csv](https://github.com/Codewriter90x/Italian_Cities/releases/download/v1.0.0/italian_locations.csv) |
| JSON | [italian_locations.json](https://github.com/Codewriter90x/Italian_Cities/releases/download/v1.0.0/italian_locations.json) |
| Excel | [italian_locations.xlsx](https://github.com/Codewriter90x/Italian_Cities/releases/download/v1.0.0/italian_locations.xlsx) |
| SQLite | [italian_locations.sqlite](https://github.com/Codewriter90x/Italian_Cities/releases/download/v1.0.0/italian_locations.sqlite) |
| Script SQL | [italian_locations.sql](https://github.com/Codewriter90x/Italian_Cities/releases/download/v1.0.0/italian_locations.sql) |
| Checksum | [SHA256SUMS](https://github.com/Codewriter90x/Italian_Cities/releases/download/v1.0.0/SHA256SUMS) |

Verifica tutti gli asset scaricati:

```bash
shasum -a 256 -c SHA256SUMS
```

`italian_locations.sql` è generato dal CSV canonico ed è compatibile con
SQLite. Il vecchio dump SQL Server resta soltanto come artefatto storico sotto
`legacy/2023-05-02-original/`: non è una fonte primaria né un asset di release.

## Dataset

| File | Grana | Righe |
| --- | --- | ---: |
| `municipalities.csv` | comune riconosciuto presente nel legacy | 7.186 |
| `localities.csv` | località postale non classificata | 7.294 |
| `postal_codes.csv` | relazione luogo–CAP | 14.480 |
| `italian_locations.csv` | vista canonica unificata | 14.480 |

JSON, XLSX, SQLite e SQL derivano esclusivamente dalla vista canonica. Il
quality gate confronta formati e tabelle e blocca le pull request incoerenti.

## Schema della vista canonica

| Colonna | Tipo | Significato |
| --- | --- | --- |
| `location_id` | testo | ID canonico deterministico |
| `legacy_uuid` | UUID | ID originario preservato |
| `name` | testo | denominazione di visualizzazione legacy |
| `normalized_name` | testo | chiave senza differenze di accento e maiuscole |
| `location_kind` | enum | `municipality` o `postal_locality_unclassified` |
| `municipality_istat_code` | testo, 6 cifre | valorizzato soltanto per i comuni |
| `parent_municipality_id` | testo opzionale | oggi vuoto finché non documentato |
| `postal_code` | testo, 5 cifre | CAP con zeri iniziali preservati |
| `province_code` | testo, 2 lettere | sigla provincia |
| `province_name` | testo | denominazione provincia legacy |
| `region_name` | testo | denominazione regione legacy |
| `country_code` | testo | sempre `IT` |
| `country_name` | testo | denominazione paese legacy |
| `latitude` | decimale opzionale | WGS84, presente con la longitudine |
| `longitude` | decimale opzionale | WGS84, presente con la latitudine |
| `coordinate_status` | enum | `available`, `corrected` o `missing` |
| `source_snapshot` | testo | snapshot da cui deriva il record |

Gli schemi completi delle quattro tabelle sono descritti in
[`SCHEMA.md`](SCHEMA.md).

## Esempi

### C#

Scarica e legge il JSON con le sole API .NET:

```csharp
using System.Net.Http;
using System.Text.Json;

const string url =
    "https://github.com/Codewriter90x/Italian_Cities/releases/download/" +
    "v1.0.0/italian_locations.json";

using var http = new HttpClient();
await using var stream = await http.GetStreamAsync(url);
using var document = await JsonDocument.ParseAsync(stream);

foreach (var row in document.RootElement.GetProperty("rows").EnumerateArray())
{
    Console.WriteLine(
        $"{row.GetProperty("name").GetString()} " +
        $"({row.GetProperty("postal_code").GetString()})");
}
```

### Python

```python
import csv
from urllib.request import urlopen
from io import TextIOWrapper

url = (
    "https://github.com/Codewriter90x/Italian_Cities/releases/download/"
    "v1.0.0/municipalities.csv"
)

with urlopen(url) as response:
    rows = csv.DictReader(TextIOWrapper(response, encoding="utf-8"))
    for municipality in rows:
        if municipality["region_name"] == "Lazio":
            print(municipality["name"], municipality["postal_code"])
```

### JavaScript

Compatibile con browser moderni e Node.js 18 o successivo:

```javascript
const url =
  "https://github.com/Codewriter90x/Italian_Cities/releases/download/" +
  "v1.0.0/italian_locations.json";

const response = await fetch(url);
if (!response.ok) throw new Error(`Download failed: ${response.status}`);

const dataset = await response.json();
const municipalities = dataset.rows.filter(
  (row) => row.location_kind === "municipality"
);
console.log(municipalities.length);
```

### SQL

Usa direttamente il database SQLite:

```bash
sqlite3 italian_locations.sqlite
```

```sql
SELECT name, postal_code, province_code
FROM italian_locations
WHERE normalized_name LIKE 'san giovanni%'
ORDER BY name, postal_code;
```

Oppure ricrea lo stesso database dallo script:

```bash
sqlite3 italian_locations-from-sql.sqlite < italian_locations.sql
```

## Fonti e licenze

| Fonte | Utilizzo | Licenza/stato |
| --- | --- | --- |
| Export legacy del repository | nomi, CAP, province e coordinate originari | CC0 dichiarata nel repository; provenienza upstream non dimostrata |
| ISTAT, elenco comuni 2026-02-21 | classificazione, codici comunali e controlli territoriali | CC BY 4.0, attribuzione richiesta |
| GeoNames e OpenStreetMap | solo indagine storica | non incorporati dalla pipeline v1.0.0 |

La licenza CC0 può operare soltanto sui diritti posseduti da chi la applica.
Non va quindi interpretata come prova della rilicenziabilità di ogni valore
legacy. Prima di una redistribuzione rilevante leggere
[`DATA_SOURCES.md`](DATA_SOURCES.md) e le note ISTAT in
[`sources/snapshots/istat/README.md`](sources/snapshots/istat/README.md).

## Politica di aggiornamento

Il progetto usa aggiornamenti basati sulle fonti, senza una cadenza garantita:

1. ogni nuova fonte viene salvata come snapshot immutabile con checksum;
2. la trasformazione viene modificata nello script, mai negli output;
3. ogni build produce un diff machine-readable rispetto alla versione
   precedente;
4. il quality gate verifica schema, identità, CAP, ISTAT, coordinate,
   integrità, formati e determinismo;
5. una nuova release viene pubblicata soltanto dopo il superamento dei check.

Versionamento:

- patch: correzioni compatibili senza cambio schema;
- minor: nuovi campi o tabelle compatibili;
- major: cambi incompatibili di schema, identità o significato.

## Segnalare una correzione

Apri il modulo
[`Data correction`](https://github.com/Codewriter90x/Italian_Cities/issues/new?template=data_correction.yml)
indicando:

1. `location_id` o `legacy_uuid`;
2. campo interessato;
3. valore attuale e valore proposto;
4. fonte verificabile e data di riferimento;
5. licenza, attribuzione ed eventuali ambiguità.

Le correzioni vengono implementate nella pipeline e rigenerate; non si
accettano modifiche manuali ai file sotto `data/`.

## Riprodurre la release

Prerequisiti: Python 3.11 o successivo e le dipendenze dichiarate.

```bash
python3 -m pip install -r requirements.txt
python3 scripts/build_dataset.py
python3 scripts/check_determinism.py
python3 scripts/validate_dataset.py
python3 -m unittest discover -s tests -v
python3 scripts/build_release.py
python3 scripts/validate_release.py
```

La pipeline e i gate sono descritti in
[`DATASET_PIPELINE.md`](DATASET_PIPELINE.md).

## English summary

Italian Cities v1.0.0 provides 14,480 generated Italian location/postal-code
records as CSV, JSON, XLSX, SQLite and SQL. It is not an official or
fully-current postal directory. Read the source and licensing caveats before
redistribution, preserve postal codes as five-character strings, and never
edit generated assets manually.
