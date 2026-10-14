// CesiumJS river map: stretch, outfalls, robot, trail, samples, hotspot, requests.
import { CONFIG } from './config.js';
import { toGlobe, toArena, toLatLon, insideArena } from './geo.js';

const C = window.Cesium;
let viewer;
let follow = false;
let pickCallback = null;
const sampleEntities = new Map();
const requestEntities = new Map();
let robotEnt, trailEnt, hotEnt, targetEnt, pickEnt, outfallEnts = {};
let trailPositions = [];
let hasTerrain = false;

const NAVY = C.Color.fromCssColorString('#023047');
const CYAN = C.Color.fromCssColorString('#219ebc');
const BINS = ['#8ecae6', '#ffb703', '#fb8500', '#b54700'].map((c) => C.Color.fromCssColorString(c));
const WHITE = C.Color.WHITE;

export function ammoniaBin(v) {
  const L = CONFIG.AMMONIA_LIMIT;
  if (v < L) return 0;
  if (v < 3 * L) return 1;
  if (v < 8 * L) return 2;
  return 3;
}

function svgUri(svg) { return `data:image/svg+xml;base64,${btoa(svg)}`; }
const OUTFALL_ICON = (fill) => svgUri(`<svg xmlns="http://www.w3.org/2000/svg" width="30" height="38" viewBox="0 0 30 38">
  <path d="M15 37 C15 37 2 22 2 14 A13 13 0 0 1 28 14 C28 22 15 37 15 37 Z" fill="${fill}" stroke="#fff" stroke-width="2.5"/>
  <circle cx="15" cy="14" r="5" fill="#fff"/></svg>`);
const HOT_ICON = svgUri(`<svg xmlns="http://www.w3.org/2000/svg" width="44" height="44" viewBox="0 0 44 44">
  <circle cx="22" cy="22" r="18" fill="none" stroke="#fff" stroke-width="7"/>
  <circle cx="22" cy="22" r="18" fill="none" stroke="#fb8500" stroke-width="4"/>
  <circle cx="22" cy="22" r="4" fill="#fb8500" stroke="#fff" stroke-width="2"/></svg>`);
const PIN_ICON = svgUri(`<svg xmlns="http://www.w3.org/2000/svg" width="26" height="34" viewBox="0 0 26 34">
  <path d="M13 33 C13 33 2 20 2 12 A11 11 0 0 1 24 12 C24 20 13 33 13 33 Z" fill="#ffb703" stroke="#023047" stroke-width="2"/>
  <circle cx="13" cy="12" r="4" fill="#023047"/></svg>`);

const label = (text, opts = {}) => ({
  text,
  font: '700 14px Calibri, Carlito, "Segoe UI", sans-serif',
  fillColor: NAVY,
  outlineColor: WHITE,
  outlineWidth: 3,
  style: C.LabelStyle.FILL_AND_OUTLINE,
  pixelOffset: new C.Cartesian2(0, -30),
  heightReference: C.HeightReference.CLAMP_TO_GROUND,
  disableDepthTestDistance: Number.POSITIVE_INFINITY,
  ...opts,
});

export async function initMap(container) {
  const token = CONFIG.CESIUM_ION_TOKEN;
  if (token) C.Ion.defaultAccessToken = token;

  const options = {
    baseLayer: new C.ImageryLayer(new C.OpenStreetMapImageryProvider({ url: 'https://tile.openstreetmap.org/' })),
    baseLayerPicker: false, geocoder: false, homeButton: false, sceneModePicker: false,
    navigationHelpButton: false, animation: false, timeline: false, fullscreenButton: false,
    infoBox: false, selectionIndicator: false, requestRenderMode: false,
  };
  if (token) {
    options.terrain = CONFIG.TERRAIN_ASSET_ID === 1
      ? C.Terrain.fromWorldTerrain()
      : new C.Terrain(C.CesiumTerrainProvider.fromIonAssetId(CONFIG.TERRAIN_ASSET_ID));
    hasTerrain = true;
  }
  viewer = new C.Viewer(container, options);
  viewer.scene.globe.depthTestAgainstTerrain = false;
  viewer.scene.screenSpaceCameraController.enableCollisionDetection = true;

  if (token) {
    try {
      const tiles = CONFIG.BUILDINGS_ASSET_ID
        ? await C.Cesium3DTileset.fromIonAssetId(CONFIG.BUILDINGS_ASSET_ID)
        : await C.createOsmBuildingsAsync();
      viewer.scene.primitives.add(tiles);
    } catch (e) {
      console.warn('Buildings not loaded:', e);
    }
  }

  drawStretch();
  drawOutfalls();
  drawLive();
  setupClicks();
  view('overview', true);
  return viewer;
}

function ground(e) { return hasTerrain ? { heightReference: C.HeightReference.CLAMP_TO_GROUND, ...e } : e; }

