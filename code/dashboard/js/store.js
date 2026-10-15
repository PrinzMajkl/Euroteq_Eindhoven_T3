// Mission state built from gateway messages ({t, topic, data}).
import { CONFIG } from './config.js';

const listeners = new Set();
export function onChange(fn) { listeners.add(fn); }

let scheduled = false;
export function changed() {
  if (scheduled) return;
  scheduled = true;
  requestAnimationFrame(() => { scheduled = false; listeners.forEach((fn) => fn(state)); });
}

function fresh() {
  return {
    robot: null,          // latest /robot_status
    twin: null,           // latest /digital_twin_state
    samples: [],          // /pollution samples
    sampleIds: new Set(),
    trail: [],            // [{x, y}]
    waypoint: null,       // latest /twin_waypoint
    navEvent: null,       // latest /twin_mission_event
    alerts: [],           // newest first: {time, text, level}
    requests: [],         // dashboard requests
    peak: null,           // highest sample
    firstExceed: null,    // first sample above limit
    lastExceed: null,     // last sample above limit
    lowDo: null,          // lowest oxygen sample
    flags: {},            // one-time alert switches
    lastMode: null,
    lastMsgAt: null,      // performance.now() of last message
    clock: null,          // epoch seconds of the latest message
  };
}

export let state = fresh();

export function reset() {
  const requests = state.requests; // keep the request log across replays
  state = fresh();
  state.requests = requests;
  changed();
}

export function alert(text, level = 'info', time = state.clock) {
  state.alerts.unshift({ time: time ?? Date.now() / 1000, text, level });
  if (state.alerts.length > 60) state.alerts.length = 60;
}

export const fmt = {
  mg: (v) => (v == null ? '–' : v < 10 ? v.toFixed(2) : v.toFixed(1)),
  times: (v) => {
    const r = v / CONFIG.AMMONIA_LIMIT;
    return r < 10 ? `${r.toFixed(1)}×` : `${Math.round(r)}×`;
  },
  clock: (epoch) => (epoch == null ? '--:--'
    : new Date(epoch * 1000).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit' })),
  hm: (epoch) => (epoch == null ? '--:--'
    : new Date(epoch * 1000).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })),
  dur: (sec) => {
    if (sec == null || !isFinite(sec)) return '–';
    const m = Math.floor(sec / 60), s = Math.round(sec % 60);
    return m ? `${m} min ${s} s` : `${s} s`;
  },
};

const MODE_TEXT = {
  BASELINE_ROUTE: 'patrolling',
  PAUSED_FOR_ANALYSIS: 'analysing',
  ROUTING_TO_HOTSPOT: 'going to the hotspot',
  COMPLETED: 'completed',
  FAILED: 'stopped with a problem',
  STOPPED: 'stopped',
};

const NAV_TEXT = {
  ACCEPTED: ['Navigation accepted the route. The robot is moving.', 'ok'],
  ARRIVED: ['Robot reached the target point.', 'done'],
  FAILED: ['Navigation could not reach the target.', 'alert'],
  REJECTED: ['Navigation refused the target point.', 'alert'],
  NAV2_UNAVAILABLE: ['Navigation system is not running, so the robot cannot drive to the target.', 'alert'],
  TIMEOUT: ['Robot took too long to reach the target.', 'alert'],
};

export function process(msg) {
  const { topic, data } = msg;
  if (data && typeof data === 'object' && typeof data.timestamp === 'number') {
    state.clock = data.timestamp;
  }
  state.lastMsgAt = performance.now();

  switch (topic) {
    case '/robot_status': onRobot(data); break;
    case '/pollution': onSample(data); break;
    case '/digital_twin_state': onTwin(data); break;
    case '/twin_waypoint':
      state.waypoint = data;
      if (data && data.basis === 'DASHBOARD_REQUEST') {
        const q = state.requests.find((r) => r.topics && r.topics.includes('/twin_waypoint') && r.status === 'sent');
        if (q) q.navActive = true;
      }
      if (data && data.basis === 'PEAK_MEASUREMENT_PROXY') {
        alert('Digital twin sent the robot back to the point with the highest reading.', 'alert');
      } else {
        alert('Robot was sent to the requested inspection point.', 'ok');
      }
      break;
    case '/navigation_decision':
      if (data === 'PAUSE') alert('Robot paused so the twin can analyse the readings.', 'warn');
      if (data === 'STOP') alert('Robot stopped.', 'info');
      break;
    case '/twin_mission_event':
      state.navEvent = data;
      if (data && NAV_TEXT[data.status]) alert(...NAV_TEXT[data.status]);
      updateRequestsFromNav(data);
      break;
    default:
      break;
  }
  changed();
}

