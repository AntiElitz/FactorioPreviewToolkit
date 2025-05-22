function initKeyboardControls(mapImage, mapContainer, zoomDisplay) {
  const keysPressed = new Set();
  const panSpeed = 32;
  let isDragging = false;
  let startX = 0;
  let startY = 0;

  mapImage.addEventListener("load", () => {
    handleImageLoad(mapImage, mapContainer, zoomDisplay);
  });

  mapImage.addEventListener("dragstart", e => e.preventDefault());

  mapContainer.addEventListener("wheel", e => {
    handleWheelZoom(e, mapImage, mapContainer, zoomDisplay);
  });

  mapContainer.addEventListener("dblclick", () => {
    resetMapView(mapImage, mapContainer, zoomDisplay);
  });

  mapContainer.addEventListener("mousedown", e => {
    if (e.button !== 0) return;
    isDragging = true;
    startX = e.clientX - offsetX;
    startY = e.clientY - offsetY;
    mapContainer.style.cursor = "grabbing";
  });

  window.addEventListener("mouseup", () => {
    isDragging = false;
    mapContainer.style.cursor = "grab";
  });

  window.addEventListener("mousemove", e => {
    if (!isDragging) return;
    offsetX = e.clientX - startX;
    offsetY = e.clientY - startY;
    updateTransform(mapImage);
  });

  window.addEventListener("keydown", e => {
    const valid = ["w", "a", "s", "d", "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"];
    if (valid.includes(e.key)) {
      keysPressed.add(e.key);
      e.preventDefault();
    }
  });

  window.addEventListener("keyup", e => {
    keysPressed.delete(e.key);
  });

  function animate() {
    let moved = false;

    if (keysPressed.has("w") || keysPressed.has("ArrowUp")) {
      offsetY += panSpeed;
      moved = true;
    }
    if (keysPressed.has("s") || keysPressed.has("ArrowDown")) {
      offsetY -= panSpeed;
      moved = true;
    }
    if (keysPressed.has("a") || keysPressed.has("ArrowLeft")) {
      offsetX += panSpeed;
      moved = true;
    }
    if (keysPressed.has("d") || keysPressed.has("ArrowRight")) {
      offsetX -= panSpeed;
      moved = true;
    }

    if (moved) {
      updateTransform(mapImage);
    }

    requestAnimationFrame(animate);
  }

  animate();
}
