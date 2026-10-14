// 3D view (CesiumJS). Loaded only when "3D view" is switched on.
import { CONFIG } from './config.js';
import { toGlobe, toArena, arenaCorners } from './geo.js';

const CESIUM = 'https://cdn.jsdelivr.net/npm/cesium@1.122.0/Build/Cesium/';
let loading;

/** Load CesiumJS from the CDN once. */
export function loadCesium() {
  if (window.Cesium) return Promise.resolve(window.Cesium);
  if (loading) return loading;
  loading = new Promise((resolve, reject) => {
    window.CESIUM_BASE_URL = CESIUM;
    const css = document.createElement('link');
    css.rel = 'stylesheet';
    css.href = `${CESIUM}Widgets/widgets.css`;
    document.head.appendChild(css);
    const s = document.createElement('script');
    s.src = `${CESIUM}Cesium.js`;
    s.onload = () => resolve(window.Cesium);
    s.onerror = () => reject(new Error('Could not download CesiumJS. Check the internet connection.'));
    document.head.appendChild(s);
  });
  return loading;
}

export async function create(el, hooks) {
  const C = await loadCesium();
  const NAVY = C.Color.fromCssColorString('#023047');
  const CYAN = C.Color.fromCssColorString('#219ebc');
  const BINS = ['#8ecae6', '#ffb703', '#fb8500', '#b54700'].map((c) => C.Color.fromCssColorString(c));
  const WHITE = C.Color.WHITE;
  const pos = (x, y) => { const p = toGlobe(x, y); return C.Cartesian3.fromDegrees(p.lon, p.lat, 0); };
  const svgUri = (svg) => `data:image/svg+xml;base64,${btoa(svg)}`;
  const PIN = (fill, stroke = '#fff') => svgUri(`<svg xmlns="http://www.w3.org/2000/svg" width="28" height="36" viewBox="0 0 28 36">
    <path d="M14 35 C14 35 2 21 2 13 A12 12 0 0 1 26 13 C26 21 14 35 14 35 Z" fill="${fill}" stroke="${stroke}" stroke-width="2.5"/>
    <circle cx="14" cy="13" r="4.5" fill="#fff"/></svg>`);
  const HOT = svgUri(`<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 40 40">
    <circle cx="20" cy="20" r="16" fill="none" stroke="#fff" stroke-width="7"/>
    <circle cx="20" cy="20" r="16" fill="none" stroke="#fb8500" stroke-width="4"/></svg>`);

  const token = CONFIG.CESIUM_ION_TOKEN;
  if (token) C.Ion.defaultAccessToken = token;
  const options = {
    baseLayerPicker: false, geocoder: false, homeButton: false, sceneModePicker: false,
    navigationHelpButton: false, animation: false, timeline: false, fullscreenButton: false,
    infoBox: false, selectionIndicator: false,
  };
  if (token) {
    // Bing aerial imagery + world terrain from Cesium ion
    options.baseLayer = C.ImageryLayer.fromWorldImagery();
    options.terrain = CONFIG.TERRAIN_ASSET_ID === 1
      ? C.Terrain.fromWorldTerrain()
      : new C.Terrain(C.CesiumTerrainProvider.fromIonAssetId(CONFIG.TERRAIN_ASSET_ID));
  } else {
    options.baseLayer = new C.ImageryLayer(new C.OpenStreetMapImageryProvider({ url: 'https://tile.openstreetmap.org/' }));
  }
  const viewer = new C.Viewer(el, options);
  const ground = token ? { heightReference: C.HeightReference.CLAMP_TO_GROUND } : {};
  const top = { disableDepthTestDistance: Number.POSITIVE_INFINITY };

  if (token) {
    try {
      const tiles = CONFIG.BUILDINGS_ASSET_ID
        ? await C.Cesium3DTileset.fromIonAssetId(CONFIG.BUILDINGS_ASSET_ID)
        : await C.createOsmBuildingsAsync();
      viewer.scene.primitives.add(tiles);
    } catch (e) {
      console.warn('3D buildings not loaded:', e);
    }
  }

  const label = (text, extra = {}) => ({
    text, font: '700 14px Calibri, Carlito, "Segoe UI", sans-serif', fillColor: NAVY,
    showBackground: true, backgroundColor: C.Color.WHITE.withAlpha(0.9),
    backgroundPadding: new C.Cartesian2(6, 3),
    heightReference: C.HeightReference.CLAMP_TO_GROUND, ...top,
    // Labels fade out when far away, so they don't pile up
    distanceDisplayCondition: new C.DistanceDisplayCondition(0, 900),
    ...extra,
  });

  // Static: stretch + outfalls
  let staticEnts = [];
  const outfalls = {};
  function drawStatic() {
    staticEnts.forEach((e) => viewer.entities.remove(e));
    staticEnts = [];
    const corners = arenaCorners().map((p) => C.Cartesian3.fromDegrees(p.lon, p.lat, 0));
    staticEnts.push(viewer.entities.add({ polygon: { hierarchy: corners, material: CYAN.withAlpha(0.15), classificationType: C.ClassificationType.TERRAIN } }));
    staticEnts.push(viewer.entities.add({ polyline: { positions: [...corners, corners[0]], width: 2, clampToGround: true,
      material: new C.PolylineDashMaterialProperty({ color: CYAN, dashLength: 14 }) } }));
    for (const o of CONFIG.OUTFALLS) {
      outfalls[o.id] = viewer.entities.add({ position: pos(o.x, o.y),
        billboard: { image: PIN('#023047'), verticalOrigin: C.VerticalOrigin.BOTTOM, ...ground, ...top },
        label: label(o.name, { pixelOffset: new C.Cartesian2(0, -46) }) });
      staticEnts.push(outfalls[o.id]);
    }
    highlighted = undefined;
  }
  let highlighted;
  function highlightOutfall(id) {
    if (id === highlighted) return;
    highlighted = id;
    for (const o of CONFIG.OUTFALLS) {
      const e = outfalls[o.id];
      if (!e) continue;
      e.billboard.image = PIN(o.id === id ? '#fb8500' : '#023047');
      e.label.text = o.id === id ? `${o.name}: likely source` : o.name;
    }
  }

  let trailPositions = [];
  const trail = viewer.entities.add({ polyline: { positions: new C.CallbackProperty(() => trailPositions, false),
    width: 3, clampToGround: true, material: NAVY.withAlpha(0.55) } });
  const route = viewer.entities.add({ show: false, polyline: { positions: [], width: 3, clampToGround: true,
    material: new C.PolylineDashMaterialProperty({ color: C.Color.fromCssColorString('#fb8500'), dashLength: 12 }) } });
  const hot = viewer.entities.add({ show: false, billboard: { image: HOT, ...ground, ...top } });
  const robot = viewer.entities.add({ show: false,
    point: { pixelSize: 16, color: NAVY, outlineColor: WHITE, outlineWidth: 3, ...ground, ...top },
    label: label('Robot', { pixelOffset: new C.Cartesian2(14, 0), horizontalOrigin: C.HorizontalOrigin.LEFT }) });
  const pick = viewer.entities.add({ show: false,
    billboard: { image: PIN('#ffb703', '#023047'), verticalOrigin: C.VerticalOrigin.BOTTOM, ...ground, ...top } });
  const samples = new Map();
  const requests = new Map();

  const handler = new C.ScreenSpaceEventHandler(viewer.scene.canvas);
  const groundAt = (screen) => {
    const ray = viewer.camera.getPickRay(screen);
    const c = (ray && viewer.scene.globe.pick(ray, viewer.scene)) || viewer.camera.pickEllipsoid(screen);
    if (!c) return null;
    const g = C.Cartographic.fromCartesian(c);
    return { lat: C.Math.toDegrees(g.latitude), lon: C.Math.toDegrees(g.longitude) };
  };
  handler.setInputAction((ev) => { const p = groundAt(ev.position); if (p) hooks.onClick(p, false); }, C.ScreenSpaceEventType.LEFT_CLICK);
  handler.setInputAction((ev) => { const p = groundAt(ev.position); if (p) hooks.onClick(p, true); }, C.ScreenSpaceEventType.LEFT_CLICK, C.KeyboardEventModifier.SHIFT);

  let trailLen = -1;
  function update(s, follow) {
    const r = s.robot;
    if (r && r.x != null) {
      robot.position = pos(r.x, r.y);
      robot.show = true;
      if (follow) {
        viewer.camera.lookAt(robot.position.getValue(), new C.HeadingPitchRange(C.Math.toRadians(CONFIG.HEADING_DEG - 90), -0.75, 260));
        viewer.camera.lookAtTransform(C.Matrix4.IDENTITY);
      }
    } else robot.show = false;

    if (s.trail.length !== trailLen) {
      trailLen = s.trail.length;
      trailPositions = s.trail.map((q) => pos(q.x, q.y));
    }
    if (s.samples.length < samples.size) { samples.forEach((e) => viewer.entities.remove(e)); samples.clear(); }
    for (const p of s.samples) {
      if (samples.has(p.sample_id)) continue;
      samples.set(p.sample_id, viewer.entities.add({ position: pos(p.x, p.y),
        point: { pixelSize: 9, color: BINS[hooks.ammoniaBin(p.nh3_n_mg_l)], outlineColor: WHITE, outlineWidth: 2, ...ground, ...top } }));
    }
    if (s.peak && s.peak.nh3_n_mg_l >= CONFIG.AMMONIA_LIMIT) { hot.position = pos(s.peak.x, s.peak.y); hot.show = true; } else hot.show = false;

    const mode = s.twin && s.twin.mission && s.twin.mission.mode;
    const tgt = s.waypoint;
    if (tgt && r && r.x != null && (mode === 'ROUTING_TO_HOTSPOT' || (r.status || '').startsWith('NAV'))) {
      route.polyline.positions = [pos(r.x, r.y), pos(tgt.x, tgt.y)];
      route.show = true;
    } else route.show = false;

    for (const q of s.requests) {
      if (q.type !== 'inspect' || requests.has(q.id)) continue;
      requests.set(q.id, viewer.entities.add({ position: pos(q.x, q.y),
        billboard: { image: PIN('#ffb703', '#023047'), verticalOrigin: C.VerticalOrigin.BOTTOM, ...ground, ...top } }));
    }
  }

  function view(kind, s) {
    const A = CONFIG.ARENA;
    const heading = C.Math.toRadians(CONFIG.HEADING_DEG - 90);
    if (kind === 'overview') {
      const len = (A.xMax - A.xMin) * CONFIG.SCALE_ALONG;
      viewer.camera.flyToBoundingSphere(new C.BoundingSphere(pos((A.xMin + A.xMax) / 2, 0), len / 2),
        { duration: 1.2, offset: new C.HeadingPitchRange(heading, C.Math.toRadians(-35), len * 1.3) });
    } else if (kind === 'hotspot' && s && s.peak) {
      viewer.camera.flyToBoundingSphere(new C.BoundingSphere(pos(s.peak.x, s.peak.y), 30),
        { duration: 1.2, offset: new C.HeadingPitchRange(heading, C.Math.toRadians(-40), 180) });
    }
  }

  drawStatic();
  view('overview');

  // If the globe never draws (some graphics setups), say so instead of showing black space.
  setTimeout(() => {
    if (!viewer.isDestroyed() && !viewer.scene.globe.tilesLoaded && viewer.scene.globe._surface._tilesToRender.length === 0) {
      hooks.toast('The 3D globe did not load on this computer. Use the 2D map, or try Chrome with hardware acceleration on.');
    }
  }, 10000);

  return {
    update, view, highlightOutfall,
    relocated(s) {
      drawStatic();
      samples.forEach((e) => viewer.entities.remove(e)); samples.clear();
      requests.forEach((e) => viewer.entities.remove(e)); requests.clear();
      trailLen = -1; pick.show = false;
      update(s, false); view('overview', s);
    },
    showPick(p) { const a = toArena(p); pick.position = pos(a.x, a.y); pick.show = true; },
    hidePick() { pick.show = false; },
    clearRequests() { requests.forEach((e) => viewer.entities.remove(e)); requests.clear(); },
    setPicking(on) { el.style.cursor = on ? 'crosshair' : ''; },
    resize() {},
    destroy() { handler.destroy(); viewer.destroy(); },
  };
}
