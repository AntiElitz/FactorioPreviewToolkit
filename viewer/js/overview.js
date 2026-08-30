/**
 * Builds the composite "Overview" layout: one large planet on the left
 * (~2/3 width) and the remaining planets stacked top-to-bottom on the
 * right (~1/3 width). Each cell is an independent pan/zoom viewport.
 *
 * The main planet opens at the planet-tab setting (100%, native pixels) so it
 * matches its own tab. The side planets open at their configured zoom
 * (viewerConfig.defaultZoom) relative to a "fill the cell" baseline.
 *
 * The side column keeps a fixed cell height and scrolls, so a modpack that adds
 * dozens of planets stays readable instead of being squashed into four slots.
 */
const OVERVIEW_MAX_ZOOM_FACTOR = 16; // how far past "fill" a cell may be zoomed
let overviewCells = [];
let overviewAutoScrollTimer = null;
// Bumped on every rebuild, so timers belonging to discarded cells stop themselves.
let overviewGeneration = 0;

/**
 * Picks the main planet and the side planets. Both can be pinned in
 * viewerConfig.overview; otherwise the planet list decides, which is what makes
 * this work for mod planets without any configuration.
 */
function resolveOverviewPlanets(previewSources) {
  const cfg = viewerConfig.overview || {};
  const planets = Object.keys(previewSources);

  const main = cfg.main && previewSources[cfg.main] ? cfg.main : planets[0];
  const preferred = cfg.side && cfg.side.length ? cfg.side : planets;
  const side = preferred.filter((planet) => planet !== main && previewSources[planet]);

  return { main, side };
}

function buildOverview(previewSources, overviewEl) {
  const cfg = viewerConfig.overview || {};
  const { main, side } = resolveOverviewPlanets(previewSources);

  // Skip the overview entirely when it would only contain the main planet
  // (e.g. vanilla / non-Space-Age maps that expose just Nauvis).
  if (!main || side.length === 0) {
    return false;
  }

  overviewEl.innerHTML = "";
  overviewCells = [];
  overviewGeneration += 1;

  overviewEl.appendChild(makeOverviewCell(main, previewSources[main], "overview-main", "native"));

  const sideEl = document.createElement("div");
  sideEl.className = "overview-side";
  sideEl.style.setProperty("--visible-side-cells", String(cfg.visibleSideCells || 4));
  side.forEach((planet) => {
    sideEl.appendChild(makeOverviewCell(planet, previewSources[planet], "overview-cell", "fill"));
  });
  overviewEl.appendChild(sideEl);

  startOverviewAutoScroll(sideEl, cfg);
  return true;
}

/**
 * (Re)initializes every overview cell's default view. Called when the
 * overview becomes visible and on resize. Cells keep the user's zoom/pan
 * across tab switches; `force` re-centers them (used on resize).
 */
function initOverviewCells(force) {
  overviewCells.forEach((cell) => cell.init(force));
}

window.addEventListener("resize", () => initOverviewCells(true));

