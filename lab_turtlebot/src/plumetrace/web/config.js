// PlumeTrace city view configuration. Edit here; nothing else needs changing.
window.PLUMETRACE_CONFIG = {
  // Gateway WebSocket. tools/relay.py overrides this with 'auto' (same origin as the page)
  wsUrl: 'ws://localhost:8765',
  // Cesium 3D Tiles of the WaterBody + nearby buildings (from FME). Loaded when not empty.
  tileset_url: '',
  // Optional Cesium ion token. Leave empty here (this file is in git): put it in web/config.local.js
  // (git-ignored) as window.PLUMETRACE_CONFIG_LOCAL = { ionToken: '...' }. Empty = OSM imagery + ellipsoid.
  ionToken: '',
  // Synthetic overflow events for the timeline until the EDM fetcher runs live (river seconds)
  overflowEvents: [{ id: 'PLACEHOLDER-EDM-EVENT', start_s: -1200, end_s: null, outfall: '?' }],
};
