const baseZoomFactor = 1.14;
const statePerPlanet = {};
let currentPlanet = null;
let zoomStepIndex = 0;
let scale = 1, offsetX = 0, offsetY = 0;

// A preview that does not exist yet is asked for again on this interval, so a planet
// still being rendered appears on its own instead of needing a manual refresh.
const IMAGE_RETRY_INTERVAL_MS = 8000;

/**
 * Adds a changing query parameter, so the browser really re-requests the image instead
 * of reusing the failed attempt. Only retries use it; first loads stay clean.
 */
function cacheBustedUrl(url) {
  return url + (url.includes("?") ? "&" : "?") + "retry=" + Date.now();
}

/**
 * Turns a raw planet id like "moon_of_iron" into a readable label.
 * Mod planets often use dashes or underscores, vanilla ones are single words.
 */
function prettifyPlanetName(planet) {
  return planet.replace(/[-_]+/g, " ").replace(/\b\p{L}/gu, (c) => c.toUpperCase());
}

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
    tab.textContent = prettifyPlanetName(planet);
    tab.title = planet;
    tab.addEventListener("click", () => switchPlanet(planet, previewSources, mapImage));
    tabContainer.appendChild(tab);
  });

  setupMapImageHandlers(mapImage);
  setupTabPaging(tabContainer);

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
  // Reused across rebuilds, so refreshing the planet list does not stack up fallbacks.
  let fallback = mapImage.parentElement.querySelector(".map-fallback");
  if (!fallback) {
    fallback = document.createElement("div");
    fallback.className = "map-fallback";
    fallback.textContent = "⏳ No preview yet for this planet - it will appear when it is ready.";
    fallback.style.cssText = "color: white; padding: 1em; text-align: center;";
    fallback.style.display = "none";
    mapImage.parentElement.appendChild(fallback);
  }

  mapImage.onerror = () => {
    mapImage.style.display = "none";
    fallback.style.display = "block";
    updateSpawnMarker(mapImage);
    scheduleMapImageRetry(mapImage);
  };
  mapImage.onload = () => {
    mapImage.style.display = "block";
    fallback.style.display = "none";
  };
}

let pendingMapImageRetry = null;

/**
 * Asks for the current planet's preview again a little later. Generation takes about
 * half a minute per planet, and the planet list is written before the images exist, so
 * a tab is often opened before its image is there.
 */
function scheduleMapImageRetry(mapImage) {
  if (pendingMapImageRetry !== null) clearTimeout(pendingMapImageRetry);

  const plannedUrl = mapImage.dataset.plannedUrl;
  pendingMapImageRetry = window.setTimeout(() => {
    pendingMapImageRetry = null;
    // Only if the user is still looking at the same planet and it is still missing.
    if (!plannedUrl || mapImage.dataset.plannedUrl !== plannedUrl) return;
    if (mapImage.naturalWidth > 0) return;
    mapImage.src = cacheBustedUrl(plannedUrl);
  }, IMAGE_RETRY_INTERVAL_MS);
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

/**
 * Pages the tab strip with the ‹ › buttons instead of wrapping it onto more
 * rows, so a modpack's worth of planets does not eat the map's height.
 * A page ends at a whole tab, never mid-tab.
 */
let tabPagingWired = false;

function setupTabPaging(tabContainer) {
  const prevButton = document.getElementById("tabPrev");
  const nextButton = document.getElementById("tabNext");
  if (!prevButton || !nextButton) return;

  const updateButtons = () => {
    const overflowing = tabContainer.scrollWidth > tabContainer.clientWidth + 1;
    prevButton.style.display = overflowing ? "" : "none";
    nextButton.style.display = overflowing ? "" : "none";
    prevButton.disabled = tabContainer.scrollLeft <= 1;
    nextButton.disabled =
      tabContainer.scrollLeft + tabContainer.clientWidth >= tabContainer.scrollWidth - 1;
  };

  const page = (direction) => {
    const tabs = Array.from(tabContainer.querySelectorAll(".tab"));
    if (tabs.length === 0) return;

    let left;
    if (direction > 0) {
      const rightEdge = tabContainer.scrollLeft + tabContainer.clientWidth;
      const firstCutOff = tabs.find((tab) => tab.offsetLeft + tab.offsetWidth > rightEdge + 1);
      left = firstCutOff ? firstCutOff.offsetLeft : tabContainer.scrollWidth;
    } else {
      const wanted = tabContainer.scrollLeft - tabContainer.clientWidth;
      const before = tabs.filter((tab) => tab.offsetLeft <= wanted);
      left = before.length ? before[before.length - 1].offsetLeft : 0;
    }
    tabContainer.scrollTo({ left: Math.max(0, left), behavior: "smooth" });
  };

  // The buttons survive a rebuild, so they must only be wired up once.
  if (!tabPagingWired) {
    prevButton.addEventListener("click", () => page(-1));
    nextButton.addEventListener("click", () => page(1));
    tabContainer.addEventListener("scroll", updateButtons);
    window.addEventListener("resize", updateButtons);
    tabPagingWired = true;
  }
  updateButtons();
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
  if (newTab) {
    newTab.classList.add("active");
    // The strip only shows one page at a time, so keep the active tab on screen.
    newTab.scrollIntoView({ block: "nearest", inline: "nearest" });
  }

  const targetUrl = previewSources[planet];
  const needLoad = mapImage.dataset.plannedUrl !== targetUrl;
  currentPlanet = planet;
  mapImage.dataset.plannedUrl = targetUrl;

  if (needLoad) {
    mapImage.src = targetUrl; // triggers the load handler -> handleImageLoad
  } else {
    // Image is already loaded (e.g. reopening Nauvis): no load event will
    // fire, so recompute the layout now that the container is visible.
    handleImageLoad(mapImage, mapContainer, zoomDisplay);
  }
}

/**
 * Draws the red spawn cross on the map center, which is map position (0, 0) -
 * every preview is rendered around it, so that is where the player spawns.
 * The marker keeps a constant screen size, so it stays usable at any zoom level.
 */
function updateSpawnMarker(mapImage) {
  const marker = document.getElementById("spawnMarker");
  if (!marker) return;

  const imgW = mapImage.naturalWidth;
  const imgH = mapImage.naturalHeight;
  if (!imgW || !imgH || mapImage.style.display === "none") {
    marker.style.display = "none";
    return;
  }

  const x = offsetX + (imgW * scale) / 2;
  const y = offsetY + (imgH * scale) / 2;
  marker.style.display = "block";
  marker.style.transform = `translate(${x}px, ${y}px)`;
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
  updateSpawnMarker(target);
}

function updateZoomLabel(label) {
  label.textContent = `Zoom: ${Math.round(getScaleFromStep(zoomStepIndex) * 100)}%`;
}
