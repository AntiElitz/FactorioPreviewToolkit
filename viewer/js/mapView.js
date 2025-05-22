const baseZoomFactor = 1.14;
const statePerPlanet = {};
let currentPlanet = null;
let zoomStepIndex = 0;
let scale = 1, offsetX = 0, offsetY = 0;

function setupTabs(previewSources, tabContainer, mapImage) {
  Object.entries(previewSources).forEach(([planet, url], index) => {
    const tab = document.createElement("div");
    tab.className = "tab";
    tab.dataset.planet = planet;
    tab.textContent = planet.charAt(0).toUpperCase() + planet.slice(1);

    if (index === 0) {
      tab.classList.add("active");
      currentPlanet = planet;

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

      mapImage.src = url;
    }

    tab.addEventListener("click", () => switchPlanet(planet, previewSources, mapImage));
    tabContainer.appendChild(tab);
  });
}

function switchPlanet(planet, previewSources, mapImage) {
  if (currentPlanet) {
    statePerPlanet[currentPlanet] = { zoomStepIndex, offsetX, offsetY };
  }

  document.querySelectorAll(".tab").forEach(tab => tab.classList.remove("active"));
  const newTab = document.querySelector(`.tab[data-planet="${planet}"]`);
  if (newTab) newTab.classList.add("active");

  currentPlanet = planet;
  mapImage.src = previewSources[planet];
  mapImage.onerror = () => console.error("Failed to load map image:", mapImage.src);
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
