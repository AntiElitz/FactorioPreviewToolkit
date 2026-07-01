const baseZoomFactor = 1.14;
const statePerPlanet = {};
let currentPlanet = null;
let zoomStepIndex = 0;
let scale = 1, offsetX = 0, offsetY = 0;

/**
 * Zoom multiplier for an overview side cell, relative to its "fill the cell"
 * baseline. Read from viewerConfig.defaultZoom; a missing entry means 1x.
 * (Planet tabs are left at the upstream default and don't use this.)
 */
function getZoomMultiplier(planet) {
  const cfg = viewerConfig.defaultZoom || {};
  const value = planet in cfg ? cfg[planet] : cfg.default;
  if (value === undefined || value === "fit") return 1;
  return value;
}

/**
 * Persists the current pan/zoom for the active planet, but only when it is
 * actually being displayed (a visible, loaded image). This avoids caching a
 * bogus layout computed while the single-map view was hidden behind the
 * overview.
 */
function saveCurrentState(mapImage) {
  const container = mapImage.parentElement;
  const visible = container && container.offsetParent !== null;
  if (currentPlanet && visible && mapImage.complete && mapImage.naturalWidth > 0) {
    statePerPlanet[currentPlanet] = { zoomStepIndex, offsetX, offsetY };
  }
}

function setupTabs(previewSources, tabContainer, mapImage) {
  const overviewEl = document.getElementById("overviewContainer");
  const hasOverview = overviewEl && buildOverview(previewSources, overviewEl);

  if (hasOverview) {
    const overviewTab = document.createElement("div");
    overviewTab.className = "tab";
    overviewTab.dataset.view = "overview";
    overviewTab.textContent = "Overview";
    overviewTab.addEventListener("click", () => activateOverview(mapImage));
    tabContainer.appendChild(overviewTab);
  }

  const planetKeys = Object.keys(previewSources);
  planetKeys.forEach((planet) => {
    const tab = document.createElement("div");
    tab.className = "tab";
    tab.dataset.planet = planet;
    tab.textContent = planet.charAt(0).toUpperCase() + planet.slice(1);
    tab.addEventListener("click", () => switchPlanet(planet, previewSources, mapImage));
    tabContainer.appendChild(tab);
  });

  setupMapImageHandlers(mapImage);

  // Select the configured default tab. Loading of the single-map image is
  // deferred until a planet tab is actually opened (see switchPlanet) so it
  // never lays out against a hidden, zero-size container.
  const target = resolveDefaultTab(hasOverview, planetKeys);
  if (target === "overview") {
    activateOverview(mapImage);
  } else if (target) {
    switchPlanet(target, previewSources, mapImage);
  }
}

/**
 * Sets up the single-map <img> load/error handling and its "no preview"
 * fallback, once, independent of which tab is shown first.
 */
function setupMapImageHandlers(mapImage) {
  const fallback = document.createElement("div");
  fallback.textContent = "🚫 No preview available yet for this planet.";
  fallback.style.cssText = "color: white; padding: 1em; text-align: center;";
  fallback.style.display = "none";
  mapImage.parentElement.appendChild(fallback);

  mapImage.onerror = () => {
    console.error("Failed to load map image:", mapImage.src);
    mapImage.style.display = "none";
    fallback.style.display = "block";
  };
  mapImage.onload = () => {
    mapImage.style.display = "block";
    fallback.style.display = "none";
  };
}

/**
 * Resolves viewerConfig.defaultTab to an actual target ("overview" or a
 * planet name), falling back to the overview (or first planet) when the
 * requested tab isn't available.
 */
function resolveDefaultTab(hasOverview, planetKeys) {
  const fallback = hasOverview ? "overview" : (planetKeys[0] || null);
  const pref = viewerConfig.defaultTab || "auto";
  if (pref === "auto" || pref === "overview") return fallback;
  return planetKeys.includes(pref) ? pref : fallback;
}

