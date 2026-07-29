import test from "node:test";
import assert from "node:assert/strict";

import {
  formatInteger,
  normalizeTerm,
  projectCoordinates,
  searchLocations,
} from "../site/assets/core.mjs";

const rows = [
  {
    location_id: "IT-COM-001",
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
    coordinate_status: "available",
  },
  {
    location_id: "IT-LOC-002",
    name: "Roma Centro",
    normalized_name: "roma centro",
    location_kind: "postal_locality_unclassified",
    municipality_istat_code: "",
    postal_code: "00186",
    province_code: "RM",
    province_name: "Roma",
    region_name: "Lazio",
    latitude: null,
    longitude: null,
    coordinate_status: "missing",
  },
  {
    location_id: "IT-COM-003",
    name: "Torino",
    normalized_name: "torino",
    location_kind: "municipality",
    municipality_istat_code: "001272",
    postal_code: "10100",
    province_code: "TO",
    province_name: "Torino",
    region_name: "Piemonte",
    latitude: 45.07,
    longitude: 7.68,
    coordinate_status: "available",
  },
];

test("normalization ignores accents, apostrophes and case", () => {
  assert.equal(normalizeTerm("  CITTÀ d’Italia  "), "citta d italia");
});

test("formats Italian thousands deterministically", () => {
  assert.equal(formatInteger(14480), "14.480");
  assert.equal(formatInteger(7186), "7.186");
});

test("searches by name without requiring accents", () => {
  const result = searchLocations(rows, { query: "citta castello" });
  assert.equal(result.total, 1);
  assert.equal(result.rows[0].location_id, "IT-COM-001");
});

test("searches by postal code and province", () => {
  assert.equal(searchLocations(rows, { query: "00186" }).total, 1);
  assert.equal(searchLocations(rows, { query: "RM" }).rows[0].name, "Roma Centro");
  assert.equal(
    searchLocations(rows, { province: "TO" }).rows[0].name,
    "Torino",
  );
});

test("filters by kind and coordinate status", () => {
  const result = searchLocations(rows, {
    kind: "postal_locality_unclassified",
    coordinateStatus: "missing",
  });
  assert.equal(result.total, 1);
  assert.equal(result.rows[0].name, "Roma Centro");
});

test("projects the extrema inside the drawing area", () => {
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