function makeOverviewCell(planet, url, className, baseMode) {
  const zoomMultiplier = getZoomMultiplier(planet);
  const generation = overviewGeneration;

  const cell = document.createElement("div");
  cell.className = className;

  const img = document.createElement("img");
  img.alt = planet;
  img.draggable = false;
  // Offscreen cells must not be decoded: one 2048px preview costs ~16 MB of
  // bitmap, so a 40 planet modpack would otherwise need gigabytes.
  img.loading = "lazy";

  const marker = document.createElement("div");
  marker.className = "spawn-marker";
  marker.style.display = "none";

  const label = document.createElement("span");
  label.className = "overview-label";
  label.textContent = prettifyPlanetName(planet);

  cell.appendChild(img);
  cell.appendChild(marker);
  cell.appendChild(label);

  const state = { scale: 1, x: 0, y: 0, cover: 1, cw: 0, ch: 0, loaded: false, ready: false };

  const apply = () => {
    img.style.transform = `translate(${state.x}px, ${state.y}px) scale(${state.scale})`;
    if (state.loaded) {
      const centerX = state.x + (img.naturalWidth * state.scale) / 2;
      const centerY = state.y + (img.naturalHeight * state.scale) / 2;
      marker.style.transform = `translate(${centerX}px, ${centerY}px)`;
      marker.style.display = "block";
    }
  };

  // Keep the image covering the cell so no dead space appears.
  const clamp = () => {
    const iw = img.naturalWidth * state.scale;
    const ih = img.naturalHeight * state.scale;
    state.x = Math.min(0, Math.max(state.cw - iw, state.x));
    state.y = Math.min(0, Math.max(state.ch - ih, state.y));
  };

  const init = (force) => {
    const w = cell.clientWidth;
    const h = cell.clientHeight;
    if (!state.loaded || w === 0 || h === 0) return;
    if (state.ready && !force && w === state.cw && h === state.ch) return;

    state.cw = w;
    state.ch = h;
    state.cover = Math.max(w / img.naturalWidth, h / img.naturalHeight);
    // "native" mirrors the planet tab (100%, native pixels); "fill" fills the
    // cell and applies the planet's configured zoom multiplier.
    state.scale = baseMode === "native" ? 1 : state.cover * zoomMultiplier;
    state.x = (w - img.naturalWidth * state.scale) / 2;
    state.y = (h - img.naturalHeight * state.scale) / 2;
    clamp();
    apply();
    state.ready = true;
  };

  img.addEventListener("load", () => {
    state.loaded = true;
    label.textContent = prettifyPlanetName(planet);
    init(true);
  });
  img.addEventListener("error", () => {
    marker.style.display = "none";
    label.textContent = `${prettifyPlanetName(planet)} — waiting for preview`;
    // Keep asking: this planet is probably still being rendered.
    window.setTimeout(() => {
      if (generation !== overviewGeneration) return; // this cell was replaced
      if (!state.loaded) img.src = cacheBustedUrl(url);
    }, IMAGE_RETRY_INTERVAL_MS);
  });
  img.src = url;

  cell.addEventListener(
    "wheel",
    (e) => {
      if (!state.ready) return;
      e.preventDefault();
      const rect = cell.getBoundingClientRect();
      const px = e.clientX - rect.left;
      const py = e.clientY - rect.top;
      const mx = (px - state.x) / state.scale;
      const my = (py - state.y) / state.scale;

      const factor = e.deltaY < 0 ? 1.14 : 1 / 1.14;
      const min = state.cover;
      const max = state.cover * OVERVIEW_MAX_ZOOM_FACTOR;
      const ns = Math.min(max, Math.max(min, state.scale * factor));

      state.x = px - mx * ns;
      state.y = py - my * ns;
      state.scale = ns;
      clamp();
      apply();
    },
    { passive: false }
  );

  let dragging = false;
  let sx = 0;
  let sy = 0;
  cell.addEventListener("pointerdown", (e) => {
    if (!state.ready) return;
    dragging = true;
    sx = e.clientX - state.x;
    sy = e.clientY - state.y;
    cell.setPointerCapture(e.pointerId);
    cell.style.cursor = "grabbing";
  });
  cell.addEventListener("pointermove", (e) => {
    if (!dragging) return;
    state.x = e.clientX - sx;
    state.y = e.clientY - sy;
    clamp();
    apply();
  });
  const endDrag = () => {
    dragging = false;
    cell.style.cursor = "grab";
  };
  cell.addEventListener("pointerup", endDrag);
  cell.addEventListener("pointercancel", endDrag);

  overviewCells.push({ init });
  return cell;
}

/**
 * Scrolls the side column one cell further every few seconds, so an audience
 * sees every planet without anyone touching the page. Pauses while the pointer
 * is over the column - which also covers reaching for the scrollbar - and wraps
 * around at the end.
 */
function stopOverviewAutoScroll() {
  if (overviewAutoScrollTimer !== null) {
    clearInterval(overviewAutoScrollTimer);
    overviewAutoScrollTimer = null;
  }
}

function startOverviewAutoScroll(sideEl, cfg) {
  stopOverviewAutoScroll();
  const seconds = cfg.autoScrollSeconds;
  if (!seconds) return;

  let paused = false;
  sideEl.addEventListener("pointerenter", () => (paused = true));
  sideEl.addEventListener("pointerleave", () => (paused = false));

  overviewAutoScrollTimer = window.setInterval(() => {
    // Skip while hidden (a planet tab is open) or while the user is inspecting.
    if (paused || sideEl.offsetParent === null) return;
    if (sideEl.scrollHeight <= sideEl.clientHeight) return;

    const first = sideEl.firstElementChild;
    const step = first ? first.offsetHeight + 4 : sideEl.clientHeight;
    const atEnd = sideEl.scrollTop + sideEl.clientHeight >= sideEl.scrollHeight - 2;
    sideEl.scrollTo({ top: atEnd ? 0 : sideEl.scrollTop + step, behavior: "smooth" });
  }, seconds * 1000);
}
