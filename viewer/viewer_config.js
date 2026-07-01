const viewerConfig  = {
    planetPreviewSources: {
    nauvis: "../previews/nauvis.png",
    vulcanus: "../previews/vulcanus.png",
    gleba: "../previews/gleba.png",
    fulgora: "../previews/fulgora.png",
    aquilo: "../previews/aquilo.png"
  },
  // Composite "Overview" tab: one large planet on the left (~2/3 width),
  // the rest stacked top-to-bottom on the right (~1/3 width). The Overview
  // tab is shown only when at least one of these side planets is available
  // (i.e. it is skipped for vanilla / non-Space-Age maps).
  overview: {
    main: "nauvis",
    side: ["gleba", "fulgora", "vulcanus", "aquilo"]
  },

  // Tab selected on load: "overview", a planet name (e.g. "nauvis"), or
  // "auto" (overview when available, otherwise the first planet). Falls back
  // gracefully when the requested tab isn't available.
  defaultTab: "overview",

  // Zoom for the overview's side cells, as a multiple of the "fill the cell"
  // baseline (1 = just fill, higher = zoom in). `default` applies to any side
  // planet not listed here. Planet tabs and the overview's main planet
  // (Nauvis) stay at the upstream default and are not affected by this.
  defaultZoom: {
    default: 1.5,
    aquilo: 3
  },

  planetNamesSource: "../previews/local_planet_names.js"
};
