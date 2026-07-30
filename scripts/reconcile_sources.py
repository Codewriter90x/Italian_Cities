#!/usr/bin/env python3
"""Conservatively reconcile GeoNames postal places with ISTAT municipalities."""

from __future__ import annotations

import hashlib
import uuid
from collections import Counter, defaultdict
from collections.abc import Iterable

from dataset_common import normalize_name

LOCATION_NAMESPACE = uuid.uuid5(
    uuid.NAMESPACE_URL,
    "https://github.com/Codewriter90x/Italian_Cities/v2/location",
)
RELATION_NAMESPACE = uuid.uuid5(
    uuid.NAMESPACE_URL,
    "https://github.com/Codewriter90x/Italian_Cities/v2/postal-relation",
)
REGION_ALIASES = {
    "abruzzi": "abruzzo",
}


def normalized_territory(value: str) -> str:
    normalized = normalize_name(value)
    return REGION_ALIASES.get(normalized, normalized)


def territory_compatible(left: str, right: str) -> bool:
    left_key = normalized_territory(left)
    right_key = normalized_territory(right)
    return (
        left_key == right_key
        or left_key.startswith(f"{right_key} ")
        or right_key.startswith(f"{left_key} ")
    )


def stable_locality_id(identity: Iterable[str]) -> str:
    value = "|".join(identity)
    return f"IT-LOC-{uuid.uuid5(LOCATION_NAMESPACE, value)}"


def stable_relation_id(location_id: str, postal_code: str) -> str:
    value = f"{location_id}|{postal_code or 'missing'}"
    return f"IT-PCR-{uuid.uuid5(RELATION_NAMESPACE, value)}"


def _source_dates(
    *,
    istat_date: str = "",
    geonames_date: str = "",
) -> str:
    values = []
    if istat_date:
        values.append(f"istat_municipalities={istat_date}")
    if geonames_date:
        values.append(f"geonames_postal_codes={geonames_date}")
    return ";".join(values)


def _best_coordinate(
    records: list[dict[str, str]],
) -> dict[str, str] | None:
    available = [
        record
        for record in records
        if record["latitude"] and record["longitude"]
    ]
    if not available:
        return None
    return sorted(
        available,
        key=lambda row: (
            -int(row["accuracy"] or "0"),
            row["postal_code"],
            row["source_record_id"],
        ),
    )[0]


