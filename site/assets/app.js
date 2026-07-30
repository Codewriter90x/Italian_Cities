import {
  filtersFromSearchParams,
  filtersToSearchParams,
  formatInteger,
  inflateRows,
  projectCoordinates,
  searchLocations,
} from "./core.mjs";

const state = {
  rows: [],
  mapRows: [],
  boundaries: null,
  stats: null,
  selected: null,
  loadPromise: null,
  filters: {
    query: "",
    province: "",
    kind: "",
    coordinateStatus: "",
  },
};

const elements = {
  status: document.querySelector("#load-status"),
  form: document.querySelector("#search-form"),
  query: document.querySelector("#query"),
  province: document.querySelector("#province"),
  kind: document.querySelector("#kind"),
  coordinateStatus: document.querySelector("#coordinate-status"),
  reset: document.querySelector("#reset-search"),
  copyFilterLink: document.querySelector("#copy-filter-link"),
  copyStatus: document.querySelector("#copy-status"),
  resultCount: document.querySelector("#result-count"),
  results: document.querySelector("#result-list"),
  canvas: document.querySelector("#coverage-map"),
  mapDetail: document.querySelector("#map-detail"),
  mapFallbackBody: document.querySelector("#map-fallback-body"),
};

function populateStats(stats) {
  const mapping = {
    total: formatInteger(stats.postal_code_relations),
    municipalities: formatInteger(stats.municipalities),
    postalCodes: formatInteger(stats.unique_postal_codes),
    coordinates: formatInteger(stats.with_coordinates),
  };
  for (const [name, value] of Object.entries(mapping)) {
    for (const target of document.querySelectorAll(`[data-stat="${name}"]`)) {
      target.textContent = value;
    }
  }
}

function populateProvinces(rows) {
  const currentProvinceCodes = new Set(
    rows
      .filter((row) => row.location_kind === "municipality")
      .map((row) => row.province_code),
  );
  const provinces = [
    ...new Map(
      rows.map((row) => [
        row.province_code,
        `${row.province_name} (${row.province_code})`,
      ]),
    ),
  ].sort((left, right) => left[1].localeCompare(right[1], "it"));

  for (const [code, label] of provinces) {
    const option = document.createElement("option");
    option.value = code;
    option.textContent = currentProvinceCodes.has(code)
      ? label
      : `${label} · sigla sorgente non corrente`;
    elements.province.append(option);
  }
}

function kindLabel(row) {
  if (row.location_kind === "municipality") return "Comune ISTAT";
  if (row.location_kind === "geonames_ambiguous") {
    return "Località GeoNames ambigua";
  }
  return "Località GeoNames non riconciliata";
}

function renderResults() {
  const result = searchLocations(state.rows, state.filters);
  elements.resultCount.textContent =
    result.total > result.rows.length
      ? `${formatInteger(result.total)} risultati · primi ${formatInteger(result.rows.length)} mostrati`
      : `${formatInteger(result.total)} risultati`;
  elements.results.replaceChildren();

  if (!result.rows.length) {
    const item = document.createElement("li");
    item.className = "empty-state";
    item.textContent =
      "Nessun risultato. Prova un nome più breve o rimuovi uno dei filtri.";
    elements.results.append(item);
    return;
  }

  const fragment = document.createDocumentFragment();
  for (const row of result.rows) {
    const item = document.createElement("li");
    const button = document.createElement("button");
    button.type = "button";
    button.className = "result-card";
    button.dataset.locationId = row.location_id;

    const heading = document.createElement("span");
    heading.className = "result-heading";
    heading.textContent = row.name;

    const cap = document.createElement("span");
    cap.className = "cap-badge";
    cap.textContent = row.postal_code || "CAP mancante";

    const location = document.createElement("span");
    location.className = "result-location";
    location.textContent = `${row.province_name} · ${row.region_name}`;

    const meta = document.createElement("span");
    meta.className = "result-meta";
    const coordinateText =
      row.latitude === null
        ? "coordinate mancanti"
        : row.coordinate_verification === "geonames_place_match"
          ? `coordinate GeoNames associate al luogo · accuracy ${row.coordinate_accuracy}`
          : `coordinate GeoNames stimate · accuracy ${row.coordinate_accuracy}`;
    const postalText =
      row.postal_code_status === "missing"
        ? "CAP non disponibile"
        : row.postal_code_status === "geonames_ambiguous"
          ? "CAP GeoNames con riconciliazione ambigua"
          : "CAP GeoNames non ufficiale";
    meta.textContent = `${kindLabel(row)} · ${postalText} · ${coordinateText}`;

    heading.append(cap);
    button.append(heading, location, meta);
    button.addEventListener("click", () => selectLocation(row));
    item.append(button);
    fragment.append(item);
  }
  elements.results.append(fragment);
}

