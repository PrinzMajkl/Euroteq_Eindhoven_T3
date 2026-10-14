// Arena (odom metres) <-> Pegnitz (globe) coordinate mapping.
import { CONFIG } from './config.js';

const C = window.Cesium;
const h = (CONFIG.HEADING_DEG * Math.PI) / 180;
// Unit vectors (east, north) of the arena axes on the ground.
const ax = { e: Math.sin(h), n: Math.cos(h) }; // robot forward
const ay = { e: -Math.cos(h), n: Math.sin(h) }; // robot left

const anchor = C.Cartesian3.fromDegrees(CONFIG.ANCHOR.lon, CONFIG.ANCHOR.lat, 0);
const enuToWorld = C.Transforms.eastNorthUpToFixedFrame(anchor);
const worldToEnu = C.Matrix4.inverse(enuToWorld, new C.Matrix4());

/** Arena x,y (m) -> metres east/north of the anchor on the river. */
export function arenaToEnu(x, y) {
  const a = x * CONFIG.SCALE_ALONG;
  const c = y * CONFIG.SCALE_ACROSS;
  return { e: a * ax.e + c * ay.e, n: a * ax.n + c * ay.n };
}

/** Arena x,y (m) -> Cesium Cartesian3 on the ground. */
export function toGlobe(x, y) {
  const { e, n } = arenaToEnu(x, y);
  return C.Matrix4.multiplyByPoint(enuToWorld, new C.Cartesian3(e, n, 0), new C.Cartesian3());
}

/** Cesium Cartesian3 -> arena x,y (m). Inverse of toGlobe. */
export function toArena(cartesian) {
  const p = C.Matrix4.multiplyByPoint(worldToEnu, cartesian, new C.Cartesian3());
  // Solve [ax ay] * [a c]^T = [e n]^T (rotation matrix, so transpose = inverse).
  const a = p.x * ax.e + p.y * ax.n;
  const c = p.x * ay.e + p.y * ay.n;
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

export function toLatLon(cartesian) {
  const c = C.Cartographic.fromCartesian(cartesian);
  return { lat: C.Math.toDegrees(c.latitude), lon: C.Math.toDegrees(c.longitude) };
}