def reconcile(
    istat_records: list[dict[str, str]],
    geonames_records: list[dict[str, str]],
    *,
    istat_reference_date: str,
    geonames_reference_date: str,
) -> dict[str, object]:
    name_index: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    provinces: dict[str, dict[str, str]] = {}
    for municipality in istat_records:
        provinces.setdefault(municipality["province_code"], municipality)
        names = {
            municipality["normalized_name"],
            normalize_name(municipality["bilingual_name"]),
        }
        for name in names:
            if name:
                name_index[(name, municipality["province_code"])].append(
                    municipality
                )

    outcomes: list[dict[str, object]] = []
    exact_by_istat: dict[str, list[dict[str, str]]] = defaultdict(list)
    unresolved: list[tuple[dict[str, str], str, list[str]]] = []
    for geonames in geonames_records:
        candidates = name_index.get(
            (geonames["normalized_name"], geonames["admin_code2"]),
            [],
        )
        compatible = [
            candidate
            for candidate in candidates
            if territory_compatible(
                geonames["admin_name1"], candidate["region_name"]
            )
            and territory_compatible(
                geonames["admin_name2"], candidate["province_name"]
            )
        ]
        candidate_ids = sorted(
            f"IT-COM-{candidate['istat_code']}" for candidate in compatible
        )
        if len(compatible) == 1:
            outcome = "exact_unambiguous"
            exact_by_istat[compatible[0]["istat_code"]].append(geonames)
        elif len(compatible) > 1:
            outcome = "multiple_candidates"
            unresolved.append((geonames, outcome, candidate_ids))
        else:
            outcome = "unmatched_no_parent"
            unresolved.append((geonames, outcome, []))
        outcomes.append(
            {
                "source_record_id": geonames["source_record_id"],
                "outcome": outcome,
                "candidate_municipality_ids": candidate_ids,
            }
        )

    municipalities: list[dict[str, str]] = []
    postal_codes: list[dict[str, str]] = []
    municipality_lookup: dict[str, dict[str, str]] = {}
    for official in istat_records:
        location_id = f"IT-COM-{official['istat_code']}"
        matches = exact_by_istat.get(official["istat_code"], [])
        coordinate = _best_coordinate(matches)
        municipality = {
            "municipality_id": location_id,
            "istat_code": official["istat_code"],
            "name": official["name"],
            "normalized_name": official["normalized_name"],
            "province_code": official["province_code"],
            "province_name": official["province_name"],
            "region_name": official["region_name"],
            "country_code": "IT",
            "country_name": "Italia",
            "latitude": coordinate["latitude"] if coordinate else "",
            "longitude": coordinate["longitude"] if coordinate else "",
            "coordinate_verification": (
                "geonames_place_match" if coordinate else "missing"
            ),
            "coordinate_accuracy": coordinate["accuracy"] if coordinate else "",
            "coordinate_source_id": (
                "geonames_postal_codes" if coordinate else ""
            ),
            "coordinate_source_record_id": (
                coordinate["source_record_id"] if coordinate else ""
            ),
            "coordinate_source_date": (
                geonames_reference_date if coordinate else ""
            ),
            "coordinate_method": (
                "exact_name_province_region_best_accuracy"
                if coordinate
                else "missing"
            ),
            "coordinate_confidence": "high" if coordinate else "missing",
            "administrative_source_id": "istat_municipalities",
            "administrative_source_record_id": official["istat_code"],
            "administrative_source_date": istat_reference_date,
            "source_ids": (
                "istat_municipalities;geonames_postal_codes"
                if matches
                else "istat_municipalities"
            ),
        }
        municipalities.append(municipality)
        municipality_lookup[location_id] = municipality

        by_postal: dict[str, list[dict[str, str]]] = defaultdict(list)
        for match in matches:
            by_postal[match["postal_code"]].append(match)
        if not by_postal:
            postal_codes.append(
                {
                    "postal_code_relation_id": stable_relation_id(
                        location_id, ""
                    ),
                    "location_id": location_id,
                    "location_kind": "municipality",
                    "postal_code": "",
                    "postal_code_status": "missing",
                    "province_code": official["province_code"],
                    "is_primary": "true",
                    "source_id": "istat_municipalities",
                    "source_record_ids": official["istat_code"],
                    "source_reference_date": istat_reference_date,
                    "match_method": "no_geonames_exact_match",
                    "confidence": "not_applicable",
                    "accuracy": "",
                }
            )
        else:
            for index, (postal_code, records) in enumerate(
                sorted(by_postal.items())
            ):
                postal_codes.append(
                    {
                        "postal_code_relation_id": stable_relation_id(
                            location_id, postal_code
                        ),
                        "location_id": location_id,
                        "location_kind": "municipality",
                        "postal_code": postal_code,
                        "postal_code_status": "geonames_matched",
                        "province_code": official["province_code"],
                        "is_primary": "true" if index == 0 else "false",
                        "source_id": "geonames_postal_codes",
                        "source_record_ids": ";".join(
                            sorted(
                                record["source_record_id"]
                                for record in records
                            )
                        ),
                        "source_reference_date": geonames_reference_date,
                        "match_method": "exact_name_province_region",
                        "confidence": "high",
                        "accuracy": max(
                            (record["accuracy"] for record in records),
                            key=lambda value: int(value or "0"),
                        ),
                    }
                )

    locality_groups: dict[
        tuple[str, str, str, str, str, tuple[str, ...]],
        list[dict[str, str]],
    ] = defaultdict(list)
    for geonames, outcome, candidate_ids in unresolved:
        key = (
            geonames["normalized_name"],
            geonames["admin_code2"],
            geonames["latitude"],
            geonames["longitude"],
            outcome,
            tuple(candidate_ids),
        )
        locality_groups[key].append(geonames)

    localities: list[dict[str, str]] = []
    locality_lookup: dict[str, dict[str, str]] = {}
    for key, records in sorted(locality_groups.items()):
        first = sorted(records, key=lambda row: row["source_record_id"])[0]
        (
            normalized_name,
            province_code,
            latitude,
            longitude,
            outcome,
            candidate_tuple,
        ) = key
        locality_id = stable_locality_id(
            (
                normalized_name,
                province_code,
                latitude,
                longitude,
                outcome,
                ";".join(candidate_tuple),
            )
        )
        official_territory = provinces.get(province_code)
        accuracy = max(
            (record["accuracy"] for record in records),
            key=lambda value: int(value or "0"),
        )
        source_record_ids = ";".join(
            sorted(record["source_record_id"] for record in records)
        )
        locality = {
            "locality_id": locality_id,
            "name": first["place_name"],
            "normalized_name": normalized_name,
            "locality_type": (
                "geonames_ambiguous"
                if outcome == "multiple_candidates"
                else "geonames_unreconciled"
            ),
            "parent_municipality_id": "",
            "candidate_municipality_ids": ";".join(candidate_tuple),
            "province_code": province_code,
            "province_name": (
                official_territory["province_name"]
                if official_territory
                else first["admin_name2"]
            ),
            "region_name": (
                official_territory["region_name"]
                if official_territory
                else first["admin_name1"]
            ),
            "country_code": "IT",
            "country_name": "Italia",
            "latitude": latitude,
            "longitude": longitude,
            "coordinate_verification": (
                "geonames_estimated" if latitude and longitude else "missing"
            ),
            "coordinate_accuracy": accuracy,
            "source_id": "geonames_postal_codes",
            "source_record_ids": source_record_ids,
            "source_reference_date": geonames_reference_date,
            "reconciliation_outcome": outcome,
            "reconciliation_method": "exact_name_province_region",
            "reconciliation_confidence": (
                "ambiguous"
                if outcome == "multiple_candidates"
                else "unmatched"
            ),
        }
        localities.append(locality)
        locality_lookup[locality_id] = locality

        locality_by_postal: dict[
            str, list[dict[str, str]]
        ] = defaultdict(list)
        for record in records:
            locality_by_postal[record["postal_code"]].append(record)
        for index, (postal_code, postal_records) in enumerate(
            sorted(locality_by_postal.items())
        ):
            postal_codes.append(
                {
                    "postal_code_relation_id": stable_relation_id(
                        locality_id, postal_code
                    ),
                    "location_id": locality_id,
                    "location_kind": locality["locality_type"],
                    "postal_code": postal_code,
                    "postal_code_status": (
                        "geonames_ambiguous"
                        if outcome == "multiple_candidates"
                        else "geonames_matched"
                    ),
                    "province_code": province_code,
                    "is_primary": "true" if index == 0 else "false",
                    "source_id": "geonames_postal_codes",
                    "source_record_ids": ";".join(
                        sorted(
                            record["source_record_id"]
                            for record in postal_records
                        )
                    ),
                    "source_reference_date": geonames_reference_date,
                    "match_method": "exact_name_province_region",
                    "confidence": locality["reconciliation_confidence"],
                    "accuracy": max(
                        (record["accuracy"] for record in postal_records),
                        key=lambda value: int(value or "0"),
                    ),
                }
            )

    municipalities.sort(key=lambda row: row["istat_code"])
    localities.sort(
        key=lambda row: (
            row["normalized_name"],
            row["province_code"],
            row["locality_id"],
        )
    )
    postal_codes.sort(
        key=lambda row: (
            row["location_id"],
            row["postal_code"],
            row["postal_code_relation_id"],
        )
    )

    italian_locations: list[dict[str, str]] = []
    for relation in postal_codes:
        if relation["location_kind"] == "municipality":
            municipality = municipality_lookup[relation["location_id"]]
            reconciliation_outcome = (
                "exact_unambiguous"
                if relation["postal_code_status"] == "geonames_matched"
                else "istat_without_postal_code"
            )
            source_ids = municipality["source_ids"]
            source_record_ids = ";".join(
                filter(
                    None,
                    (
                        municipality["administrative_source_record_id"],
                        relation["source_record_ids"],
                    ),
                )
            )
            source_dates = _source_dates(
                istat_date=istat_reference_date,
                geonames_date=(
                    geonames_reference_date
                    if relation["source_id"] == "geonames_postal_codes"
                    else ""
                ),
            )
            row = {
                "location_postal_id": relation["postal_code_relation_id"],
                "location_id": municipality["municipality_id"],
                "name": municipality["name"],
                "normalized_name": municipality["normalized_name"],
                "location_kind": "municipality",
                "municipality_istat_code": municipality["istat_code"],
                "parent_municipality_id": "",
                "candidate_municipality_ids": "",
                "postal_code": relation["postal_code"],
                "postal_code_status": relation["postal_code_status"],
                "province_code": municipality["province_code"],
                "province_name": municipality["province_name"],
                "region_name": municipality["region_name"],
                "country_code": municipality["country_code"],
                "country_name": municipality["country_name"],
                "latitude": municipality["latitude"],
                "longitude": municipality["longitude"],
                "coordinate_verification": municipality[
                    "coordinate_verification"
                ],
                "coordinate_accuracy": municipality["coordinate_accuracy"],
                "reconciliation_outcome": reconciliation_outcome,
                "reconciliation_method": relation["match_method"],
                "reconciliation_confidence": relation["confidence"],
                "source_ids": source_ids,
                "source_record_ids": source_record_ids,
                "source_reference_dates": source_dates,
            }
        else:
            locality = locality_lookup[relation["location_id"]]
            row = {
                "location_postal_id": relation["postal_code_relation_id"],
                "location_id": locality["locality_id"],
                "name": locality["name"],
                "normalized_name": locality["normalized_name"],
                "location_kind": locality["locality_type"],
                "municipality_istat_code": "",
                "parent_municipality_id": "",
                "candidate_municipality_ids": locality[
                    "candidate_municipality_ids"
                ],
                "postal_code": relation["postal_code"],
                "postal_code_status": relation["postal_code_status"],
                "province_code": locality["province_code"],
                "province_name": locality["province_name"],
                "region_name": locality["region_name"],
                "country_code": locality["country_code"],
                "country_name": locality["country_name"],
                "latitude": locality["latitude"],
                "longitude": locality["longitude"],
                "coordinate_verification": locality[
                    "coordinate_verification"
                ],
                "coordinate_accuracy": locality["coordinate_accuracy"],
                "reconciliation_outcome": locality[
                    "reconciliation_outcome"
                ],
                "reconciliation_method": locality[
                    "reconciliation_method"
                ],
                "reconciliation_confidence": locality[
                    "reconciliation_confidence"
                ],
                "source_ids": "geonames_postal_codes",
                "source_record_ids": relation["source_record_ids"],
                "source_reference_dates": _source_dates(
                    geonames_date=geonames_reference_date
                ),
            }
        italian_locations.append(row)

    italian_locations.sort(
        key=lambda row: (
            row["normalized_name"],
            row["province_code"],
            row["postal_code"],
            row["location_id"],
            row["location_postal_id"],
        )
    )
    counts = Counter(item["outcome"] for item in outcomes)
    canonical_digest_material = "\n".join(
        f"{row['location_postal_id']}|{row['source_record_ids']}"
        for row in italian_locations
    )
    return {
        "municipalities": municipalities,
        "localities": localities,
        "postal_codes": postal_codes,
        "italian_locations": italian_locations,
        "reconciliation_outcomes": outcomes,
        "statistics": {
            "istat_municipalities": len(istat_records),
            "geonames_records": len(geonames_records),
            "postal_code_relations": len(postal_codes),
            "localities": len(localities),
            "exact_matches": counts["exact_unambiguous"],
            "ambiguous_matches": counts["multiple_candidates"],
            "unmatched_geonames": counts["unmatched_no_parent"],
            "municipalities_without_postal_code": sum(
                not exact_by_istat.get(record["istat_code"])
                for record in istat_records
            ),
        },
        "canonical_source_digest": hashlib.sha256(
            canonical_digest_material.encode("utf-8")
        ).hexdigest(),
    }
