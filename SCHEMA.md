# Dataset schema — version 2.0.0

## Perimetro semantico

Il dataset rappresenta associazioni tra un nome geografico e un CAP. Non è
un elenco ufficiale completo dei soli comuni italiani.

- **Comune**: unità amministrativa riconosciuta nell'elenco ISTAT scelto come
  riferimento. Nella Milestone 1 una riga è `municipality` soltanto se nome
  normalizzato e sigla di provincia coincidono esattamente.
- **Località**: luogo denominato e associato a un CAP; può non avere autonomia
  amministrativa o postale.
- **Frazione**: località subordinata a un comune. Il legacy non contiene il
  comune padre né una fonte sufficiente a distinguere con affidabilità le
  frazioni dalle altre località.
- **CAP**: codice di avviamento postale di cinque cifre. Può essere condiviso
  da più luoghi e un luogo può essere associato a più CAP; non è un
  identificatore.

`postal_locality_unclassified` è quindi una categoria prudenziale, non
sinonimo di frazione.

## Tabelle generate

### `municipalities.csv`

Grana: un comune riconosciuto nel dataset. `municipality_id` è
`IT-COM-<codice ISTAT>`. Contiene codice ISTAT, UUID legacy, nome e chiave
normalizzata, CAP, geografia amministrativa, coordinate e provenienza.

### `localities.csv`

Grana: una località postale non ancora riconciliata. `locality_id` è un UUIDv5
deterministico preceduto da `IT-LOC-`. `parent_municipality_id` resta vuoto
finché una fonte autorevole non documenta la relazione.

### `postal_codes.csv`

Grana: una relazione luogo-CAP. Il CAP non è una chiave univoca. Nella
Milestone 2 ogni luogo ha una sola relazione legacy marcata `is_primary=true`;
lo schema consente future relazioni multiple.

### `italian_locations.csv`

Vista canonica unificata di comuni e località. È l'unica base degli export
JSON, XLSX e SQLite.

## Schema della vista canonica

`data/italian_locations.csv` è UTF-8, delimitato da virgole, con
intestazione e terminatori di riga LF.

| Campo | Tipo/logica | Obbligatorio | Descrizione |
| --- | --- | --- | --- |
| `location_id` | stringa | sì | Identificatore canonico deterministico |
| `legacy_uuid` | UUID | sì | Identificatore originario conservato per migrazione |
| `name` | stringa | sì | Denominazione legacy |
| `normalized_name` | stringa | sì | Chiave di ricerca normalizzata |
| `location_kind` | enum | sì | `municipality` o `postal_locality_unclassified` |
| `municipality_istat_code` | stringa di 6 cifre | solo comuni | Codice ISTAT corrente del comune riconosciuto |
| `parent_municipality_id` | identificatore | no | Relazione futura, vuota finché non documentata |
| `postal_code` | stringa, `^[0-9]{5}$` | sì | CAP con eventuali zeri iniziali |
| `province_code` | stringa, `^[A-Z]{2}$` | sì | Sigla legacy della provincia |
| `province_name` | stringa | sì | Nome legacy della provincia |
| `region_name` | stringa | sì | Nome legacy della regione |
| `country_code` | ISO 3166-1 alpha-2 | sì | Sempre `IT` |
| `country_name` | stringa | sì | Nome paese legacy |
| `latitude` | decimale WGS84 | con longitudine | Vuoto se la coppia non è disponibile |
| `longitude` | decimale WGS84 | con latitudine | Vuoto se la coppia non è disponibile |
| `coordinate_status` | enum | sì | `available`, `corrected` o `missing` |
| `source_snapshot` | stringa | sì | Baseline di provenienza del record |

I campi vuoti sono l'unica rappresentazione ammessa dei valori mancanti. La
stringa letterale `NULL` non è ammessa nel canonico.

## Normalizzazione

`name` non viene riscritto. `normalized_name`:

1. uniforma apostrofi tipografici e backtick;
2. applica Unicode NFKD e rimuove i segni diacritici;
3. applica il case folding;
4. sostituisce punteggiatura e sequenze di spazi con un singolo spazio;
5. rimuove gli spazi iniziali e finali.

Esempi: `Sant’Agata`, `SANT'AGATA` e `sant agata` producono
`sant agata`; `Città` produce `citta`.

## Equivalenza dei formati

JSON conserva stringhe e ordine delle righe del CSV. SQLite usa colonne `TEXT`
per preservare identificativi, CAP e precisione testuale delle coordinate.
Nel workbook il CAP resta testo, mentre latitudine e longitudine sono numeriche.
Il validatore ammette per XLSX soltanto differenze di rappresentazione numerica
entro `1e-12`.

## Identificativi stabili

Per i comuni riconosciuti:

```text
IT-COM-<codice ISTAT a 6 cifre>
```

Per le località non classificate:

```text
IT-LOC-<UUIDv5>
```

L'UUIDv5 usa il namespace
`dcdcd1a0-8746-51cc-98a6-b31af7ae78b2` e la chiave:

```text
IT|<postal_code>|<province_code>|<normalized_name>
```

La normalizzazione rimuove segni diacritici, uniforma maiuscole/minuscole e
riduce punteggiatura e spazi. È deterministica, ma un cambio di nome, CAP o
provincia modifica l'identificativo della località. Le future riconciliazioni
devono quindi conservare una tabella di alias/migrazione. `legacy_uuid` non
deve essere riutilizzato per nuove righe.

## Contratto di qualità

Il quality gate `3.0.0` non modifica lo schema dati `2.0.0`. Verifica:

- intestazioni esatte e nessuna colonna aggiunta, rimossa o rinominata;
- identificativi non vuoti e unici alla grana di ogni tabella;
- CAP di cinque cifre;
- codici ISTAT di sei cifre presenti nello snapshot dichiarato;
- coerenza fra codice ISTAT, sigla di provincia e regione;
- coordinate complete, numeriche, finite e comprese nel bounding box
  prudenziale Italia `latitudine 35–48`, `longitudine 6–19`;
- nessuna riga completamente vuota e nessun duplicato logico;
- ricostruzione esatta del canonico tramite comuni, località e relazioni CAP;
- equivalenza degli export e due build consecutive deterministiche.

I nomi di provincia e regione sono display label legacy. La relazione
amministrativa autorevole usa il codice ISTAT e la sigla di provincia; il
validatore accetta i suffissi bilingui ufficiali nelle denominazioni regionali.

## Scelte di migrazione

- `visible` è stato omesso perché vale `True` per tutte le righe reali e non
  descrive una proprietà geografica.
- `country_code=IT` rende il paese machine-readable.
- latitudine e longitudine sono valori decimali WGS84; SQLite le conserva
  testualmente per evitare perdita di precisione ed XLSX le espone come numeri.
- l'ordine delle righe è deterministico e non costituisce identità.
- `NA` è la sigla valida della provincia di Napoli nel legacy, non un valore
  mancante. La Milestone 1 non contiene sigle di provincia vuote.
