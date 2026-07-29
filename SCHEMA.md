# Canonical schema

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

## File canonico

`data/italian_postal_localities.csv` è UTF-8, delimitato da virgole, con
intestazione e terminatori di riga LF.

| Campo | Tipo/logica | Obbligatorio | Descrizione |
| --- | --- | --- | --- |
| `location_id` | stringa | sì | Identificatore canonico deterministico |
| `legacy_uuid` | UUID | sì | Identificatore originario conservato per migrazione |
| `name` | stringa | sì | Denominazione legacy |
| `postal_code` | stringa, `^[0-9]{5}$` | sì | CAP con eventuali zeri iniziali |
| `record_type` | enum | sì | `municipality` o `postal_locality_unclassified` |
| `municipality_istat_code` | stringa di 6 cifre | solo comuni | Codice ISTAT corrente del comune riconosciuto |
| `province_code` | stringa, `^[A-Z]{2}$` | sì | Sigla legacy della provincia |
| `province_name` | stringa | sì | Nome legacy della provincia |
| `region_name` | stringa | sì | Nome legacy della regione |
| `country_code` | ISO 3166-1 alpha-2 | sì | Sempre `IT` nella Milestone 1 |
| `country_name` | stringa | sì | Nome paese legacy |
| `latitude` | decimale WGS84 | con longitudine | Vuoto se la coppia non è disponibile |
| `longitude` | decimale WGS84 | con latitudine | Vuoto se la coppia non è disponibile |
| `coordinate_status` | enum | sì | `available`, `corrected` o `missing` |
| `source_snapshot` | stringa | sì | Baseline di provenienza del record |

I campi vuoti sono l'unica rappresentazione ammessa dei valori mancanti. La
stringa letterale `NULL` non è ammessa nel canonico.

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

## Scelte di migrazione

- `visible` è stato omesso perché vale `True` per tutte le righe reali e non
  descrive una proprietà geografica.
- `country_code=IT` rende il paese machine-readable.
- latitudine e longitudine sono numeriche, non testo SQL generico.
- l'ordine delle righe è deterministico e non costituisce identità.
- `NA` è la sigla valida della provincia di Napoli nel legacy, non un valore
  mancante. La Milestone 1 non contiene sigle di provincia vuote.
