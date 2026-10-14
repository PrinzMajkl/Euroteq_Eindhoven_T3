// Incident report (print / save as PDF) and samples CSV download.
import { CONFIG } from './config.js';
import { state, fmt } from './store.js';
import { toGlobe, toLatLon } from './geo.js';
import { likelySource, aboveLimitSeconds } from './panels.js';

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const dateTime = (epoch) => new Date(epoch * 1000).toLocaleString('en-GB', {
  day: 'numeric', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit',
});

export function downloadCsv(toast) {
  const s = state;
  if (!s.samples.length) { toast('No samples yet. Start a replay or connect the robot.'); return; }
  const rows = [['sample_id', 'time', 'arena_x_m', 'arena_y_m', 'latitude', 'longitude',
    'ammonia_nh3_n_mg_l', 'times_legal_limit', 'above_limit', 'oxygen_mg_l', 'sensor']];
  for (const p of s.samples) {
    const ll = toLatLon(toGlobe(p.x, p.y));
    rows.push([p.sample_id, new Date(p.timestamp * 1000).toISOString(), p.x, p.y,
      ll.lat.toFixed(6), ll.lon.toFixed(6), p.nh3_n_mg_l, (p.nh3_n_mg_l / CONFIG.AMMONIA_LIMIT).toFixed(2),
      p.nh3_n_mg_l >= CONFIG.AMMONIA_LIMIT ? 'yes' : 'no', p.do_mg_l, p.sensor_type || 'SYNTHETIC_POSITION_BASED']);
  }
  const csv = rows.map((r) => r.join(',')).join('\n');
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }));
  a.download = `plumetrace_samples_${new Date(s.samples[0].timestamp * 1000).toISOString().slice(0, 16).replace(/[:T]/g, '-')}.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  toast(`Downloaded ${s.samples.length} samples as CSV.`);
}

export function openReport(toast) {
  const s = state;
  if (!s.samples.length) { toast('No samples yet. Start a replay or connect the robot.'); return; }
  const L = CONFIG.AMMONIA_LIMIT;
  const first = s.samples[0], last = s.samples[s.samples.length - 1];
  const exceed = s.samples.filter((p) => p.nh3_n_mg_l >= L);
  const src = likelySource(s);
  const peakLL = s.peak ? toLatLon(toGlobe(s.peak.x, s.peak.y)) : null;
  const mode = s.twin && s.twin.mission && s.twin.mission.mode;
  const confirmed = mode === 'COMPLETED';

  let summary;
  if (!exceed.length) {
    summary = `The robot took ${s.samples.length} samples between ${fmt.hm(first.timestamp)} and ${fmt.hm(last.timestamp)}. Ammonia stayed within the legal limit of ${L} mg/L the whole time.`;
  } else {
    summary = `Ammonia above the legal limit was found in the Pegnitz. The highest reading was ${fmt.mg(s.peak.nh3_n_mg_l)} mg/L at ${fmt.hm(s.peak.timestamp)}, ${fmt.times(s.peak.nh3_n_mg_l)} the limit of ${L} mg/L.`;
    if (src) summary += ` The most likely source is ${src.outfall.name} (${src.outfall.note.toLowerCase()}), about ${Math.round(src.dist)} m from the highest reading.`;
    summary += confirmed ? ' The robot returned to the hotspot and confirmed the location.' : ' The hotspot has not been confirmed by a second visit yet.';
  }

  const facts = [
    ['Patrol period', `${dateTime(first.timestamp)} to ${fmt.hm(last.timestamp)}`],
    ['Samples taken', `${s.samples.length} (${exceed.length} above the limit)`],
    ['Highest ammonia', s.peak ? `${fmt.mg(s.peak.nh3_n_mg_l)} mg/L (${fmt.times(s.peak.nh3_n_mg_l)} the limit) at ${fmt.clock(s.peak.timestamp)}` : '–'],
    ['Location of highest reading', peakLL ? `${peakLL.lat.toFixed(5)} N, ${peakLL.lon.toFixed(5)} E` : '–'],
    ['First above the limit', s.firstExceed ? fmt.clock(s.firstExceed.timestamp) : 'Not exceeded'],
    ['Time above the limit', exceed.length ? fmt.dur(aboveLimitSeconds(s)) : '–'],
    ['Lowest oxygen', s.lowDo ? `${s.lowDo.do_mg_l.toFixed(1)} mg/L at ${fmt.clock(s.lowDo.timestamp)}` : '–'],
    ['Most likely source', src ? `${src.outfall.name}, ${src.outfall.note} (about ${Math.round(src.dist)} m away)` : '–'],
    ['Hotspot confirmed by robot', confirmed ? 'Yes, robot returned and arrival was verified' : 'No'],
  ];

  const topSamples = [...exceed].sort((a, b) => b.nh3_n_mg_l - a.nh3_n_mg_l).slice(0, 8);
  const events = [...s.alerts].reverse();

  $('report-body').innerHTML = `
    <div class="r-head">
      <div>
        <h1 id="r-title">Pollution incident report</h1>
        <p class="r-sub">PlumeTrace river monitoring, Pegnitz in Nürnberg. Created ${esc(dateTime(Date.now() / 1000))}.</p>
      </div>
      <img src="assets/logo.jpeg" alt="PlumeTrace">
    </div>
    <p class="r-summary">${esc(summary)}</p>
    <h2>Key facts</h2>
    <table><tbody>${facts.map(([k, v]) => `<tr><th>${esc(k)}</th><td>${esc(v)}</td></tr>`).join('')}</tbody></table>
    ${topSamples.length ? `<h2>Highest readings</h2>
    <table><thead><tr><th>Sample</th><th>Time</th><th class="num">Ammonia (mg/L)</th><th class="num">Times limit</th><th class="num">Oxygen (mg/L)</th></tr></thead>
    <tbody>${topSamples.map((p) => `<tr><td>${p.sample_id}</td><td>${fmt.clock(p.timestamp)}</td><td class="num">${fmt.mg(p.nh3_n_mg_l)}</td><td class="num">${fmt.times(p.nh3_n_mg_l)}</td><td class="num">${p.do_mg_l.toFixed(1)}</td></tr>`).join('')}</tbody></table>` : ''}
    ${s.requests.length ? `<h2>Inspection requests</h2>
    <table><thead><tr><th>Request</th><th>Time</th><th>Reason</th><th>Status</th></tr></thead>
    <tbody>${s.requests.map((q) => `<tr><td>${esc(q.id)} ${esc(q.what)}</td><td>${fmt.hm(q.time)}</td><td>${esc(q.reason || '–')}</td><td>${esc(q.label)}</td></tr>`).join('')}</tbody></table>` : ''}
    <h2>Mission timeline</h2>
    <table><tbody>${events.map((e) => `<tr><td style="width:70px">${fmt.clock(e.time)}</td><td>${esc(e.text)}</td></tr>`).join('')}</tbody></table>
    <p class="r-note">Legal limit: ${L} mg/L ammonia nitrogen (acute limit, German OGewV). Prototype notice: readings are simulated from the robot's position in a lab arena that stands in for this stretch of the Pegnitz, and the likely source is the outfall nearest the highest reading. Full sample data is available as CSV from the dashboard.</p>`;
  $('report').hidden = false;
  $('r-close').focus();
}

export function initReport(toast) {
  $('btn-csv').addEventListener('click', () => downloadCsv(toast));
  $('btn-report').addEventListener('click', () => openReport(toast));
  $('r-close').addEventListener('click', () => { $('report').hidden = true; });
  $('r-print').addEventListener('click', () => window.print());
  $('report').addEventListener('click', (e) => { if (e.target.id === 'report') $('report').hidden = true; });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') $('report').hidden = true; });
}
