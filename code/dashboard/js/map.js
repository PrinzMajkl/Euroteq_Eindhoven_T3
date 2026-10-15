// Map facade: the 2D map (Leaflet) by default, CesiumJS for the "3D view".
import { CONFIG } from './config.js';
import { toArena, insideArena, setAnchor, resetAnchor } from './geo.js';
import * as map2d from './map2d.js';
import * as map3d from './map3d.js';

let backend = null;
let mode = '2d';
let el;
let follow = false;
let pickCallback = null;
let lastState = null;
let toastFn = () => {};

export function setToast(fn) { toastFn = fn; }

export function ammoniaBin(v) {
  const L = CONFIG.AMMONIA_LIMIT;
  if (v < L) return 0;
  if (v < 3 * L) return 1;
  if (v < 8 * L) return 2;
  return 3;
}

const hooks = {
  ammoniaBin,
  toast: (t) => toastFn(t),
  onClick(ll, shift) {
    if (shift) {
      toastFn(`Latitude ${ll.lat.toFixed(5)}, longitude ${ll.lon.toFixed(5)}`);
      return;
    }
    if (!pickCallback) return;
    const p = toArena(ll);
    if (!insideArena(p)) {
      toastFn('That point is outside the monitored stretch. Click inside the dashed outline.');
      return;
    }
    backend.showPick(ll);
    const cb = pickCallback;
    pickCallback = null;
    backend.setPicking(false);
    cb(p);
  },
  onRelocate(ll) {
    if (ll) setAnchor(ll.lat, ll.lon); else resetAnchor();
    backend.relocated(lastState);
    toastFn(ll ? 'The monitored stretch now starts here. Right-click again to move it back.'
      : 'The monitored stretch is back at Wöhrder Wiese.');
  },
};

export async function initMap(container) {
  el = container;
  await useMode('2d');
}

export async function useMode(next) {
  if (backend && next === mode) return mode;
  const old = backend;
  backend = null;
  if (old) old.destroy();
  el.innerHTML = '';
  const holder = document.createElement('div');
  holder.className = 'map-holder';
  el.appendChild(holder);
  mode = next;
  try {
    backend = next === '3d' ? await map3d.create(holder, hooks) : map2d.create(holder, hooks);
  } catch (e) {
    console.error(e);
    toastFn(next === '3d' ? `3D view could not start: ${e.message}` : 'The map could not start.');
    if (next === '3d') return useMode('2d');
    return mode;
  }
  if (lastState) backend.update(lastState, false);
  return mode;
}

export function getMode() { return mode; }

export function updateMap(s) {
  lastState = s;
  if (backend) backend.update(s, follow);
}

export function highlightOutfall(id) { if (backend) backend.highlightOutfall(id); }

export function view(kind, instant = false, s = lastState) {
  follow = kind === 'follow';
  if (backend && kind !== 'none') backend.view(kind, s);
}

export function isFollowing() { return follow; }

export function pickSpot(cb) {
  pickCallback = cb;
  if (backend) backend.setPicking(true);
}

export function cancelPick() {
  pickCallback = null;
  if (backend) backend.setPicking(false);
}

export function hidePickMarker() { if (backend) backend.hidePick(); }
export function clearRequestMarkers() { if (backend) backend.clearRequests(); }
