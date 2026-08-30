const tabButtonsContainer = document.querySelector(".tab-buttons");
const mapImage = document.getElementById("mapImage");
const mapContainer = document.getElementById("mapContainer");
const zoomDisplay = document.getElementById("zoomDisplay");
const resetBtn = document.getElementById("resetView");

/**
 * Loads the planet list, either as a <script> defining window.planetNames (local
 * viewer, because fetch() is blocked on file:// URLs) or as JSON (hosted viewer).
 * Returns the planet names plus the time the list was written, which versions the
 * image URLs. `bustCache` forces a fresh read, used when polling for a new run.
 */
function loadPlanetList(src, bustCache) {
  const url = bustCache ? `${src}${src.includes("?") ? "&" : "?"}t=${Date.now()}` : src;

  if (location.protocol === "file:" || src.endsWith(".js")) {
    return new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = url;
      script.onload = () => {
        script.remove();
        // Older lists were written as 'const planetNames', which does not become a
        // window property - read either form so an existing file keeps working.
        const names =
          typeof window.planetNames !== "undefined"
            ? window.planetNames
            : typeof planetNames !== "undefined"
              ? planetNames
              : undefined;
        const time =
          typeof window.planetNamesUploadTime !== "undefined"
            ? window.planetNamesUploadTime
            : typeof planetNamesUploadTime !== "undefined"
              ? planetNamesUploadTime
              : "";
        const mapString =
          typeof window.mapExchangeString !== "undefined" ? window.mapExchangeString : "";
        // An older list declares 'const planetNames', which cannot be re-declared, so
        // re-reading it can never see a new run. Flag it instead of failing quietly.
        const rereadable = typeof window.planetNames !== "undefined";
        if (names !== undefined) {
          resolve({ planets: names, time: time || "", mapString: mapString, rereadable });
        } else {
          reject(new Error("planetNames is not defined after loading script."));
        }
      };
      script.onerror = () => {
        script.remove();
        reject(new Error("Failed to load planetNames script."));
      };
      document.head.appendChild(script);
    });
  }

  return fetch(url, { cache: "no-store" })
    .then((res) => {
      if (!res.ok) throw new Error(`Failed to fetch JSON (${res.status})`);
      return res.json();
    })
    .then((data) => {
      if (!Array.isArray(data.planets)) {
        throw new Error("Invalid JSON format: expected a 'planets' array.");
      }
      return {
        planets: data.planets,
        time: data.time || "",
        mapString: data.map_string || "",
        rereadable: true,
      };
    });
}

/**
 * Builds the preview image source for every reported planet.
 * Explicit entries in `planetPreviewSources` win (used by the uploaded remote config),
 * everything else falls back to `planetPreviewSourceTemplate`. Planets added by mods
 * therefore work without touching the viewer config.
 */
function buildPreviewSources(planetNames, version) {
  const explicitSources = viewerConfig.planetPreviewSources || {};
  const template = viewerConfig.planetPreviewSourceTemplate;
  const sources = {};

  // The image file names never change, so a browser will happily keep showing the
  // previous run's map. Stamping the URL with the time the planet list was written
  // makes every new run a new URL, while a reload within the same run still hits
  // the cache.
  const stamp = version ? `v=${encodeURIComponent(version)}` : "";

  planetNames.forEach((planet) => {
    let url;
    if (explicitSources[planet]) {
      url = explicitSources[planet];
    } else if (template) {
      url = template.replace("{planet}", encodeURIComponent(planet));
    } else {
      console.warn(`⚠️ No preview source configured for planet '${planet}'.`);
      return;
    }
    sources[planet] = stamp ? `${url}${url.includes("?") ? "&" : "?"}${stamp}` : url;
  });

  return sources;
}

let shownPlanetListTime = null;

/**
 * Builds (or rebuilds) the tabs and views for a planet list.
 */
function showPlanetList(planets, time, mapString) {
  shownPlanetListTime = time;
  clearViewerUi();
  setupTabs(buildPreviewSources(planets, time), tabButtonsContainer, mapImage);
  updateCopyMapStringButton(mapString);
}

/**
 * Shows the "Copy map string" button when there is a string to copy, so anyone watching
 * can paste it into Factorio and generate the exact same map.
 */
function updateCopyMapStringButton(mapString) {
  const button = document.getElementById("copyMapString");
  if (!button) return;

  const enabled = viewerConfig.showCopyMapStringButton !== false;
  if (!enabled || !mapString) {
    button.style.display = "none";
    return;
  }

  button.style.display = "";
  button.onclick = () => {
    copyToClipboard(mapString)
      .then(() => flashButton(button, "Copied!"))
      .catch(() => flashButton(button, "Press Ctrl+C"));
  };
}

/**
 * Copies text to the clipboard. The modern API needs a secure context, which a page
 * opened straight from disk is not always considered, so fall back to a hidden textarea.
 */
function copyToClipboard(text) {
  if (navigator.clipboard && window.isSecureContext) {
    return navigator.clipboard.writeText(text);
  }

  return new Promise((resolve, reject) => {
    const area = document.createElement("textarea");
    area.value = text;
    area.style.cssText = "position: fixed; top: -1000px; opacity: 0;";
    document.body.appendChild(area);
    area.select();
    const ok = document.execCommand && document.execCommand("copy");
    area.remove();
    ok ? resolve() : reject(new Error("copy failed"));
  });
}

function flashButton(button, message) {
  const original = button.textContent;
  button.textContent = message;
  window.setTimeout(() => (button.textContent = original), 1500);
}

/**
 * Removes the tabs and overview cells of the previous planet list, so a rebuild does
 * not stack them up.
 */
function clearViewerUi() {
  tabButtonsContainer.innerHTML = "";
  const overviewEl = document.getElementById("overviewContainer");
  if (overviewEl) overviewEl.innerHTML = "";
  stopOverviewAutoScroll();
}

/**
 * Watches the planet list for a newer timestamp, which means a new generation run
 * finished, and rebuilds the viewer with the new images. Without this you would have to
 * reload the page after every run.
 */
function startAutoRefresh(seconds, rereadable) {
  if (!seconds) return;

  if (rereadable === false) {
    console.warn(
      "⚠️ Auto refresh is off: 'local_planet_names.js' is in the old 'const planetNames' " +
        "format, which cannot be re-read. It is rewritten on the next preview generation."
    );
    return;
  }

  window.setInterval(() => {
    loadPlanetList(viewerConfig.planetNamesSource, true)
      .then(({ planets, time, mapString }) => {
        if (!time || time === shownPlanetListTime) return;
        console.info(`🔄 New previews detected (${time}) - refreshing.`);
        showPlanetList(planets, time, mapString);
      })
      .catch(() => {
        // A list being rewritten mid-run reads as an error; the next tick picks it up.
      });
  }, seconds * 1000);
}

// Main startup logic
loadPlanetList(viewerConfig.planetNamesSource, false)
  .then(({ planets, time, mapString, rereadable }) => {
    showPlanetList(planets, time, mapString);
    initKeyboardControls(mapImage, mapContainer, zoomDisplay);

    resetBtn.addEventListener("click", () => {
      resetMapView(mapImage, mapContainer, zoomDisplay);
    });

    const refreshSeconds = viewerConfig.autoRefreshSeconds;
    startAutoRefresh(refreshSeconds === undefined ? 10 : refreshSeconds, rereadable);
  })
  .catch((err) => {
    console.error("❌ Could not initialize viewer:", err);
  });
