// Right rail, top bar and replay bar rendering.
import { CONFIG } from './config.js';
import { fmt } from './store.js';
import { riverDistance } from './geo.js';
import { highlightOutfall } from './map.js';

const $ = (id) => document.getElementById(id);
const Chart = window.Chart;

// ---------------- Status sentence ----------------
function statusFor(s) {
  const t = s.twin, r = s.robot;
  const mode = t && t.mission && t.mission.mode;
  const a = s.samples.length ? s.samples[s.samples.length - 1].nh3_n_mg_l : null;
  if (!t && !r) return null;
  const robotStatus = (r && r.status) || '';
  if (robotStatus === 'STOPPED_BY_TWIN' && mode !== 'COMPLETED' && mode !== 'FAILED') {
    return ['Stopped', 'The robot has stopped and is waiting.', 'fail'];
  }
  switch (mode) {
    case 'PAUSED_FOR_ANALYSIS':
      return ['Analysing', 'The robot has passed the pollution. The digital twin is working out where it was strongest.', 'warn'];
    case 'ROUTING_TO_HOTSPOT':
      return ['Going to the hotspot', 'The robot is driving back to the spot with the highest pollution to confirm it.', 'alert'];
    case 'COMPLETED':
      return ['Mission complete', 'Pollution hotspot confirmed. The incident report is ready to download.', 'done'];
    case 'FAILED': {
      const ev = t.mission.last_nav2_event;
      const why = ev && ev.status === 'NAV2_UNAVAILABLE' ? ' The navigation system is not running.' : '';
      return ['Needs attention', `The mission stopped before the robot reached its target.${why}`, 'fail'];
    }
    case 'STOPPED':
      return ['Stopped', 'The mission was stopped.', 'fail'];
    default:
      if (a != null && a >= CONFIG.AMMONIA_LIMIT) {
        return ['Pollution detected', 'The robot is inside polluted water and keeps measuring to find where it is strongest.', 'alert'];
      }
      if (s.firstExceed) {
        return ['Patrolling', 'The robot left the polluted water and is checking that the water is clean again.', 'warn'];
      }
      if (!s.samples.length) return ['Starting', 'The robot is starting its patrol. The first water sample will appear shortly.', 'ok'];
      return ['Patrolling', 'The robot is following its route and measuring the water. Everything is within limits.', 'ok'];
  }
}

// ---------------- Charts ----------------
let chartNh3, chartDo, chartLen = -1;
const axisColor = '#5f7a8b';
const gridColor = '#eef2f6';

function baseChart(canvas, color, yMax) {
  return new Chart(canvas, {
    type: 'line',
    data: { datasets: [
      { label: 'Measured', data: [], borderColor: color, borderWidth: 2, pointRadius: 0, pointHoverRadius: 5,
        pointHoverBackgroundColor: color, pointHoverBorderColor: '#fff', pointHoverBorderWidth: 2, tension: 0.25 },
      { label: 'Threshold', data: [], borderColor: axisColor, borderWidth: 1.5, borderDash: [5, 4], pointRadius: 0,
        pointHoverRadius: 0 },
    ] },
    options: {
      animation: false, maintainAspectRatio: false, parsing: false, normalized: true,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#023047', titleFont: { family: 'Calibri, Carlito, sans-serif' }, bodyFont: { family: 'Calibri, Carlito, sans-serif' },
          filter: (item) => item.datasetIndex === 0,
          callbacks: {
            title: (items) => (items.length ? fmt.clock(items[0].raw.epoch) : ''),
            label: (item) => ` ${item.parsed.y.toFixed(2)} mg/L`,
          },
        },
      },
      scales: {
        x: { type: 'linear', grid: { display: false }, border: { color: '#e2e8f0' },
          ticks: { color: axisColor, maxTicksLimit: 5, font: { family: 'Calibri, Carlito, sans-serif' },
            callback: (v) => { const m = Math.floor(v / 60); return `${m}:${String(Math.floor(v % 60)).padStart(2, '0')}`; } } },
        y: { beginAtZero: true, suggestedMax: yMax, grid: { color: gridColor }, border: { display: false },
          ticks: { color: axisColor, maxTicksLimit: 4, font: { family: 'Calibri, Carlito, sans-serif' } } },
      },
    },
  });
}