function drawStretch() {
  const A = CONFIG.ARENA;
  const corners = [[A.xMin, A.yMin], [A.xMax, A.yMin], [A.xMax, A.yMax], [A.xMin, A.yMax]]
    .map(([x, y]) => toGlobe(x, y));
  viewer.entities.add({
    name: 'Monitored river stretch',
    polygon: { hierarchy: corners, material: CYAN.withAlpha(0.12), classificationType: C.ClassificationType.TERRAIN },
  });
  viewer.entities.add({
    polyline: { positions: [...corners, corners[0]], width: 2, clampToGround: true,
      material: new C.PolylineDashMaterialProperty({ color: CYAN, dashLength: 14 }) },
  });
  // Flow arrow label at downstream end
  viewer.entities.add({
    position: toGlobe(A.xMax, A.yMin),
    label: label('Monitored stretch (lab arena)', { font: '400 13px Calibri, Carlito, "Segoe UI", sans-serif', pixelOffset: new C.Cartesian2(0, 16), horizontalOrigin: C.HorizontalOrigin.RIGHT }),
  });
}

function drawOutfalls() {
  for (const o of CONFIG.OUTFALLS) {
    outfallEnts[o.id] = viewer.entities.add({
      id: `outfall-${o.id}`,
      position: toGlobe(o.x, o.y),
      billboard: ground({ image: OUTFALL_ICON('#023047'), verticalOrigin: C.VerticalOrigin.BOTTOM,
        disableDepthTestDistance: Number.POSITIVE_INFINITY }),
      label: label(o.name, { pixelOffset: new C.Cartesian2(0, -44) }),
    });
  }
}

let highlighted;
export function highlightOutfall(id) {
  if (id === highlighted) return;
  highlighted = id;
  for (const [k, e] of Object.entries(outfallEnts)) {
    e.billboard.image = OUTFALL_ICON(k === id ? '#fb8500' : '#023047');
    e.label.text = k === id ? `${CONFIG.OUTFALLS.find((o) => o.id === k).name}: likely source` : CONFIG.OUTFALLS.find((o) => o.id === k).name;
  }
}

function drawLive() {
  trailEnt = viewer.entities.add({
    polyline: { positions: new C.CallbackProperty(() => trailPositions, false), width: 3,
      clampToGround: true, material: NAVY.withAlpha(0.55) },
  });
  targetEnt = viewer.entities.add({
    show: false,
    polyline: { positions: [], width: 3, clampToGround: true,
      material: new C.PolylineDashMaterialProperty({ color: C.Color.fromCssColorString('#fb8500'), dashLength: 12 }) },
  });
  hotEnt = viewer.entities.add({
    show: false,
    billboard: ground({ image: HOT_ICON, disableDepthTestDistance: Number.POSITIVE_INFINITY }),
    label: label('Highest reading', { pixelOffset: new C.Cartesian2(0, 34), fillColor: C.Color.fromCssColorString('#b54700') }),
  });
  robotEnt = viewer.entities.add({
    show: false,
    point: ground({ pixelSize: 16, color: NAVY, outlineColor: WHITE, outlineWidth: 4,
      disableDepthTestDistance: Number.POSITIVE_INFINITY }),
    label: label('Robot', { pixelOffset: new C.Cartesian2(16, 0), horizontalOrigin: C.HorizontalOrigin.LEFT }),
  });
  pickEnt = viewer.entities.add({
    show: false,
    billboard: ground({ image: PIN_ICON, verticalOrigin: C.VerticalOrigin.BOTTOM, disableDepthTestDistance: Number.POSITIVE_INFINITY }),
    label: label('New request', { pixelOffset: new C.Cartesian2(0, -40) }),
  });
}

export function updateMap(s) {
  if (!viewer) return;
  // Robot + trail
  const r = s.robot;
  if (r && r.x != null) {
    const p = toGlobe(r.x, r.y);
    robotEnt.position = p;
    robotEnt.show = true;
    if (follow) {
      viewer.camera.lookAt(p, new C.HeadingPitchRange(C.Math.toRadians(CONFIG.HEADING_DEG - 90), -0.75, 260));
      viewer.camera.lookAtTransform(C.Matrix4.IDENTITY);
    }
  } else {
    robotEnt.show = false;
  }
  if (trailPositions.length !== s.trail.length) {
    trailPositions = s.trail.map((q) => toGlobe(q.x, q.y));
  }

  // Samples
  if (s.samples.length < sampleEntities.size) {
    for (const e of sampleEntities.values()) viewer.entities.remove(e);
    sampleEntities.clear();
  }
  for (const smp of s.samples) {
    if (sampleEntities.has(smp.sample_id)) continue;
    sampleEntities.set(smp.sample_id, viewer.entities.add({
      position: toGlobe(smp.x, smp.y),
      point: ground({ pixelSize: 8, color: BINS[ammoniaBin(smp.nh3_n_mg_l)], outlineColor: WHITE, outlineWidth: 2,
        disableDepthTestDistance: Number.POSITIVE_INFINITY }),
      properties: { kind: 'sample', sample: smp },
    }));
  }

  // Hotspot = highest reading above the limit
  if (s.peak && s.peak.nh3_n_mg_l >= CONFIG.AMMONIA_LIMIT) {
    hotEnt.position = toGlobe(s.peak.x, s.peak.y);
    hotEnt.show = true;
  } else {
    hotEnt.show = false;
  }

  // Active route to target
  const mode = s.twin && s.twin.mission && s.twin.mission.mode;
  const tgt = s.waypoint;
  if (tgt && r && r.x != null && (mode === 'ROUTING_TO_HOTSPOT' || (r.status || '').startsWith('NAV'))) {
    targetEnt.polyline.positions = [toGlobe(r.x, r.y), toGlobe(tgt.x, tgt.y)];
    targetEnt.show = true;
  } else {
    targetEnt.show = false;
  }

  // Request markers
  for (const q of s.requests) {
    if (q.type !== 'inspect' || requestEntities.has(q.id)) continue;
    requestEntities.set(q.id, viewer.entities.add({
      position: toGlobe(q.x, q.y),
      billboard: ground({ image: PIN_ICON, verticalOrigin: C.VerticalOrigin.BOTTOM, disableDepthTestDistance: Number.POSITIVE_INFINITY }),
      label: label(q.id, { pixelOffset: new C.Cartesian2(0, -40), font: '400 13px Calibri, Carlito, "Segoe UI", sans-serif' }),
    }));
  }
}

