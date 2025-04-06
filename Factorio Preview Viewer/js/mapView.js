const baseZoomFactor = 1.1;
const statePerPlanet = {};
let currentPlanet = null;
let zoomStepIndex = 0;
let scale = 1, offsetX = 0, offsetY = 0;

function setupTabs(config, tabContainer, mapImage) {
  Object.entries(config).forEach(([planet, url], index) => {
    const tab = document.createElement("div");
    tab.className = "tab";
    tab.dataset.planet = planet;
    tab.textContent = planet.charAt(0).toUpperCase() + planet.slice(1);

    if (index === 0) {
      tab.classList.add("active");
      currentPlanet = planet;
      mapImage.src = url;
      mapImage.onerror = () => console.error("Failed to load map image:", mapImage.src);
    }

    tab.addEventListener("click", () => switchPlanet(planet, config, mapImage));
    tabContainer.appendChild(tab);
  });
}

function switchPlanet(planet, config, mapImage) {
  if (currentPlanet) {
    statePerPlanet[currentPlanet] = { zoomStepIndex, offsetX, offsetY };
  }

  document.querySelectorAll(".tab").forEach(tab => tab.classList.remove("active"));
  document.querySelector(`.tab[data-planet="${planet}"]`).classList.add("active");

  currentPlanet = planet;
  mapImage.src = config[planet];
  mapImage.onerror = () => console.error("Failed to load map image:", mapImage.src);
}

function setInitialPlanet(mapImage) {
  if (currentPlanet && planetConfig[currentPlanet]) {
    mapImage.src = planetConfig[currentPlanet];
  }
}

function handleImageLoad(mapImage, container, zoomDisplay) {
  const rect = container.getBoundingClientRect();
  const imgW = mapImage.naturalWidth;
  const imgH = mapImage.naturalHeight;
  const minScale = Math.max(rect.width / imgW, rect.height / imgH);
  const minStep = Math.ceil(Math.log(minScale) / Math.log(baseZoomFactor));

  if (statePerPlanet[currentPlanet]) {
    ({ zoomStepIndex, offsetX, offsetY } = statePerPlanet[currentPlanet]);
    scale = getScaleFromStep(zoomStepIndex);
  } else {
    zoomStepIndex = 0;
    scale = getScaleFromStep(zoomStepIndex);
    offsetX = (rect.width - imgW * scale) / 2;
    offsetY = (rect.height - imgH * scale) / 2;
  }

  clampOffsets(mapImage, container);
  updateTransform(mapImage);
  updateZoomLabel(zoomDisplay);
}

function handleWheelZoom(e, mapImage, container, zoomDisplay) {
  e.preventDefault();
  const rect = container.getBoundingClientRect();
  const mouseX = (e.clientX - rect.left - offsetX) / scale;
  const mouseY = (e.clientY - rect.top - offsetY) / scale;

  const minScale = Math.max(rect.width / mapImage.naturalWidth, rect.height / mapImage.naturalHeight);
  const minStep = Math.ceil(Math.log(minScale) / Math.log(baseZoomFactor));

  zoomStepIndex += e.deltaY < 0 ? 1 : -1;
  zoomStepIndex = Math.max(zoomStepIndex, minStep);

  const newScale = getScaleFromStep(zoomStepIndex);
  offsetX -= mouseX * (newScale - scale);
  offsetY -= mouseY * (newScale - scale);
  scale = newScale;

  clampOffsets(mapImage, container);
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

  clampOffsets(mapImage, container);
  updateTransform(mapImage);
  updateZoomLabel(zoomDisplay);
}

function getScaleFromStep(step) {
  return Math.pow(baseZoomFactor, step);
}

function clampOffsets(mapImage, container) {
  const rect = container.getBoundingClientRect();
  const imgW = mapImage.naturalWidth * scale;
  const imgH = mapImage.naturalHeight * scale;

  offsetX = Math.min(0, Math.max(offsetX, rect.width - imgW));
  offsetY = Math.min(0, Math.max(offsetY, rect.height - imgH));
}

function updateTransform(mapImage) {
  mapImage.style.transform = `translate(${offsetX}px, ${offsetY}px) scale(${scale})`;
}

function updateZoomLabel(label) {
  label.textContent = `Zoom: ${Math.round(getScaleFromStep(zoomStepIndex) * 100)}%`;
}
