const tabButtonsContainer = document.querySelector(".tab-buttons");
const mapImage = document.getElementById("mapImage");
const mapContainer = document.getElementById("mapContainer");
const zoomDisplay = document.getElementById("zoomDisplay");
const resetBtn = document.getElementById("resetView");

/**
 * Dynamically loads a <script> containing `planetNames` variable.
 */
function loadPlanetNamesFromScript(src) {
  if (location.protocol === "file:" || src.endsWith(".js")) {
    // Load as JS script tag
    return new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = src;
      script.onload = () => {
        if (typeof planetNames !== "undefined") {
          resolve(planetNames);
        } else {
          reject(new Error("planetNames is not defined after loading script."));
        }
      };
      script.onerror = () => reject(new Error("Failed to load planetNames script."));
      document.head.appendChild(script);
    });
  } else {
    // Load as JSON
    return fetch(src)
      .then((res) => {
        if (!res.ok) throw new Error("Network response was not ok");
        return res.json();
      })
      .then((data) => {
        if (!Array.isArray(data)) throw new Error("Invalid planetNames format in JSON");
        return data;
      });
  }
}

// Main startup logic
loadPlanetNamesFromScript(viewerConfig.planetNamesSource)
  .then((planetNames) => {
    const filteredSources = Object.fromEntries(
      Object.entries(viewerConfig.planetPreviewSources).filter(([planet]) =>
        planetNames.includes(planet)
      )
    );

    setupTabs(filteredSources, tabButtonsContainer, mapImage);
    initKeyboardControls(mapImage, mapContainer, zoomDisplay);

    resetBtn.addEventListener("click", () => {
      resetMapView(mapImage, mapContainer, zoomDisplay);
    });
  })
  .catch((err) => {
    console.error("❌ Could not initialize viewer:", err);
  });
