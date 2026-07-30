import {
  formatInteger,
  formatPercent,
  projectCoordinates,
  searchLocations,
} from "./core.mjs";

const state = {
  rows: [],
  stats: null,
  selected: null,
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
  resultCount: document.querySelector("#result-count"),
  results: document.querySelector("#result-list"),
  canvas: document.querySelector("#coverage-map"),
  mapDetail: document.querySelector("#map-detail"),
};

function populateStats(stats) {
  const mapping = {
    total: formatInteger(stats.total_locations),
    municipalities: formatInteger(stats.municipalities),
    postalCodes: formatInteger(stats.unique_postal_codes),
    coordinates: `${formatPercent(stats.coordinate_coverage_percent)}%`,
  };
  for (const [name, value] of Object.entries(mapping)) {
    for (const target of document.querySelectorAll(`[data-stat="${name}"]`)) {
      target.textContent = value;
    }
  }
}

function populateProvinces(rows) {
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
    option.textContent = label;
    elements.province.append(option);
  }
}

function kindLabel(row) {
  return row.location_kind === "municipality"
    ? "Comune ISTAT"
    : "Località non classificata";
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
    cap.textContent = row.postal_code;

    const location = document.createElement("span");
    location.className = "result-location";
    location.textContent = `${row.province_name} · ${row.region_name}`;

    const meta = document.createElement("span");
    meta.className = "result-meta";
    const coordinateText =
      row.latitude === null
        ? "coordinate mancanti"
        : row.coordinate_verification === "legacy_unverified"
          ? "coordinate legacy non verificate"
          : row.coordinate_verification === "corrected_legacy_unverified"
            ? "coordinate corrette ma non verificate"
            : "coordinate verificate";
    const postalText =
      row.postal_code_status === "generic_multicap"
        ? "CAP generico città multi-CAP"
        : row.postal_code_status === "legacy_unverified"
          ? "CAP legacy non verificato"
          : `CAP ${row.postal_code_status}`;
    meta.textContent = `${kindLabel(row)} · ${postalText} · ${coordinateText}`;

    heading.append(cap);
    button.append(heading, location, meta);
    button.addEventListener("click", () => selectLocation(row));
    item.append(button);
    fragment.append(item);
  }
  elements.results.append(fragment);
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

  context.strokeStyle = "rgba(129, 185, 204, 0.10)";
  context.lineWidth = 1;
  for (let index = 1; index < 8; index += 1) {
    const x = (width / 8) * index;
    const y = (height / 8) * index;
    context.beginPath();
    context.moveTo(x, 0);
    context.lineTo(x, height);
    context.stroke();
    context.beginPath();
    context.moveTo(0, y);
    context.lineTo(width, y);
    context.stroke();
  }

  const bounds = state.stats.bounds;
  for (const row of state.rows) {
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
      `${row.name} (${row.postal_code}, ${row.province_code}): ` +
      "coordinate non disponibili.";
  } else {
    elements.mapDetail.textContent =
      `${row.name} (${row.postal_code}, ${row.province_code}) · ` +
      `${row.latitude.toFixed(5)}, ${row.longitude.toFixed(5)}`;
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

async function loadDataset() {
  try {
    const response = await fetch("./assets/locations.json");
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const payload = await response.json();
    state.rows = payload.rows;
    state.stats = payload.stats;
    populateStats(payload.stats);
    populateProvinces(payload.rows);
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

elements.form.addEventListener("input", updateFilters);
elements.form.addEventListener("submit", (event) => event.preventDefault());
elements.reset.addEventListener("click", resetSearch);
window.addEventListener("resize", drawMap);

loadDataset();