function updateCharts(s) {
  if (!chartNh3) {
    chartNh3 = baseChart($('chart-nh3'), '#fb8500', 1.5);
    chartDo = baseChart($('chart-do'), '#219ebc', 10);
  }
  if (s.samples.length === chartLen) return;
  chartLen = s.samples.length;
  const t0 = s.samples.length ? s.samples[0].timestamp : 0;
  const pts = (key) => s.samples.map((p) => ({ x: p.timestamp - t0, y: p[key], epoch: p.timestamp }));
  const span = s.samples.length ? Math.max(10, s.samples[s.samples.length - 1].timestamp - t0) : 10;
  const line = (v) => [{ x: 0, y: v }, { x: span, y: v }];
  chartNh3.data.datasets[0].data = pts('nh3_n_mg_l');
  chartNh3.data.datasets[1].data = line(CONFIG.AMMONIA_LIMIT);
  chartDo.data.datasets[0].data = pts('do_mg_l');
  chartDo.data.datasets[1].data = line(CONFIG.OXYGEN_LOW);
  chartNh3.options.scales.x.max = span;
  chartDo.options.scales.x.max = span;
  chartNh3.update('none');
  chartDo.update('none');
}

// ---------------- Findings ----------------
export function likelySource(s) {
  if (!s.peak || s.peak.nh3_n_mg_l < CONFIG.AMMONIA_LIMIT) return null;
  let best = null;
  for (const o of CONFIG.OUTFALLS) {
    const d = riverDistance(o, s.peak);
    if (!best || d < best.dist) best = { outfall: o, dist: d };
  }
  return best;
}

export function aboveLimitSeconds(s) {
  if (!s.firstExceed) return null;
  return s.lastExceed.timestamp - s.firstExceed.timestamp;
}

// ---------------- Render ----------------
let lastAlertsKey = '';
let lastSource = null;