function drawPolygon(context, coordinates, width, height, bounds) {
  context.beginPath();
  for (const ring of coordinates) {
    for (const [index, [longitude, latitude]] of ring.entries()) {
      const point = projectCoordinates(
        longitude,
        latitude,
        width,
        height,
        bounds,
        28,
      );
      if (index === 0) context.moveTo(point.x, point.y);
      else context.lineTo(point.x, point.y);
    }
    context.closePath();
  }
  context.fill("evenodd");
  context.stroke();
}

function drawBoundaries(context, width, height, bounds) {
  if (!state.boundaries) return;
  context.fillStyle = "rgba(18, 55, 70, 0.72)";
  context.strokeStyle = "rgba(151, 209, 222, 0.48)";
  context.lineWidth = 0.8;
  for (const feature of state.boundaries.features) {
    const geometry = feature.geometry;
    if (geometry.type === "Polygon") {
      drawPolygon(context, geometry.coordinates, width, height, bounds);
    } else if (geometry.type === "MultiPolygon") {
      for (const polygon of geometry.coordinates) {
        drawPolygon(context, polygon, width, height, bounds);
      }
    }
  }
}

function populateAccessibleMap(rows) {
  const regions = new Map();
  for (const row of rows) {
    const current = regions.get(row.region_name) ?? {
      total: 0,
      present: 0,
      missing: 0,
    };
    current.total += 1;
    if (row.latitude !== null) current.present += 1;
    else current.missing += 1;
    regions.set(row.region_name, current);
  }

  const fragment = document.createDocumentFragment();
  const names = [...regions.keys()].sort((left, right) =>
    left.localeCompare(right, "it"),
  );
  for (const name of names) {
    const values = regions.get(name);
    const row = document.createElement("tr");
    for (const value of [
      name,
      formatInteger(values.total),
      formatInteger(values.present),
      formatInteger(values.missing),
    ]) {
      const cell = document.createElement("td");
      cell.textContent = value;
      row.append(cell);
    }
    fragment.append(row);
  }
  elements.mapFallbackBody.replaceChildren(fragment);
}

function drawMap() {
  if (!state.stats) return;
  const canvas = elements.canvas;
  const rect = canvas.getBoundingClientRect();
  const ratio = Math.min(window.devicePixelRatio || 1, 2);
  canvas.width = Math.max(1, Math.round(rect.width * ratio));
  canvas.height = Math.max(1, Math.round(rect.height * ratio));

  const context = canvas.getContext("2d");
  context.scale(ratio, ratio);
  const width = rect.width;
  const height = rect.height;
  context.clearRect(0, 0, width, height);

  const gradient = context.createLinearGradient(0, 0, width, height);
  gradient.addColorStop(0, "#0a1d2c");
  gradient.addColorStop(1, "#07111b");
  context.fillStyle = gradient;
  context.fillRect(0, 0, width, height);

  const bounds = state.stats.bounds;
  drawBoundaries(context, width, height, bounds);
  for (const row of state.mapRows) {
    if (row.latitude === null || row.longitude === null) continue;
    const point = projectCoordinates(
      row.longitude,
      row.latitude,
      width,
      height,
      bounds,
      28,
    );
    context.fillStyle =
      row.location_kind === "municipality"
        ? "rgba(69, 215, 232, 0.68)"
        : "rgba(255, 122, 102, 0.36)";
    context.beginPath();
    context.arc(point.x, point.y, 1.35, 0, Math.PI * 2);
    context.fill();
  }

  if (
    state.selected &&
    state.selected.latitude !== null &&
    state.selected.longitude !== null
  ) {
    const point = projectCoordinates(
      state.selected.longitude,
      state.selected.latitude,
      width,
      height,
      bounds,
      28,
    );
    context.strokeStyle = "#f4f8fb";
    context.lineWidth = 2;
    context.fillStyle = "#ff7a66";
    context.beginPath();
    context.arc(point.x, point.y, 7, 0, Math.PI * 2);
    context.fill();
    context.stroke();
  }
}

