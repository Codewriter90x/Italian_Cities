# Italian Cities

Dataset italiano riproducibile di comuni, località, relazioni CAP e
coordinate, costruito con una pipeline **clean room**.

**[Ricerca web](https://codewriter90x.github.io/Italian_Cities/)** ·
[Schema](SCHEMA.md) · [Fonti](DATA_SOURCES.md) ·
[Pipeline](DATASET_PIPELINE.md) ·
[Segnala una correzione](https://github.com/Codewriter90x/Italian_Cities/issues/new/choose)

> [!CAUTION]
> La v2 è una prerelease sperimentale, non una banca dati postale ufficiale.
> GeoNames non è Poste Italiane. CAP e coordinate sono forniti senza garanzia;
> alcune coordinate GeoNames sono stimate algoritmicamente. Non usare il
> dataset per certificare o indirizzare spedizioni.

**Dataset:** `v2.0.0` prerelease · **Schema:** `3.0.0` ·
**Build:** 30 luglio 2026
**Structural quality:** `passed` · **Operational data readiness:**
`experimental_non_official`

Il tag e la prerelease
[`v2.0.0`](https://github.com/Codewriter90x/Italian_Cities/releases/tag/v2.0.0)
sono pubblicati con tag protetto, attestazioni e checksum SHA-256. Gli asset
della v2.0.0 non sono retroattivamente immutabili; il workflow applica il
processo draft–upload–publish alle release future. L'impostazione GitHub
**Immutable releases** è attiva dal 30 luglio 2026 e si applica soltanto alle
release pubblicate dopo l'attivazione.

## Fonti canoniche

La v2 deriva esclusivamente da:

1. elenco ufficiale dei comuni ISTAT del 21 febbraio 2026;
2. dump gratuito [GeoNames Postal Codes per l'Italia](https://download.geonames.org/export/zip/IT.zip),
   snapshot del 30 luglio 2026.

Entrambe le fonti richiedono attribuzione CC BY 4.0. Il file GeoNames originale
è conservato e verificato tramite SHA-256. Il legacy rimane sotto `legacy/`,
ma non contribuisce ad alcun CSV, JSON, XLSX, SQLite, SQL o dato della Pages.
È letto soltanto per [`reports/legacy-comparison.json`](reports/legacy-comparison.json).

## Copertura della v2

| Contenuto | Conteggio | Interpretazione |
| --- | ---: | --- |
| Comuni ISTAT | 7.894 | tutti i comuni dello snapshot, chiave stabile codice ISTAT |
| Record GeoNames | 18.415 | righe originali del dump |
| Relazioni CAP | 18.811 | include 396 relazioni esplicite `missing` |
| Località GeoNames non riconciliate | 10.270 | nessun comune padre inferito |
| Record GeoNames con match esatto | 8.095 | nome, provincia e regione coerenti |
| Match ambigui | 0 | nessuno nello snapshot corrente; il caso è comunque modellato |
| Comuni senza CAP GeoNames | 396 | il comune resta presente |

Coordinate nella vista canonica:

| Stato | Righe |
| --- | ---: |
| `geonames_place_match` | 8.095 |
| `geonames_estimated` | 10.320 |
| `missing` | 396 |

Accuracy GeoNames preservata: livello `1` su 46 righe, `3` su 2.418, `4` su
15.951; 396 righe senza coordinate. Questi conteggi misurano presenza e
classificazione, non correttezza certificata.

Alla grana del luogo univoco: 7.498 comuni hanno coordinate
`geonames_place_match`, 10.270 località hanno coordinate
`geonames_estimated` e 396 comuni sono `missing`.

## Dataset

| File | Grana |
| --- | --- |
| `data/municipalities.csv` | un comune per codice ISTAT |
| `data/localities.csv` | una località GeoNames non riconciliata o ambigua |
| `data/postal_codes.csv` | una relazione molti-a-molti luogo–CAP |
| `data/italian_locations.csv` | vista unificata, una riga per relazione CAP |
| `data/italian_locations.json` | stessa vista e metadata di provenienza |
| `data/italian_locations.xlsx` | stessa vista più foglio informativo |
| `data/italian_locations.sqlite` | stessa vista e metadata |

Il bundle pubblicato aggiunge `italian_locations.sql` e `SHA256SUMS`.
Tutti gli output sono generati: non modificarli manualmente.

## Stati principali

- `postal_code_status`: `geonames_matched`, `geonames_ambiguous`, `missing`;
  `official_verified` e `obsolete` sono riservati e inutilizzati.
- `coordinate_verification`: `geonames_place_match`,
  `geonames_estimated`, `missing`; `official_boundary_derived` è riservato e
  inutilizzato.
- `reconciliation_outcome`: `exact_unambiguous`,
  `multiple_candidates`, `unmatched_no_parent`,
  `istat_without_postal_code`.

Nessun candidato multiplo viene scelto automaticamente. Lo schema completo è
in [`SCHEMA.md`](SCHEMA.md).

## Download della release v2.0.0

- [municipalities.csv](https://github.com/Codewriter90x/Italian_Cities/releases/download/v2.0.0/municipalities.csv)
- [localities.csv](https://github.com/Codewriter90x/Italian_Cities/releases/download/v2.0.0/localities.csv)
- [postal_codes.csv](https://github.com/Codewriter90x/Italian_Cities/releases/download/v2.0.0/postal_codes.csv)
- [italian_locations.csv](https://github.com/Codewriter90x/Italian_Cities/releases/download/v2.0.0/italian_locations.csv)
- [italian_locations.json](https://github.com/Codewriter90x/Italian_Cities/releases/download/v2.0.0/italian_locations.json)
- [italian_locations.xlsx](https://github.com/Codewriter90x/Italian_Cities/releases/download/v2.0.0/italian_locations.xlsx)
- [italian_locations.sqlite](https://github.com/Codewriter90x/Italian_Cities/releases/download/v2.0.0/italian_locations.sqlite)
- [italian_locations.sql](https://github.com/Codewriter90x/Italian_Cities/releases/download/v2.0.0/italian_locations.sql)
- [SHA256SUMS](https://github.com/Codewriter90x/Italian_Cities/releases/download/v2.0.0/SHA256SUMS)

## Esempi

### C#

```csharp
using System.Net.Http;
using System.Text.Json;

var url = "https://github.com/Codewriter90x/Italian_Cities/" +
          "releases/download/v2.0.0/italian_locations.json";
using var http = new HttpClient();
await using var stream = await http.GetStreamAsync(url);
using var document = await JsonDocument.ParseAsync(stream);

foreach (var row in document.RootElement.GetProperty("rows").EnumerateArray())
{
    if (row.GetProperty("municipality_istat_code").GetString() == "058091")
        Console.WriteLine(row.GetProperty("postal_code").GetString());
}
```

### Python

```python
import csv

with open("data/municipalities.csv", encoding="utf-8", newline="") as source:
    for row in csv.DictReader(source):
        if row["province_code"] == "RM":
            print(row["istat_code"], row["name"])
```

### JavaScript

```javascript
const response = await fetch("./data/italian_locations.json");
const dataset = await response.json();
const missing = dataset.rows.filter(
  (row) => row.postal_code_status === "missing",
);
console.log(dataset.metadata.operational_data_readiness, missing.length);
```

### SQL

```sql
SELECT name, postal_code, postal_code_status, coordinate_accuracy
FROM italian_locations
WHERE normalized_name = 'roma'
ORDER BY postal_code;
```

## Build e validazione

Richiede Python 3.11–3.13:

```bash
python -m pip install -r requirements.txt -r requirements-dev.txt
python scripts/build_dataset.py
python scripts/check_determinism.py
python scripts/validate_dataset.py
python -m unittest discover -s tests -v
node --test tests/pages_core.test.mjs
python scripts/build_pages.py
python scripts/build_release.py
python scripts/validate_release.py
```

La CI aggiunge Ruff, mypy, coverage, matrice Python 3.11–3.13, CodeQL e
controlli deterministici. Dettagli in [`DATASET_PIPELINE.md`](DATASET_PIPELINE.md).

## Differenze rispetto al legacy

Il confronto investigativo trova 10.881 coppie esatte nome–CAP e 10.738
coppie esatte nome–provincia–CAP, 3.742 record soltanto nel legacy, 7.677
soltanto in GeoNames, 3.018 insiemi CAP discordanti e 1.414 differenze
coordinate oltre 0,01 gradi. Una somiglianza non prova la provenienza del
legacy.

I 3.742 record esclusivi del legacy scompaiono dal canonico perché la loro
origine e licenza non sono dimostrate e non sono presenti nello snapshot
GeoNames scelto. I comuni ISTAT mancanti nel legacy, invece, entrano nella v2
anche senza CAP.

## Licenze e attribuzione

- Il codice e la documentazione originali del repository sono dedicati CC0
  1.0 nei limiti dei diritti detenuti.
- © Istituto nazionale di statistica (ISTAT), dati riutilizzati secondo
  CC BY 4.0.
- GeoNames Postal Codes, © GeoNames, CC BY 4.0,
  <https://www.geonames.org/>.

Il dataset canonico derivato non è CC0 e richiede entrambe le attribuzioni.
GeoNames non è una fonte ufficiale di Poste Italiane. Vedere
[`DATA_LICENSE.md`](DATA_LICENSE.md), [`NOTICE.md`](NOTICE.md) e
[`DATA_SOURCES.md`](DATA_SOURCES.md).

## Aggiornamenti e correzioni

Ogni aggiornamento richiede uno snapshot immutabile, checksum, licenza,
attribuzione, build deterministica e una PR verde. Per una correzione aprire
un [issue form](https://github.com/Codewriter90x/Italian_Cities/issues/new/choose)
indicando record, fonte, data e licenza.

Un esempio completo del processo è disponibile in
[`docs/SOURCE_BACKED_CORRECTION_EXAMPLE.md`](docs/SOURCE_BACKED_CORRECTION_EXAMPLE.md).
