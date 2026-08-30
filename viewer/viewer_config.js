const viewerConfig = {
  // Local previews are always written as ../previews/<planet>.png, so the source is
  // derived from the planet name. This way mod planets show up without extra config.
  planetPreviewSourceTemplate: "../previews/{planet}.png",

  // Optional per-planet overrides, e.g. { nauvis: "../previews/my_nauvis.png" }
  planetPreviewSources: {},

  // Composite "Overview" tab: one large planet plus a scrollable column of the rest.
  overview: {
    // Leave main/side out to follow the planet list, so mod planets are included.
    // main: "nauvis",
    // side: ["gleba", "fulgora", "vulcanus", "aquilo"],

    // How many side cells are visible before the column scrolls.
    visibleSideCells: 4,

    // Seconds between automatic scrolls of the side column, for streaming.
    // Pauses while the mouse is over the column. Set to 0 to disable.
    autoScrollSeconds: 0
  },

  // Show a button that copies the map exchange string, so viewers can generate the
  // very same map themselves. Set to false to hide it.
  showCopyMapStringButton: true,

  // Check for a newer set of previews every N seconds and refresh the images on its
  // own, so a generation started while the viewer is open shows up without reloading
  // the page. Set to 0 to turn it off.
  autoRefreshSeconds: 10,

  // Tab selected on load: "overview", a planet name, or "auto"
  // (overview when available, otherwise the first planet).
  defaultTab: "auto",

  // Zoom for the overview's side cells, as a multiple of the "fill the cell"
  // baseline (1 = just fill, higher = zoom in). `default` applies to any planet
  // not listed. The main cell always opens at 100%, like its own tab.
  defaultZoom: {
    default: 1.5,
    aquilo: 3
  },

  planetNamesSource: "../previews/local_planet_names.js"
};