function onRobot(r) {
  if (!r) return;
  state.robot = r;
  if (r.x == null || r.y == null) return;
  const last = state.trail[state.trail.length - 1];
  if (!last || Math.hypot(r.x - last.x, r.y - last.y) > 0.03) {
    state.trail.push({ x: r.x, y: r.y });
    if (state.trail.length > 5000) state.trail.shift();
  }
  if (r.battery_percent != null && r.battery_percent < 20 && !state.flags.batt) {
    state.flags.batt = true;
    alert(`Robot battery is low (${Math.round(r.battery_percent)}%).`, 'warn');
  }
  for (const q of state.requests) {
    if (q.type === 'stop' && q.status === 'sent' && r.status === 'STOPPED_BY_TWIN') {
      setRequest(q, 'done', 'Robot stopped');
    }
  }
}

function onSample(s) {
  if (!s || state.sampleIds.has(s.sample_id)) return;
  state.sampleIds.add(s.sample_id);
  state.samples.push(s);
  const a = s.nh3_n_mg_l, d = s.do_mg_l;

  if (!state.peak || a > state.peak.nh3_n_mg_l) state.peak = s;
  if (!state.lowDo || d < state.lowDo.do_mg_l) state.lowDo = s;

  if (a >= CONFIG.AMMONIA_LIMIT) {
    if (!state.firstExceed) {
      state.firstExceed = s;
      alert(`Ammonia above the legal limit: ${fmt.mg(a)} mg/L (${fmt.times(a)} the limit).`, 'alert', s.timestamp);
    }
    state.lastExceed = s;
    if (a >= CONFIG.AMMONIA_LIMIT * 8 && !state.flags.x8) {
      state.flags.x8 = true;
      alert(`Very high ammonia: ${fmt.mg(a)} mg/L, ${fmt.times(a)} the limit. Likely raw sewage.`, 'alert', s.timestamp);
    }
  } else if (state.firstExceed && !state.flags.clean && a < 0.1) {
    state.flags.clean = true;
    alert('Robot is back in clean water.', 'ok', s.timestamp);
  }
  if (d < CONFIG.OXYGEN_LOW && !state.flags.lowDo) {
    state.flags.lowDo = true;
    alert(`Oxygen is low for fish: ${d.toFixed(1)} mg/L.`, 'warn', s.timestamp);
  }
  if (d < CONFIG.OXYGEN_CRITICAL && !state.flags.critDo) {
    state.flags.critDo = true;
    alert(`Oxygen is critical: ${d.toFixed(1)} mg/L. Fish may die.`, 'alert', s.timestamp);
  }
}

function onTwin(t) {
  if (!t) return;
  state.twin = t;
  const mode = t.mission && t.mission.mode;
  if (mode && mode !== state.lastMode) {
    if (state.lastMode) {
      if (mode === 'COMPLETED') alert('Mission complete. The hotspot is confirmed and the report is ready.', 'done');
      else if (mode === 'FAILED') alert('Mission stopped with a problem. See the latest navigation event.', 'alert');
      else if (mode === 'PAUSED_FOR_ANALYSIS') alert('Plume passed. The twin is choosing where pollution was strongest.', 'warn');
    } else {
      alert(`Digital twin data received. The robot is ${MODE_TEXT[mode] || mode}.`, 'info');
    }
    state.lastMode = mode;
  }
  // Fallback when /pollution is not forwarded: build samples from twin state.
  const sid = t.synchronization && t.synchronization.last_sample_id;
  if (sid != null && !state.sampleIds.has(sid) && t.environment && t.environment.nh3_n_mg_l != null
      && t.robot && t.robot.x != null) {
    onSample({
      sample_id: sid, timestamp: t.timestamp, x: t.robot.x, y: t.robot.y,
      nh3_n_mg_l: t.environment.nh3_n_mg_l, do_mg_l: t.environment.do_mg_l,
    });
  }
}

// ---- requests ----
export function addRequest(q) {
  state.requests.unshift(q);
  changed();
}

export function setRequest(q, status, label) {
  q.status = status;
  q.label = label;
  changed();
}

export function ackRequest(ack) {
  const q = state.requests.find((r) => r.id === ack.id);
  if (!q) return;
  if (!ack.delivered) { setRequest(q, 'failed', `Not delivered: ${ack.reason}`); return; }
  q.topics = ack.topics;
  if (q.type === 'stop') setRequest(q, 'sent', 'Stop sent to robot');
  else if (ack.topics.includes('/twin_waypoint')) setRequest(q, 'sent', 'Sent to robot');
  else setRequest(q, 'sent', 'Sent to the digital twin');
}

function updateRequestsFromNav(e) {
  const q = state.requests.find((r) => r.navActive && (r.status === 'sent' || r.status === 'moving'));
  if (!q || !e) return;
  if (e.status === 'ACCEPTED') setRequest(q, 'moving', 'Robot on its way');
  else if (e.status === 'ARRIVED') { q.navActive = false; setRequest(q, 'done', 'Robot arrived at the spot'); }
  else if (NAV_TEXT[e.status]) { q.navActive = false; setRequest(q, 'failed', NAV_TEXT[e.status][0]); }
}
