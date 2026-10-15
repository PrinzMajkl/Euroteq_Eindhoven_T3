// PlumeTrace dashboard settings. Edit this file, not the code.

export const CONFIG = {
  // Cesium ion access token for the "3D view" button (ion.cesium.com ->
  // Access Tokens -> Default token). The normal 2D map does not need it.
  // Empty = 3D globe with street map only. With a token: aerial imagery,
  // 3D terrain and 3D buildings. Set TERRAIN_ASSET_ID to your own
  // uploaded Bavarian DGM1 terrain later; 1 = Cesium World Terrain.
  CESIUM_ION_TOKEN: '',
  TERRAIN_ASSET_ID: 1,
  // Optional: your uploaded Bavarian LoD2 buildings (3D Tiles asset id).
  // null = Cesium OSM Buildings (needs a token).
  BUILDINGS_ASSET_ID: null,

  // Gateway WebSocket (gateway_node.py). Same computer by default.
  WS_URL: `ws://${location.hostname || 'localhost'}:8765`,

  // ---- Arena -> Pegnitz mapping -------------------------------------------
  // The robot's start point (odom 0,0) is placed here on the river:
  // the Pegnitz at Wöhrder Wiese, Nürnberg (checked on OpenStreetMap).
  // Shift+click the map to read coordinates if you want another stretch.
  ANCHOR: { lat: 49.45155, lon: 11.0905 },
  // Direction of the robot's forward axis (+x), degrees clockwise from north.
  // 98 = roughly east along the river here, so the robot drives upstream
  // towards the Wöhrder See.
  HEADING_DEG: 98,
  // Metres of river per metre of arena. Along the river and across it, so the
  // arena's wooden walls line up with the riverbanks.
  SCALE_ALONG: 30,
  SCALE_ACROSS: 3.5,
  // Arena walls in odom coordinates (metres). 10 x 10 m arena.
  ARENA: { xMin: -0.5, xMax: 9.5, yMin: -5, yMax: 5 },

  // Candidate outfalls in arena coordinates (metres, odom frame).
  // Place them where your markers stand in the lab.
  OUTFALLS: [
    { id: 'A', name: 'Outfall A', note: 'Storm overflow, south bank', x: 1.5, y: -4.8 },
    { id: 'B', name: 'Outfall B', note: 'Combined sewer overflow, north bank', x: 4.7, y: 4.8 },
    { id: 'C', name: 'Outfall C', note: 'Road drainage, north bank', x: 8.0, y: 4.8 },
  ],

  // ---- Limits (OGewV acute ammonia limit) ----------------------------------
  AMMONIA_LIMIT: 0.6, // mg/L NH3-N
  OXYGEN_LOW: 7.0, // mg/L, matches the twin's low_do_mg_l
  OXYGEN_CRITICAL: 3.0, // mg/L, fish kills below this

  // Manual grab sampling cost per sample (Gemini cost study), EUR
  MANUAL_SAMPLE_COST: [439, 828],

  REPLAY_FILE: 'data/demo_run.jsonl',
};
