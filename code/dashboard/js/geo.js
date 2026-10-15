// Arena (odom metres) <-> Pegnitz (lat/lon) mapping. Plain maths, no map library.
import { CONFIG } from './config.js';

const KEY = 'plumetrace.anchor';
const R = 6378137; // WGS84 equatorial radius, metres

function loadAnchor() {
  try {
    const a = JSON.parse(localStorage.getItem(KEY));
    if (a && isFinite(a.lat) && isFinite(a.lon)) return a;
  } catch { /* storage unavailable */ }
  return { ...CONFIG.ANCHOR };
}

let anchor = loadAnchor();
export function getAnchor() { return anchor; }
export function isCustomAnchor() { return anchor.lat !== CONFIG.ANCHOR.lat || anchor.lon !== CONFIG.ANCHOR.lon; }

/** Move the monitored stretch: the robot's start point goes to lat/lon. */
export function setAnchor(lat, lon) {
  anchor = { lat, lon };
  try { localStorage.setItem(KEY, JSON.stringify(anchor)); } catch { /* ignore */ }
}
export function resetAnchor() {
  anchor = { ...CONFIG.ANCHOR };
  try { localStorage.removeItem(KEY); } catch { /* ignore */ }
}

const h = (CONFIG.HEADING_DEG * Math.PI) / 180;
const ax = { e: Math.sin(h), n: Math.cos(h) };   // robot forward on the ground
const ay = { e: -Math.cos(h), n: Math.sin(h) };  // robot left

/** Arena x,y (m) -> metres east/north of the anchor. */
export function arenaToEnu(x, y) {
  const a = x * CONFIG.SCALE_ALONG;
  const c = y * CONFIG.SCALE_ACROSS;
  return { e: a * ax.e + c * ay.e, n: a * ax.n + c * ay.n };
}

/** Arena x,y (m) -> {lat, lon}. */
export function toGlobe(x, y) {
  const { e, n } = arenaToEnu(x, y);
  const lat = anchor.lat + (n / R) * (180 / Math.PI);
  const lon = anchor.lon + (e / (R * Math.cos((anchor.lat * Math.PI) / 180))) * (180 / Math.PI);
  return { lat, lon };
}

/** {lat, lon} -> arena x,y (m). Inverse of toGlobe. */
export function toArena(ll) {
  const n = ((ll.lat - anchor.lat) * Math.PI / 180) * R;
  const e = ((ll.lon - anchor.lon) * Math.PI / 180) * R * Math.cos((anchor.lat * Math.PI) / 180);
  const a = e * ax.e + n * ax.n;
  const c = e * ay.e + n * ay.n;
  return { x: a / CONFIG.SCALE_ALONG, y: c / CONFIG.SCALE_ACROSS };
}

/** Distance in river metres between two arena points. */
export function riverDistance(p, q) {
  const a = arenaToEnu(p.x, p.y);
  const b = arenaToEnu(q.x, q.y);
  return Math.hypot(a.e - b.e, a.n - b.n);
}

export function insideArena(p) {
  const A = CONFIG.ARENA;
  return p.x >= A.xMin && p.x <= A.xMax && p.y >= A.yMin && p.y <= A.yMax;
}

/** Kept for the report: toLatLon(toGlobe(x, y)). */
export function toLatLon(ll) { return ll; }

export function arenaCorners() {
  const A = CONFIG.ARENA;
  return [[A.xMin, A.yMin], [A.xMax, A.yMin], [A.xMax, A.yMax], [A.xMin, A.yMax]].map(([x, y]) => toGlobe(x, y));
}
