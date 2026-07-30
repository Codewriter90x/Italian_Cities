const COLLATOR = new Intl.Collator("it", {
  sensitivity: "base",
  numeric: true,
});

export function normalizeTerm(value = "") {
  return String(value)
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .replace(/[’']/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .toLowerCase();
}

function searchableText(row) {
  return normalizeTerm(
    [
      row.name,
      row.normalized_name,
      row.postal_code,
      row.province_code,
      row.province_name,
      row.region_name,
      row.municipality_istat_code,
    ].join(" "),
  );
}

function relevance(row, normalizedQuery) {
  if (!normalizedQuery) return row.location_kind === "municipality" ? 2 : 3;
  const normalizedName = normalizeTerm(row.name);
  const provinceCode = normalizeTerm(row.province_code);
  const postalCode = normalizeTerm(row.postal_code);

  if (postalCode === normalizedQuery) return 0;
  if (normalizedName === normalizedQuery) return 0;
  if (normalizedName.startsWith(normalizedQuery)) return 1;
  if (provinceCode === normalizedQuery) return 1;
  return 2;
}

export function searchLocations(
  rows,
  {
    query = "",
    province = "",
    kind = "",
    coordinateStatus = "",
    limit = 60,
  } = {},
) {
  const normalizedQuery = normalizeTerm(query);
  const tokens = normalizedQuery.split(" ").filter(Boolean);
  const exactPostalCodeQuery = /^\d{5}$/.test(normalizedQuery);

  const matches = rows.filter((row) => {
    if (province && row.province_code !== province) return false;
    if (kind && row.location_kind !== kind) return false;
    if (coordinateStatus === "present" && row.latitude === null) return false;
    if (coordinateStatus === "missing" && row.latitude !== null) return false;
    if (
      coordinateStatus === "legacy_unverified" &&
      !["legacy_unverified", "corrected_legacy_unverified"].includes(
        row.coordinate_verification,
      )
    ) {
      return false;
    }
    if (
      coordinateStatus === "verified" &&
      ["missing", "legacy_unverified", "corrected_legacy_unverified"].includes(
        row.coordinate_verification,
      )
    ) {
      return false;
    }
    if (!tokens.length) return true;
    if (exactPostalCodeQuery) return row.postal_code === normalizedQuery;
    const haystack = searchableText(row);
    return tokens.every((token) => haystack.includes(token));
  });

  matches.sort((left, right) => {
    const scoreDifference =
      relevance(left, normalizedQuery) - relevance(right, normalizedQuery);
    if (scoreDifference) return scoreDifference;
    const nameDifference = COLLATOR.compare(left.name, right.name);
    if (nameDifference) return nameDifference;
    const provinceDifference = COLLATOR.compare(
      left.province_code,
      right.province_code,
    );
    if (provinceDifference) return provinceDifference;
    return COLLATOR.compare(left.postal_code, right.postal_code);
  });

  return {
    total: matches.length,
    rows: matches.slice(0, limit),
  };
}

export function projectCoordinates(
  longitude,
  latitude,
  width,
  height,
  bounds,
  padding = 24,
) {
  const usableWidth = Math.max(1, width - padding * 2);
  const usableHeight = Math.max(1, height - padding * 2);
  const x =
    padding +
    ((longitude - bounds.min_longitude) /
      (bounds.max_longitude - bounds.min_longitude)) *
      usableWidth;
  const y =
    padding +
    ((bounds.max_latitude - latitude) /
      (bounds.max_latitude - bounds.min_latitude)) *
      usableHeight;
  return { x, y };
}

export function formatInteger(value) {
  return String(Math.trunc(value)).replace(/\B(?=(\d{3})+(?!\d))/g, ".");
}

export function formatPercent(value) {
  return new Intl.NumberFormat("it-IT", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}
