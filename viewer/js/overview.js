/**
 * Builds the composite "Overview" layout: one large planet on the left
 * (~2/3 width) and the remaining planets stacked top-to-bottom on the
 * right (~1/3 width). Each cell is an independent pan/zoom viewport.
 *
 * The main planet (Nauvis) opens at the upstream planet-tab setting (100%,
 * native pixels) so it matches its own tab. The side planets open at their
 * configured zoom (viewerConfig.defaultZoom) relative to a "fill the cell"
 * baseline.
 */
const OVERVIEW_MAX_ZOOM_FACTOR = 16; // how far past "fill" a cell may be zoomed
let overviewCells = [];

function buildOverview(previewSources, overviewEl) {
  const cfg = viewerConfig.overview;
  const availableSide = ((cfg && cfg.side) || []).filter((planet) => previewSources[planet]);

  // Skip the overview entirely when it would only contain the main planet
  // (e.g. vanilla / non-Space-Age maps that expose just Nauvis).
  if (!cfg || !cfg.main || !previewSources[cfg.main] || availableSide.length === 0) {
    return false;
  }

  overviewEl.innerHTML = "";
  overviewCells = [];

  overviewEl.appendChild(makeOverviewCell(cfg.main, previewSources[cfg.main], "overview-main", "native"));

  const side = document.createElement("div");
  side.className = "overview-side";
  availableSide.forEach((planet) => {
    side.appendChild(makeOverviewCell(planet, previewSources[planet], "overview-cell", "fill"));
  });
  overviewEl.appendChild(side);
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

  const cell = document.createElement("div");
  cell.className = className;

  const img = document.createElement("img");
  img.alt = planet;
  img.draggable = false;

  const label = document.createElement("span");
  label.className = "overview-label";
  label.textContent = planet.charAt(0).toUpperCase() + planet.slice(1);

  cell.appendChild(img);
  cell.appendChild(label);

  const state = { scale: 1, x: 0, y: 0, cover: 1, cw: 0, ch: 0, loaded: false, ready: false };

  const apply = () => {
    img.style.transform = `translate(${state.x}px, ${state.y}px) scale(${state.scale})`;
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
    // "native" mirrors the upstream planet tab (100%, native pixels); "fill"
    // fills the cell and applies the planet's configured zoom multiplier.
    state.scale = baseMode === "native" ? 1 : state.cover * zoomMultiplier;
    state.x = (w - img.naturalWidth * state.scale) / 2;
    state.y = (h - img.naturalHeight * state.scale) / 2;
    clamp();
    apply();
    state.ready = true;
  };

  img.addEventListener("load", () => {
    state.loaded = true;
    init(true);
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