// ---------------- Clicks ----------------
function groundPoint(screen) {
  const ray = viewer.camera.getPickRay(screen);
  return (ray && viewer.scene.globe.pick(ray, viewer.scene)) || viewer.camera.pickEllipsoid(screen);
}

let toastFn = () => {};
export function setToast(fn) { toastFn = fn; }

function setupClicks() {
  const h = new C.ScreenSpaceEventHandler(viewer.scene.canvas);
  h.setInputAction((ev) => {
    const pos = groundPoint(ev.position);
    if (!pos) return;
    const ll = toLatLon(pos);
    toastFn(`Lat ${ll.lat.toFixed(5)}, Lon ${ll.lon.toFixed(5)} (copy into config.js ANCHOR)`);
  }, C.ScreenSpaceEventType.LEFT_CLICK, C.KeyboardEventModifier.SHIFT);

  h.setInputAction((ev) => {
    const pos = groundPoint(ev.position);
    if (pickCallback && pos) {
      const p = toArena(pos);
      if (!insideArena(p)) {
        toastFn('That point is outside the monitored stretch. Click inside the dashed outline.');
        return;
      }
      pickEnt.position = toGlobe(p.x, p.y);
      pickEnt.show = true;
      const cb = pickCallback;
      pickCallback = null;
      cb(p);
      return;
    }
    const picked = viewer.scene.pick(ev.position);
    const ent = picked && picked.id;
    if (ent && ent.properties && ent.properties.kind) {
      const smp = ent.properties.sample.getValue();
      toastFn(`Sample ${smp.sample_id}: ammonia ${smp.nh3_n_mg_l.toFixed(2)} mg/L, oxygen ${smp.do_mg_l.toFixed(1)} mg/L`);
    }
  }, C.ScreenSpaceEventType.LEFT_CLICK);
}

export function pickSpot(cb) {
  pickCallback = cb;
  viewer.container.style.cursor = 'crosshair';
  const done = cb;
  pickCallback = (p) => { viewer.container.style.cursor = ''; done(p); };
}

export function cancelPick() {
  pickCallback = null;
  if (viewer) viewer.container.style.cursor = '';
}

export function hidePickMarker() { if (pickEnt) pickEnt.show = false; }

export function clearRequestMarkers() {
  for (const e of requestEntities.values()) viewer.entities.remove(e);
  requestEntities.clear();
}

// ---------------- Camera ----------------
export function view(kind, instant = false, s = null) {
  if (!viewer) return;
  follow = kind === 'follow';
  if (kind === 'overview') {
    const A = CONFIG.ARENA;
    // Aim a little downstream of the middle so the stretch clears the request panel.
    const xMid = (A.xMin + A.xMax) / 2 - 0.14 * (A.xMax - A.xMin);
    const center = toGlobe(xMid, (A.yMin + A.yMax) / 2);
    const len = (A.xMax - A.xMin) * CONFIG.SCALE_ALONG;
    const sphere = new C.BoundingSphere(center, len / 2);
    viewer.camera.flyToBoundingSphere(sphere, {
      duration: instant ? 0 : 1.2,
      offset: new C.HeadingPitchRange(C.Math.toRadians(CONFIG.HEADING_DEG - 90), C.Math.toRadians(-62), len * 1.55),
    });
  } else if (kind === 'hotspot' && s && s.peak) {
    viewer.camera.flyToBoundingSphere(new C.BoundingSphere(toGlobe(s.peak.x, s.peak.y), 30), {
      duration: 1.2,
      offset: new C.HeadingPitchRange(C.Math.toRadians(CONFIG.HEADING_DEG - 90), C.Math.toRadians(-45), 160),
    });
  }
}

export function isFollowing() { return follow; }
