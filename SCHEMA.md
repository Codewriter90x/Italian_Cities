# Dataset schema — 3.0.0

La v2 separa identità amministrativa, località e relazioni CAP. Il CAP non è
mai una chiave univoca e l'assenza di CAP non elimina un comune.

## Identificativi

- comune: `IT-COM-<codice ISTAT a 6 cifre>`;
- località: `IT-LOC-<UUIDv5>` da nome normalizzato, provincia, coordinate ed
  esito di riconciliazione;
- relazione CAP: `IT-PCR-<UUIDv5>` da `location_id` e CAP, oppure `missing`.

## `municipalities.csv`

Una riga per ciascuno dei 7.894 comuni ISTAT. Campi:

`municipality_id`, `istat_code`, `name`, `normalized_name`, `province_code`,
`province_name`, `region_name`, `country_code`, `country_name`, `latitude`,
`longitude`, `coordinate_verification`, `coordinate_accuracy`,
`coordinate_source_id`, `coordinate_source_record_id`,
`coordinate_source_date`, `coordinate_method`, `coordinate_confidence`,
`administrative_source_id`, `administrative_source_record_id`,
`administrative_source_date`, `source_ids`.

Il codice ISTAT è la chiave stabile. Coordinate e campi `coordinate_*` restano
vuoti/`missing` quando non esiste un match GeoNames esatto.

## `localities.csv`

Una riga per ogni luogo GeoNames non riconciliato con certezza:

`locality_id`, `name`, `normalized_name`, `locality_type`,
`parent_municipality_id`, `candidate_municipality_ids`, `province_code`,
`province_name`, `region_name`, `country_code`, `country_name`, `latitude`,
`longitude`, `coordinate_verification`, `coordinate_accuracy`, `source_id`,
`source_record_ids`, `source_reference_date`, `reconciliation_outcome`,
`reconciliation_method`, `reconciliation_confidence`.

`parent_municipality_id` è sempre vuoto per record ambigui o non riconciliati.
Le sigle territoriali obsolete presenti in GeoNames, come `SU`, sono
preservate soltanto su località `unmatched_no_parent` e non vengono promosse a
classificazione ISTAT.

## `postal_codes.csv`

Una riga per relazione molti-a-molti:

`postal_code_relation_id`, `location_id`, `location_kind`, `postal_code`,
`postal_code_status`, `province_code`, `is_primary`, `source_id`,
`source_record_ids`, `source_reference_date`, `match_method`, `confidence`,
`accuracy`.

Un comune senza CAP ha una relazione con `postal_code=""` e
`postal_code_status=missing`. Ogni altro CAP deve rispettare `^[0-9]{5}$`.

## `italian_locations.csv`

Vista unificata, una riga per relazione CAP:

| Campo | Descrizione |
| --- | --- |
| `location_postal_id` | chiave univoca della riga |
| `location_id` | comune o località |
| `name`, `normalized_name` | denominazione e chiave normalizzata |
| `location_kind` | `municipality`, `geonames_unreconciled` o `geonames_ambiguous` |
| `municipality_istat_code` | presente soltanto per comuni |
| `parent_municipality_id` | vuoto finché non documentato |
| `candidate_municipality_ids` | candidati ordinati per match multiplo |
| `postal_code` | cinque cifre o vuoto con stato `missing` |
| `postal_code_status` | stato della relazione CAP |
| `province_code`, `province_name`, `region_name` | contesto territoriale |
| `country_code`, `country_name` | `IT`, `Italia` |
| `latitude`, `longitude` | coppia WGS84 opzionale |
| `coordinate_verification` | origine/semantica della coordinata |
| `coordinate_accuracy` | campo GeoNames `accuracy`, preservato |
| `reconciliation_outcome` | esito separato dal dato CAP |
| `reconciliation_method` | regola riproducibile applicata |
| `reconciliation_confidence` | `high`, `ambiguous`, `unmatched`, `not_applicable` |
| `source_ids` | fonti canoniche coinvolte |
| `source_record_ids` | record sorgente tracciabili |
| `source_reference_dates` | date associate alle fonti |

## Enum

`postal_code_status`:

- `geonames_matched`;
- `geonames_ambiguous`;
- `official_verified` — riservato, inutilizzato;
- `obsolete` — riservato, inutilizzato;
- `missing`.

`coordinate_verification`:

- `geonames_estimated`;
- `geonames_place_match`;
- `official_boundary_derived` — riservato, inutilizzato;
- `missing`.

`reconciliation_outcome`:

- `exact_unambiguous`;
- `multiple_candidates`;
- `unmatched_no_parent`;
- `istat_without_postal_code`.

## Riconciliazione

Un match è `exact_unambiguous` soltanto quando:

1. il nome normalizzato coincide;
2. la sigla provincia GeoNames coincide;
3. nome provincia e regione sono compatibili con ISTAT;
4. rimane un solo candidato.

Il CAP partecipa all'identità e alla deduplicazione della relazione, ma non
viene usato per inventare un comune padre. Non esiste fuzzy matching.

## Formati e null

CSV e JSON sono UTF-8. CAP e identificativi restano stringhe. SQLite e SQL
usano colonne `TEXT NOT NULL`; il valore mancante è la stringa vuota, mai
`NULL`. XLSX conserva CAP come testo, coordinate come numeri e include un
foglio `Dataset Info` con attribuzione e warning.

CSV, JSON, XLSX, SQLite e SQL devono avere lo stesso ordine di campi, record e
digest semantico. Due build consecutive devono essere identiche.
