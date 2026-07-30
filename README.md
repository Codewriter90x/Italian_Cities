# Italian Cities

Dataset sperimentale e riproducibile di nomi geografici italiani associati a
CAP legacy, comuni riconosciuti tramite ISTAT e coordinate quando presenti.

**[Apri la ricerca web](https://codewriter90x.github.io/Italian_Cities/)** ·
[Fonti e licenze](DATA_SOURCES.md) ·
[Segnala una correzione](https://github.com/Codewriter90x/Italian_Cities/issues/new/choose) ·
[Discussions](https://github.com/Codewriter90x/Italian_Cities/discussions)

> [!CAUTION]
> Questo non è un elenco postale ufficiale. I CAP e le coordinate legacy non
> sono verificati per l'uso operativo. I CAP generici delle città multi-CAP non
> sono validi per indirizzare una spedizione. La provenienza e i diritti
> upstream di parte del legacy restano irrisolti.

**Working dataset:** `v1.1.0` prerelease · **Schema:** `2.1.0` ·
**Build:** 30 luglio 2026.

La release pubblicata `v1.0.0` è una baseline storica e non va interpretata
come certificazione di accuratezza o licenza. Gli output sotto `data/` sono
generati: non modificarli manualmente.

## Copertura

| Contenuto | Record | Affidabilità |
| --- | ---: | --- |
| Comuni riconosciuti | 7.186 | codice ISTAT verificato; non è l'elenco completo dei 7.894 comuni dello snapshot |
| Località non classificate | 7.294 | comune padre non disponibile |
| Relazioni luogo–CAP | 14.480 | tutti i CAP sono legacy non verificati |
| CAP generici città multi-CAP | 9 | esplicitamente marcati `generic_multicap` |
| Coordinate presenti | 12.388 | legacy non verificate |
| Coordinate verificate | 0 | nessun punto è ancora certificato da una fonte geografica dichiarata |
| Coordinate mancanti | 2.092 | campi vuoti |

La percentuale di coordinate presenti misura soltanto la completezza dei campi,
non la correttezza geografica.

## Cosa contiene

- associazioni legacy fra denominazione, CAP e provincia;
- riconciliazione conservativa con lo snapshot ISTAT del 21 febbraio 2026;
- CAP conservati come stringhe di cinque cifre;
- stato esplicito di affidabilità dei CAP e delle coordinate;
- denominazione provinciale ufficiale e valore legacy originale;
- identificativi deterministici e riferimenti alle fonti usate;
- output equivalenti in CSV, JSON, XLSX, SQLite e SQL.

## Cosa non contiene

- una banca dati CAP ufficiale o garantita aggiornata da Poste Italiane;
- CAP specifici per via e numero civico nelle città multi-CAP;
- tutti i comuni italiani correnti;
- una classificazione affidabile di tutte le frazioni;
- relazioni comune padre per le località non classificate;
- coordinate ufficiali o verificate;
- una catena di provenienza completa per i valori legacy.

Non usare il CAP come identificatore univoco. Non assumere che una località sia
un comune o una frazione senza verificare `location_kind`.

## Date di riferimento

| Componente | Data |
| --- | --- |
| Artefatti legacy preservati | 1–2 maggio 2023 |
| Data sottostante dei valori legacy | sconosciuta |
| Elenco comuni e codici ISTAT | 21 febbraio 2026 |
| Build corrente | 30 luglio 2026 |

La data ISTAT non rende automaticamente aggiornati CAP e coordinate legacy.

## Download

Gli output correnti sono disponibili dal branch `main`:

| Formato | Download |
| --- | --- |
| Comuni CSV | [municipalities.csv](https://raw.githubusercontent.com/Codewriter90x/Italian_Cities/main/data/municipalities.csv) |
| Località CSV | [localities.csv](https://raw.githubusercontent.com/Codewriter90x/Italian_Cities/main/data/localities.csv) |
| Relazioni CAP CSV | [postal_codes.csv](https://raw.githubusercontent.com/Codewriter90x/Italian_Cities/main/data/postal_codes.csv) |
| Vista canonica CSV | [italian_locations.csv](https://raw.githubusercontent.com/Codewriter90x/Italian_Cities/main/data/italian_locations.csv) |
| JSON | [italian_locations.json](https://raw.githubusercontent.com/Codewriter90x/Italian_Cities/main/data/italian_locations.json) |
| Excel | [italian_locations.xlsx](https://raw.githubusercontent.com/Codewriter90x/Italian_Cities/main/data/italian_locations.xlsx) |
| SQLite | [italian_locations.sqlite](https://raw.githubusercontent.com/Codewriter90x/Italian_Cities/main/data/italian_locations.sqlite) |

La baseline pubblicata resta disponibile nella
[release v1.0.0](https://github.com/Codewriter90x/Italian_Cities/releases/tag/v1.0.0),
ma è superata dalla working copy e mantiene i limiti documentati.

## Dataset

| File | Grana |
| --- | --- |
| `municipalities.csv` | comune riconosciuto presente nel legacy |
| `localities.csv` | località postale non classificata |
| `postal_codes.csv` | relazione luogo–CAP con stato di verifica |
| `italian_locations.csv` | vista canonica unificata |

JSON, XLSX, SQLite e SQL derivano esclusivamente dalla vista canonica.

## Schema canonico

| Colonna | Significato |
| --- | --- |
| `location_id` | ID canonico deterministico |
| `legacy_uuid` | ID originario preservato |
| `name` / `normalized_name` | denominazione legacy e chiave normalizzata |
| `location_kind` | `municipality` o `postal_locality_unclassified` |
| `municipality_istat_code` | codice ISTAT, soltanto per i comuni riconosciuti |
| `parent_municipality_id` | relazione futura, oggi vuota |
| `postal_code` | CAP legacy di cinque cifre |
| `postal_code_status` | `legacy_unverified`, `generic_multicap`, `verified` o `obsolete` |
| `province_code` | sigla provincia |
| `province_name` | denominazione ufficiale dallo snapshot ISTAT |
| `legacy_province_name` | denominazione originaria preservata |
| `region_name` | denominazione regione |
| `latitude` / `longitude` | coppia WGS84 opzionale |
| `coordinate_status` | presenza tecnica: `available`, `corrected` o `missing` |
| `coordinate_verification` | affidabilità e provenienza della coordinata |
| `source_snapshot` | baseline storica del record |
| `source_ids` | fonti dichiarate che contribuiscono al record |

Lo schema completo è in [`SCHEMA.md`](SCHEMA.md).

## Esempi

### C#

```csharp
using System.Net.Http;
using System.Text.Json;

const string url =
    "https://raw.githubusercontent.com/Codewriter90x/Italian_Cities/" +
    "main/data/italian_locations.json";

using var http = new HttpClient();
await using var stream = await http.GetStreamAsync(url);
using var document = await JsonDocument.ParseAsync(stream);

foreach (var row in document.RootElement.GetProperty("rows").EnumerateArray())
{
    if (row.GetProperty("postal_code_status").GetString() == "verified")
        Console.WriteLine(row.GetProperty("name").GetString());
}
```

### Python

```python
import csv
from io import TextIOWrapper
from urllib.request import urlopen

url = (
    "https://raw.githubusercontent.com/Codewriter90x/Italian_Cities/"
    "main/data/municipalities.csv"
)

with urlopen(url) as response:
    rows = csv.DictReader(TextIOWrapper(response, encoding="utf-8"))
    for municipality in rows:
        if municipality["province_code"] == "RM":
            print(municipality["name"], municipality["postal_code_status"])
```

### JavaScript

```javascript
const url =
  "https://raw.githubusercontent.com/Codewriter90x/Italian_Cities/" +
  "main/data/italian_locations.json";
const response = await fetch(url);
const dataset = await response.json();

const genericMultiCap = dataset.rows.filter(
  (row) => row.postal_code_status === "generic_multicap",
);
console.log(genericMultiCap);
```

### SQL

```sql
SELECT name, postal_code, postal_code_status
FROM italian_locations
WHERE normalized_name = 'roma';
```

## Fonti e licenze

| Fonte | Utilizzo | Stato |
| --- | --- | --- |
| Export legacy del repository | nomi, CAP, province e coordinate | provenienza e diritti upstream non dimostrati |
| ISTAT 2026-02-21 | classificazione, codici e denominazioni territoriali | CC BY 4.0, attribuzione richiesta |

Il testo CC0 si applica soltanto al codice e alla documentazione originale per
i quali il proprietario del repository possiede i diritti. Non rende CC0 i
dati di terze parti. Leggere:

- [`DATA_LICENSE.md`](DATA_LICENSE.md);
- [`NOTICE.md`](NOTICE.md);
- [`DATA_SOURCES.md`](DATA_SOURCES.md).

## Aggiornamenti e differenze

La configurazione centrale è `project.json`. Ogni build:

1. verifica checksum e licenze dichiarate delle fonti;
2. costruisce tutti i formati dallo stesso canonico;
3. confronta il risultato con la release precedente versionata sotto
   `baselines/releases/`;
4. scrive `reports/release-diff.json`;
5. valida schema, CAP, ISTAT, territorio, provenienza, coordinate e formati;
6. esegue due build consecutive per verificare il determinismo.

Il confronto non è più un vincolo “sempre zero”: correzioni intenzionali sono
ammesse e vengono riportate campo per campo.

## Segnalare una correzione

Usare il modulo più specifico:

- [località errata](https://github.com/Codewriter90x/Italian_Cities/issues/new?template=wrong-locality.yml);
- [CAP errato](https://github.com/Codewriter90x/Italian_Cities/issues/new?template=wrong-postal-code.yml);
- [coordinata mancante](https://github.com/Codewriter90x/Italian_Cities/issues/new?template=missing-coordinate.yml);
- [variazione amministrativa](https://github.com/Codewriter90x/Italian_Cities/issues/new?template=administrative-change.yml).

Ogni proposta deve includere fonte, data, licenza e procedura riproducibile.
Le correzioni entrano nella pipeline, mai direttamente nei file generati.

## Riprodurre

Prerequisiti: Python 3.11+, Node.js 20+ e le dipendenze dichiarate.

```bash
python3 -m pip install -r requirements.txt
python3 scripts/build_dataset.py
python3 scripts/check_determinism.py
python3 scripts/validate_dataset.py
python3 -m unittest discover -s tests -v
node --test tests/pages_core.test.mjs
python3 scripts/build_release.py
python3 scripts/validate_release.py
python3 scripts/build_pages.py
```

## English summary

Italian Cities is an experimental, reproducible dataset of legacy Italian
place/postal-code associations. Postal codes and legacy coordinates are not
operationally verified. The working dataset is a prerelease and must not be
described as official, complete, or entirely CC0.