function setViewControlsVisible(visible) {
  const display = visible ? "" : "none";
  const zoomDisplay = document.getElementById("zoomDisplay");
  const resetBtn = document.getElementById("resetView");
  if (zoomDisplay) zoomDisplay.style.display = display;
  if (resetBtn) resetBtn.style.display = display;
}

function activateOverview(mapImage) {
  saveCurrentState(mapImage);

  document.querySelectorAll(".tab").forEach(tab => tab.classList.remove("active"));
  const overviewTab = document.querySelector('.tab[data-view="overview"]');
  if (overviewTab) overviewTab.classList.add("active");

  mapImage.parentElement.style.display = "none";
  const overviewEl = document.getElementById("overviewContainer");
  if (overviewEl) overviewEl.style.display = "grid";
  setViewControlsVisible(false);

  // Cells need their size to lay out; they were hidden until now.
  initOverviewCells(false);
}

function switchPlanet(planet, previewSources, mapImage) {
  saveCurrentState(mapImage);

  const overviewEl = document.getElementById("overviewContainer");
  if (overviewEl) overviewEl.style.display = "none";
  mapImage.parentElement.style.display = "";
  setViewControlsVisible(true);

  document.querySelectorAll(".tab").forEach(tab => tab.classList.remove("active"));
  const newTab = document.querySelector(`.tab[data-planet="${planet}"]`);
  if (newTab) newTab.classList.add("active");

  const targetUrl = previewSources[planet];
  const needLoad = mapImage.getAttribute("src") !== targetUrl;
  currentPlanet = planet;

  if (needLoad) {
    mapImage.src = targetUrl; // triggers the load handler -> handleImageLoad
  } else {
    // Image is already loaded (e.g. reopening Nauvis): no load event will
    // fire, so recompute the layout now that the container is visible.
    handleImageLoad(mapImage, mapContainer, zoomDisplay);
  }
}

function handleImageLoad(mapImage, container, zoomDisplay) {
  const rect = container.getBoundingClientRect();
  const imgW = mapImage.naturalWidth;
  const imgH = mapImage.naturalHeight;

  if (statePerPlanet[currentPlanet]) {
    ({ zoomStepIndex, offsetX, offsetY } = statePerPlanet[currentPlanet]);
    scale = getScaleFromStep(zoomStepIndex);
  } else {
    zoomStepIndex = 0;
    scale = getScaleFromStep(zoomStepIndex);
    offsetX = (rect.width - imgW * scale) / 2;
    offsetY = (rect.height - imgH * scale) / 2;
  }

  updateTransform(mapImage);
  updateZoomLabel(zoomDisplay);
}

function handleWheelZoom(e, mapImage, container, zoomDisplay) {
  e.preventDefault();
  const rect = container.getBoundingClientRect();
  const mouseX = (e.clientX - rect.left - offsetX) / scale;
  const mouseY = (e.clientY - rect.top - offsetY) / scale;

  zoomStepIndex += e.deltaY < 0 ? 1 : -1;
  const newScale = getScaleFromStep(zoomStepIndex);

  offsetX -= mouseX * (newScale - scale);
  offsetY -= mouseY * (newScale - scale);
  scale = newScale;

  updateTransform(mapImage);
  updateZoomLabel(zoomDisplay);
}

function resetMapView(mapImage, container, zoomDisplay) {
  const rect = container.getBoundingClientRect();
  const imgW = mapImage.naturalWidth;
  const imgH = mapImage.naturalHeight;

  zoomStepIndex = 0;
  scale = getScaleFromStep(zoomStepIndex);
  offsetX = (rect.width - imgW * scale) / 2;
  offsetY = (rect.height - imgH * scale) / 2;

  updateTransform(mapImage);
  updateZoomLabel(zoomDisplay);
}

function getScaleFromStep(step) {
  return Math.pow(baseZoomFactor, step);
}

function updateTransform(target) {
  target.style.transform = `translate(${offsetX}px, ${offsetY}px) scale(${scale})`;
}

function updateZoomLabel(label) {
  label.textContent = `Zoom: ${Math.round(getScaleFromStep(zoomStepIndex) * 100)}%`;
}