export function render(s) {
  // Status
  const st = statusFor(s);
  const box = $('status');
  if (st) {
    $('status-mode').textContent = st[0];
    $('status-text').textContent = st[1];
    box.dataset.tone = st[2];
  }

  // Clock
  $('clock').textContent = fmt.hm(s.clock);

  // Tiles
  const last = s.samples[s.samples.length - 1];
  if (last) {
    const a = last.nh3_n_mg_l, d = last.do_mg_l;
    $('v-nh3').textContent = fmt.mg(a);
    const over = a >= CONFIG.AMMONIA_LIMIT;
    $('n-nh3').textContent = over ? `${fmt.times(a)} the legal limit` : 'Within the legal limit';
    $('tile-nh3').dataset.level = over ? 'high' : '';
    $('v-do').textContent = d.toFixed(1);
    const crit = d < CONFIG.OXYGEN_CRITICAL, low = d < CONFIG.OXYGEN_LOW;
    $('n-do').textContent = crit ? 'Critical: fish may die' : low ? 'Low for fish' : 'Healthy for fish';
    $('tile-do').dataset.level = crit ? 'high' : low ? 'warn' : '';
  }
  const n = s.samples.length;
  $('v-samples').textContent = n;
  const [lo, hi] = CONFIG.MANUAL_SAMPLE_COST;
  const eur = (v) => `€${Math.round(v).toLocaleString('en-GB')}`;
  $('n-samples').textContent = n ? `By hand this would cost ${eur(n * lo)} to ${eur(n * hi)}` : 'Manual sampling equivalent: €0';
  const r = s.robot;
  if (r && r.battery_percent != null) {
    $('v-batt').textContent = Math.round(r.battery_percent);
    $('n-batt').textContent = r.battery_estimated_remaining_min != null
      ? `About ${Math.round(r.battery_estimated_remaining_min)} min left${r.battery_is_simulated ? ' (estimate)' : ''}`
      : 'Live reading';
  }

  updateCharts(s);

  // Findings
  if (s.peak && s.peak.nh3_n_mg_l >= CONFIG.AMMONIA_LIMIT) {
    $('f-peak').innerHTML = `<strong>${fmt.mg(s.peak.nh3_n_mg_l)} mg/L</strong>, ${fmt.times(s.peak.nh3_n_mg_l)} the legal limit, at ${fmt.hm(s.peak.timestamp)}`;
  } else {
    $('f-peak').textContent = 'Nothing above the limit yet';
  }
  const src = likelySource(s);
  if (src) {
    $('f-source').innerHTML = `<strong>${src.outfall.name}</strong>, about ${Math.round(src.dist)} m from the highest reading (${src.outfall.note.toLowerCase()})`;
    highlightOutfall(src.outfall.id);
  } else {
    $('f-source').textContent = 'Not enough data yet';
    highlightOutfall(null);
  }
  const dur = aboveLimitSeconds(s);
  $('f-duration').textContent = dur == null ? '–' : `${fmt.dur(dur)} of the patrol (${s.samples.filter((p) => p.nh3_n_mg_l >= CONFIG.AMMONIA_LIMIT).length} samples)`;

  // Alerts
  const key = s.alerts.length + ':' + (s.alerts[0] ? s.alerts[0].text : '');
  if (key !== lastAlertsKey) {
    lastAlertsKey = key;
    const list = $('alerts');
    list.innerHTML = '';
    if (!s.alerts.length) list.innerHTML = '<li class="empty">Nothing yet.</li>';
    for (const al of s.alerts) {
      const li = document.createElement('li');
      li.dataset.level = al.level;
      li.innerHTML = `<span class="a-time">${fmt.hm(al.time)}</span><span class="a-text"></span>`;
      li.querySelector('.a-text').textContent = al.text;
      list.appendChild(li);
    }
  }
}

export function renderSource(src, rp, s) {
  for (const b of document.querySelectorAll('.source-btn')) {
    b.setAttribute('aria-checked', String(b.dataset.source === src.kind));
  }
  const link = $('link');
  let text = '', state = '';
  if (src.kind === 'replay') {
    text = rp.name ? `Replay: ${rp.name === 'demo_run.jsonl' ? 'demo mission' : rp.name}` : 'Replay';
    state = 'replay';
  } else if (src.link === 'ok') {
    const age = s && s.lastMsgAt ? (performance.now() - s.lastMsgAt) / 1000 : null;
    if (!src.ros) { text = 'Gateway running, ROS 2 not found'; state = 'warn'; }
    else if (age == null || age > 5) { text = 'Connected, waiting for robot data'; state = 'warn'; }
    else { text = 'Live: robot connected'; state = 'ok'; }
  } else if (src.link === 'connecting') {
    text = 'Connecting to gateway…'; state = 'warn';
  } else {
    text = 'Gateway not reachable. Is gateway_node.py running?'; state = 'down';
  }
  $('link-text').textContent = text;
  link.dataset.state = state;

  // Replay bar
  const bar = $('replay');
  bar.hidden = src.kind !== 'replay';
  if (src.kind === 'replay') {
    $('rp-play').textContent = rp.playing ? '❚❚' : '▶';
    $('rp-play').title = rp.playing ? 'Pause' : 'Play';
    const mmss = (v) => `${Math.floor(v / 60)}:${String(Math.floor(v % 60)).padStart(2, '0')}`;
    $('rp-time').textContent = `${mmss(rp.pos)} / ${mmss(rp.duration)}`;
    if (document.activeElement !== $('rp-seek')) {
      $('rp-seek').value = rp.duration ? Math.round((rp.pos / rp.duration) * 1000) : 0;
    }
  }
  if (lastSource !== src.kind) {
    lastSource = src.kind;
  }
}