function selectLocation(row) {
  state.selected = row;
  if (row.latitude === null) {
    elements.mapDetail.textContent =
      `${row.name} (${row.postal_code || "CAP mancante"}, ${row.province_code}): ` +
      "coordinate non disponibili.";
  } else {
    elements.mapDetail.textContent =
      `${row.name} (${row.postal_code}, ${row.province_code}) · ` +
      `${row.latitude.toFixed(5)}, ${row.longitude.toFixed(5)} · ` +
      `GeoNames accuracy ${row.coordinate_accuracy}`;
  }
  drawMap();
  elements.canvas.scrollIntoView({ behavior: "smooth", block: "center" });
}

function updateFilters() {
  state.filters = {
    query: elements.query.value,
    province: elements.province.value,
    kind: elements.kind.value,
    coordinateStatus: elements.coordinateStatus.value,
  };
  renderResults();
  const url = new URL(window.location.href);
  url.search = filtersToSearchParams(state.filters).toString();
  window.history.replaceState(null, "", url);
}

async function copyCurrentFilterLink() {
  const url = window.location.href;
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(url);
    } else {
      const temporary = document.createElement("textarea");
      temporary.value = url;
      temporary.setAttribute("readonly", "");
      temporary.style.position = "fixed";
      temporary.style.opacity = "0";
      document.body.append(temporary);
      temporary.select();
      if (!document.execCommand("copy")) {
        throw new Error("copy command unavailable");
      }
      temporary.remove();
    }
    elements.copyStatus.textContent = "Link dei filtri copiato.";
  } catch {
    elements.copyStatus.textContent =
      "Copia non disponibile: seleziona l’indirizzo dalla barra del browser.";
  }
}

function resetSearch() {
  elements.form.reset();
  state.selected = null;
  elements.mapDetail.textContent =
    "Seleziona un risultato per evidenziarlo sulla mappa.";
  updateFilters();
  drawMap();
  elements.query.focus();
}

function applyFiltersFromUrl() {
  state.filters = filtersFromSearchParams(window.location.search);
  elements.query.value = state.filters.query;
  elements.province.value = state.filters.province;
  elements.kind.value = state.filters.kind;
  elements.coordinateStatus.value = state.filters.coordinateStatus;
}

async function loadDataset() {
  try {
    const [response, boundaryResponse] = await Promise.all([
      fetch("./assets/locations.json"),
      fetch("./assets/italy-regions.geojson"),
    ]);
    if (!response.ok) throw new Error(`Dataset HTTP ${response.status}`);
    if (!boundaryResponse.ok) {
      throw new Error(`Geographic base HTTP ${boundaryResponse.status}`);
    }
    const [payload, boundaries] = await Promise.all([
      response.json(),
      boundaryResponse.json(),
    ]);
    state.rows = inflateRows(payload.fields, payload.rows);
    state.mapRows = [
      ...new Map(
        [...state.rows].reverse().map((row) => [row.location_id, row]),
      ).values(),
    ];
    state.stats = payload.stats;
    state.boundaries = boundaries;
    populateStats(payload.stats);
    populateProvinces(state.rows);
    populateAccessibleMap(state.rows);
    applyFiltersFromUrl();
    renderResults();
    drawMap();
    elements.status.textContent =
      `Dataset ${payload.metadata.release} caricato: ` +
      `${formatInteger(payload.stats.total_locations)} record.`;
    elements.status.dataset.state = "ready";
  } catch (error) {
    elements.status.textContent =
      "Impossibile caricare il dataset. Riprova tra qualche minuto.";
    elements.status.dataset.state = "error";
    console.error(error);
  }
}

function ensureDatasetLoaded() {
  if (!state.loadPromise) {
    elements.status.textContent = "Caricamento del dataset…";
    elements.status.dataset.state = "loading";
    state.loadPromise = loadDataset();
  }
  return state.loadPromise;
}

elements.form.addEventListener("input", updateFilters);
elements.form.addEventListener("focusin", ensureDatasetLoaded, { once: true });
elements.form.addEventListener("submit", (event) => event.preventDefault());
elements.reset.addEventListener("click", resetSearch);
elements.copyFilterLink.addEventListener("click", copyCurrentFilterLink);
window.addEventListener("resize", drawMap);
window.addEventListener("popstate", () => {
  applyFiltersFromUrl();
  renderResults();
});

if (window.location.search || ["#search", "#map"].includes(window.location.hash)) {
  ensureDatasetLoaded();
} else if ("IntersectionObserver" in window) {
  const observer = new IntersectionObserver(
    (entries) => {
      if (entries.some((entry) => entry.isIntersecting)) {
        observer.disconnect();
        ensureDatasetLoaded();
      }
    },
    { rootMargin: "240px" },
  );
  observer.observe(elements.form);
} else {
  ensureDatasetLoaded();
}
