import test from "node:test";
import assert from "node:assert/strict";

import {
  filtersFromSearchParams,
  filtersToSearchParams,
  formatInteger,
  inflateRows,
  normalizeTerm,
  projectCoordinates,
  searchLocations,
} from "../site/assets/core.mjs";

const rows = [
  {
    location_id: "IT-COM-054013",
    name: "Città di Castello",
    normalized_name: "citta di castello",
    location_kind: "municipality",
    municipality_istat_code: "054013",
    postal_code: "06012",
    province_code: "PG",
    province_name: "Perugia",
    region_name: "Umbria",
    latitude: 43.46,
    longitude: 12.24,
    coordinate_verification: "geonames_place_match",
  },
  {
    location_id: "IT-LOC-002",
    name: "Roma Centro",
    normalized_name: "roma centro",
    location_kind: "geonames_unreconciled",
    municipality_istat_code: "",
    postal_code: "00186",
    province_code: "RM",
    province_name: "Roma",
    region_name: "Lazio",
    latitude: 41.9,
    longitude: 12.5,
    coordinate_verification: "geonames_estimated",
  },
  {
    location_id: "IT-COM-001001",
    name: "Agliè",
    normalized_name: "aglie",
    location_kind: "municipality",
    municipality_istat_code: "001001",
    postal_code: "",
    province_code: "TO",
    province_name: "Torino",
    region_name: "Piemonte",
    latitude: null,
    longitude: null,
    coordinate_verification: "missing",
  },
];

test("normalization ignores accents, apostrophes and case", () => {
  assert.equal(normalizeTerm("  CITTÀ d’Italia  "), "citta d italia");
});

test("inflates compact page rows without changing legacy object rows", () => {
  assert.deepEqual(
    inflateRows(["name", "postal_code"], [["Roma", "00186"]]),
    [{ name: "Roma", postal_code: "00186" }],
  );
  assert.equal(inflateRows([], rows), rows);
  assert.throws(
    () => inflateRows([], [["Roma"]]),
    /require a field list/,
  );
});

test("searches by name, postal code and province", () => {
  assert.equal(searchLocations(rows, { query: "citta castello" }).total, 1);
  assert.equal(searchLocations(rows, { query: "00186" }).total, 1);
  assert.equal(searchLocations(rows, { query: "RM" }).total, 1);
});

test("filters clean-room location kinds and coordinate states", () => {
  assert.equal(
    searchLocations(rows, {
      kind: "geonames_unreconciled",
      coordinateStatus: "geonames_estimated",
    }).total,
    1,
  );
  assert.equal(
    searchLocations(rows, { coordinateStatus: "geonames_place_match" }).total,
    1,
  );
  assert.equal(
    searchLocations(rows, { coordinateStatus: "missing" }).total,
    1,
  );
});

test("projects coordinates inside the drawing area", () => {
  const bounds = {
    min_latitude: 35,
    max_latitude: 48,
    min_longitude: 6,
    max_longitude: 19,
  };
  assert.deepEqual(projectCoordinates(6, 48, 500, 700, bounds), {
    x: 24,
    y: 24,
  });
  assert.deepEqual(projectCoordinates(19, 35, 500, 700, bounds), {
    x: 476,
    y: 676,
  });
});

test("round-trips shareable clean-room filters", () => {
  const filters = {
    query: "Città d'Italia",
    province: "TO",
    kind: "municipality",
    coordinateStatus: "geonames_place_match",
  };
  const encoded = filtersToSearchParams(filters);
  assert.deepEqual(filtersFromSearchParams(encoded), filters);
});

test("rejects unsupported URL filter values", () => {
  assert.deepEqual(
    filtersFromSearchParams(
      "q=Roma&province=invalid&kind=legacy&coordinates=verified",
    ),
    {
      query: "Roma",
      province: "",
      kind: "",
      coordinateStatus: "",
    },
  );
});

test("formats Italian thousands deterministically", () => {
  assert.equal(formatInteger(18811), "18.811");
});
