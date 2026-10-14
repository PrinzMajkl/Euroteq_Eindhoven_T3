// 2D interactive map (Leaflet + OpenStreetMap / satellite). The default map.
import { CONFIG } from './config.js';
import { toGlobe, arenaCorners, getAnchor, isCustomAnchor } from './geo.js';

const L = window.L;
const BIN_COLORS = ['#8ecae6', '#ffb703', '#fb8500', '#b54700'];
const LABEL_MIN_ZOOM = 16.5; // permanent labels only when zoomed in enough

const ll = (p) => [p.lat, p.lon];
const at = (x, y) => ll(toGlobe(x, y));

const pinSvg = (fill, stroke = '#fff') => `<svg xmlns="http://www.w3.org/2000/svg" width="28" height="36" viewBox="0 0 28 36">
  <path d="M14 35 C14 35 2 21 2 13 A12 12 0 0 1 26 13 C26 21 14 35 14 35 Z" fill="${fill}" stroke="${stroke}" stroke-width="2.5"/>
  <circle cx="14" cy="13" r="4.5" fill="#fff"/></svg>`;
const pinIcon = (fill, stroke) => L.divIcon({ html: pinSvg(fill, stroke), className: 'pin', iconSize: [28, 36], iconAnchor: [14, 35], tooltipAnchor: [0, -34] });

export function create(el, hooks) {
  const map = L.map(el, { zoomControl: false, attributionControl: true, maxZoom: 21, zoomSnap: 0.25 });
  L.control.zoom({ position: 'topright' }).addTo(map);

  const street = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 21, maxNativeZoom: 19, attribution: '© OpenStreetMap contributors',
  });
  const satellite = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
    maxZoom: 21, maxNativeZoom: 19, attribution: 'Imagery © Esri, Maxar, Earthstar Geographics',
  });
  street.addTo(map);
  L.control.layers({ 'Street map': street, Satellite: satellite }, null, { position: 'topright', collapsed: false }).addTo(map);

  // Panes keep the drawing order: stretch < trail < samples < markers < robot
  for (const [name, z] of [['stretch', 410], ['trail', 420], ['samples', 430], ['marks', 640], ['robot', 650]]) {
    map.createPane(name).style.zIndex = z;
  }

  const staticLayer = L.layerGroup().addTo(map);
  const sampleLayer = L.layerGroup().addTo(map);
  const requestLayer = L.layerGroup().addTo(map);
  const outfallMarkers = {};
  const sampleMarkers = new Map();
  const requestMarkers = new Map();

  const trail = L.polyline([], { pane: 'trail', color: '#023047', weight: 3, opacity: 0.5 }).addTo(map);
  const route = L.polyline([], { pane: 'trail', color: '#fb8500', weight: 3, dashArray: '8 8' });
  const hot = L.circleMarker([0, 0], { pane: 'marks', radius: 15, color: '#fb8500', weight: 4, fill: false });
  hot.bindTooltip('', { direction: 'bottom', offset: [0, 14], className: 'lbl lbl-hot', permanent: true });
  const robot = L.circleMarker([0, 0], { pane: 'robot', radius: 8, color: '#fff', weight: 3, fillColor: '#023047', fillOpacity: 1 });
  robot.bindTooltip('Robot', { direction: 'right', offset: [10, 0], className: 'lbl lbl-perm', permanent: true });
  const pick = L.marker([0, 0], { pane: 'marks', icon: pinIcon('#ffb703', '#023047') });
  pick.bindTooltip('New request', { direction: 'top', className: 'lbl', permanent: true });

  function drawStatic() {
    staticLayer.clearLayers();
    const corners = arenaCorners().map(ll);
    L.polygon(corners, { pane: 'stretch', color: '#219ebc', weight: 2, dashArray: '8 6', fillColor: '#219ebc', fillOpacity: 0.12 })
      .bindTooltip('Monitored river stretch (the lab arena)', { sticky: true, className: 'lbl' })
      .addTo(staticLayer);
    for (const o of CONFIG.OUTFALLS) {
      outfallMarkers[o.id] = L.marker(at(o.x, o.y), { pane: 'marks', icon: pinIcon('#023047') })
        .bindTooltip(o.name, { direction: 'top', className: 'lbl lbl-perm', permanent: true })
        .bindPopup(`<strong>${o.name}</strong><br>${o.note}`)
        .addTo(staticLayer);
    }
    highlighted = undefined;
  }

  let highlighted;
  function highlightOutfall(id) {
    if (id === highlighted) return;
    highlighted = id;
    for (const o of CONFIG.OUTFALLS) {
      const m = outfallMarkers[o.id];
      if (!m) continue;
      m.setIcon(pinIcon(o.id === id ? '#fb8500' : '#023047'));
      m.setTooltipContent(o.id === id ? `${o.name}: likely source` : o.name);
    }
  }

  function setLabelVisibility() {
    el.classList.toggle('labels-off', map.getZoom() < LABEL_MIN_ZOOM);
  }
  map.on('zoomend', setLabelVisibility);

  // Clicks
  map.on('click', (e) => hooks.onClick({ lat: e.latlng.lat, lon: e.latlng.lng }, e.originalEvent.shiftKey));
  map.on('contextmenu', (e) => {
    const div = L.DomUtil.create('div', 'ctx');
    div.innerHTML = `<p>Place the monitored stretch here?</p>
      <button type="button" class="btn btn-primary btn-small" data-a="move">Move stretch here</button>
      ${isCustomAnchor() ? '<button type="button" class="btn btn-small" data-a="reset">Back to Wöhrder Wiese</button>' : ''}`;
    const popup = L.popup({ className: 'ctx-popup' }).setLatLng(e.latlng).setContent(div).openOn(map);
    div.addEventListener('click', (ev) => {
      const a = ev.target.dataset.a;
      if (!a) return;
      map.closePopup(popup);
      hooks.onRelocate(a === 'move' ? { lat: e.latlng.lat, lon: e.latlng.lng } : null);
    });
  });

  let trailLen = -1;
  function update(s, follow) {
    const r = s.robot;
    if (r && r.x != null) {
      robot.setLatLng(at(r.x, r.y));
      if (!map.hasLayer(robot)) robot.addTo(map);
      if (follow) map.panTo(robot.getLatLng(), { animate: false });
    } else if (map.hasLayer(robot)) {
      robot.remove();
    }

    if (s.trail.length !== trailLen) {
      trailLen = s.trail.length;
      trail.setLatLngs(s.trail.map((q) => at(q.x, q.y)));
    }

    if (s.samples.length < sampleMarkers.size) { sampleLayer.clearLayers(); sampleMarkers.clear(); }
    for (const p of s.samples) {
      if (sampleMarkers.has(p.sample_id)) continue;
      const bin = hooks.ammoniaBin(p.nh3_n_mg_l);
      const m = L.circleMarker(at(p.x, p.y), { pane: 'samples', radius: 6, color: '#fff', weight: 2,
        fillColor: BIN_COLORS[bin], fillOpacity: 1 })
        .bindTooltip(`Sample ${p.sample_id}<br>Ammonia ${p.nh3_n_mg_l.toFixed(2)} mg/L<br>Oxygen ${p.do_mg_l.toFixed(1)} mg/L`, { className: 'lbl lbl-info', direction: 'top' });
      m.addTo(sampleLayer);
      sampleMarkers.set(p.sample_id, m);
    }

    if (s.peak && s.peak.nh3_n_mg_l >= CONFIG.AMMONIA_LIMIT) {
      hot.setLatLng(at(s.peak.x, s.peak.y));
      hot.setTooltipContent(`Highest reading ${s.peak.nh3_n_mg_l.toFixed(1)} mg/L`);
      if (!map.hasLayer(hot)) hot.addTo(map);
    } else if (map.hasLayer(hot)) {
      hot.remove();
    }

    const mode = s.twin && s.twin.mission && s.twin.mission.mode;
    const tgt = s.waypoint;
    if (tgt && r && r.x != null && (mode === 'ROUTING_TO_HOTSPOT' || (r.status || '').startsWith('NAV'))) {
      route.setLatLngs([at(r.x, r.y), at(tgt.x, tgt.y)]);
      if (!map.hasLayer(route)) route.addTo(map);
    } else if (map.hasLayer(route)) {
      route.remove();
    }

    for (const q of s.requests) {
      if (q.type !== 'inspect' || requestMarkers.has(q.id)) continue;
      requestMarkers.set(q.id, L.marker(at(q.x, q.y), { pane: 'marks', icon: pinIcon('#ffb703', '#023047') })
        .bindTooltip(`${q.id}: ${q.what}`, { direction: 'top', className: 'lbl' })
        .addTo(requestLayer));
    }
  }

  function view(kind, s) {
    if (kind === 'overview') {
      const b = L.latLngBounds(arenaCorners().map(ll));
      const panel = document.querySelector('.requests');
      const left = panel && !panel.classList.contains('collapsed') ? panel.offsetWidth + 40 : 40;
      map.fitBounds(b, { paddingTopLeft: [left, 70], paddingBottomRight: [40, 70], maxZoom: 19 });
    } else if (kind === 'hotspot' && s && s.peak) {
      map.setView(at(s.peak.x, s.peak.y), 19);
    } else if (kind === 'follow' && s && s.robot && s.robot.x != null) {
      map.setView(at(s.robot.x, s.robot.y), Math.max(map.getZoom(), 18));
    }
  }

  function relocated(s) {
    drawStatic();
    sampleLayer.clearLayers(); sampleMarkers.clear();
    requestLayer.clearLayers(); requestMarkers.clear();
    trailLen = -1;
    if (map.hasLayer(pick)) pick.remove();
    update(s, false);
    view('overview', s);
  }

  drawStatic();
  map.setView(ll(getAnchor()), 17);
  setLabelVisibility();
  // Leaflet needs a size check once the layout has settled.
  setTimeout(() => { map.invalidateSize(); view('overview'); }, 50);

  return {
    update, view, highlightOutfall, relocated,
    showPick(p) { pick.setLatLng(ll(p)); pick.addTo(map); },
    hidePick() { if (map.hasLayer(pick)) pick.remove(); },
    clearRequests() { requestLayer.clearLayers(); requestMarkers.clear(); },
    setPicking(on) { el.classList.toggle('picking', on); },
    resize() { map.invalidateSize(); },
    destroy() { map.remove(); },
  };
}
