/* PlumeTrace authority view: a plain-language page for the water authorities.
   Same gateway messages as index.html (schema.json); live through the gateway or tools/relay.py,
   or Replay of a recorded mission (data/replay_*.jsonl, tools/make_authority_replay.py).
   It never contacts anyone: notifications and actions are recorded with a time stamp only. */
(function () {
  'use strict';
  const CFG = window.PLUMETRACE_CONFIG || {};
  const R = window.PEGNITZ_RESPONSE || {};
  const TH = Object.assign({ nh3_n_elevated: 0.3, nh3_n_alert: 0.6, nh3_n_severe: 2.0, do_low: 6.0, do_critical: 4.0 }, R.thresholds || {});
  const MANUAL_COST = [439, 828];  // EUR per manual grab sample (team cost study)
  const REPLAYS = [
    { file: 'data/replay_B.jsonl', name: 'Recorded mission: outfall B' },
    { file: 'data/replay_A.jsonl', name: 'Recorded mission: outfall A' },
    { file: 'data/replay_C.jsonl', name: 'Recorded mission: outfall C' },
  ];
  const BIN_COLORS = ['#8ecae6', '#ffb703', '#fb8500', '#b54700'];
  const BIN_NAMES = ['Normal', 'Elevated', 'Above legal limit', 'Severe'];
  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const isNum = (v) => typeof v === 'number' && isFinite(v);
  const hm = (ms) => (ms == null ? '--:--' : new Date(ms).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' }));
  const hms = (ms) => (ms == null ? '--:--:--' : new Date(ms).toLocaleTimeString('en-GB'));
  const mg = (v) => (v == null ? '–' : v < 10 ? v.toFixed(2) : v.toFixed(1));
  const times = (v) => { const r = v / TH.nh3_n_alert; return r < 10 ? r.toFixed(1) + '×' : Math.round(r) + '×'; };
  const bin = (v) => (v >= TH.nh3_n_severe ? 3 : v >= TH.nh3_n_alert ? 2 : v >= TH.nh3_n_elevated ? 1 : 0);
  const pct = (p) => Math.round(p * 100) + ' %';

  // ------------------------------------------------------------------ state
  let S;
  function fresh() {
    return {
      hello: null, mission: null, post: null, done: null, battery: null, sync: null,
      samples: [], trail: [], pose: null, plume: null, activity: null, lastAt: null,
      log: [], peak: null, minDo: null, firstAlert: null,
      incident: null,  // {openedAt, notified: {tier: at}, actions: {i: at}}
      flags: {},
    };
  }
  S = fresh();
  const REQUESTS = [];  // kept across replays and reconnects
  const listeners = [];
  let raf = 0;
  function changed() { if (!raf) raf = requestAnimationFrame(() => { raf = 0; listeners.forEach((f) => f()); }); }

  function log(text, level = 'info', at = S.lastAt || Date.now()) {
    S.log.unshift({ at, text, level });
    if (S.log.length > 80) S.log.length = 80;
  }

  // ------------------------------------------------------------------ messages
  const H = {
    hello(m) {
      S.hello = m;
      if (m.reach) $('reach-name').textContent = m.reach;
      log(m.replay ? 'Recorded mission loaded.' : 'Connected to the digital twin.', 'info');
    },
    mission(m) {
      const prev = S.mission && S.mission.state;
      S.mission = m;
      if (prev && prev !== m.state) {
        if (m.state === 'RUNNING') log('Mission started: the robot is surveying the river bank.', 'ok');
        if (m.state === 'HOLD') log('Mission paused (link or position lost). It resumes by itself.', 'warn');
        if (m.state === 'ABORTED') log('Mission stopped before the source was found.', 'alert');
      }
    },
    pose(m) {
      S.pose = m;
      // trail only while surveying the bank: the start mark lies far off the river at 1:100
      if (!S.surveying) return;
      const last = S.trail[S.trail.length - 1];
      if (!last || Math.abs(last[0] - m.lat) + Math.abs(last[1] - m.lon) > 2e-6) S.trail.push([m.lat, m.lon]);
      if (S.trail.length > 4000) S.trail.shift();
    },
    sample(m) {
      if (S.samples.some((s) => s.seq === m.seq && s.t === m.t)) return;  // relay replay duplicate
      m.at = S.lastAt;
      S.samples.push(m);
      const a = m.nh3_n_mg_l, d = m.do_mg_l;
      if (!S.peak || a > S.peak.nh3_n_mg_l) S.peak = m;
      if (isNum(d) && (!S.minDo || d < S.minDo.do_mg_l)) S.minDo = m;
      if (a >= TH.nh3_n_alert) {
        if (!S.firstAlert) {
          S.firstAlert = m;
          log(`Ammonia above the legal limit: ${mg(a)} mg/L, ${times(a)} the limit.`, 'alert');
        }
        if (a >= TH.nh3_n_severe && !S.flags.severe) { S.flags.severe = true; log(`Severe ammonia level: ${mg(a)} mg/L. Risk to fish.`, 'alert'); }
        openIncident();
      }
      if (isNum(d) && d < TH.do_critical && !S.flags.doc) { S.flags.doc = true; log(`Oxygen critical: ${d.toFixed(1)} mg/L. Fish kill risk.`, 'alert'); openIncident(); }
      else if (isNum(d) && d < TH.do_low && !S.flags.dol) { S.flags.dol = true; log(`Oxygen low for fish: ${d.toFixed(1)} mg/L.`, 'warn'); }
    },
    posterior(m) {
      const prevLead = S.post ? lead(S.post) : null;
      S.post = m;
      const l = lead(m);
      if (S.samples.length && l.p >= 0.5 && (!prevLead || prevLead.label !== l.label || (prevLead.p < 0.9 && l.p >= 0.9))) {
        log(`Most likely source now: Outfall ${l.label} (${pct(l.p)}).`, l.p >= 0.9 ? 'alert' : 'warn');
      }
    },
    plume_points(m) { S.plume = m.points; },
    alert(m) { openIncident(); },
    event(m) {
      const d = m.data || {};
      const act = activity(m.kind, d);
      if (act) S.activity = act;
      if (m.kind === 'goal_result' && +d.status === 4) S.surveying = true;
      if (m.kind === 'done' || m.kind === 'return_home_start' || m.kind === 'abort') S.surveying = false;
      if (m.kind === 'done') {
        const probs = d.probabilities || (S.post && S.post.probabilities) || [];
        const labels = (S.post && S.post.labels) || ['A', 'B', 'C'];
        const i = labels.indexOf(d.map_label);
        S.done = { label: d.map_label, p: i >= 0 && isNum(probs[i]) ? probs[i] : null, samples: d.samples, at: S.lastAt };
        log(`Source confirmed: Outfall ${d.map_label}${S.done.p != null ? ` (${pct(S.done.p)})` : ''} after ${d.samples ?? '?'} samples.`, 'done');
        if (S.incident) S.incident.confirmed = d.map_label;
      } else if (m.kind === 'return_home') {
        log(+d.status === 4 ? 'Robot is back at its start point.' : 'Robot could not drive home.', +d.status === 4 ? 'ok' : 'warn');
      } else if (m.kind === 'abort') {
        log('Mission aborted.', 'alert');
      } else if (m.kind === 'battery_low') {
        log('Robot battery low.', 'warn');
      }
    },
    battery(m) { S.battery = m; },
    sync(m) { S.sync = m; },
    ack(m) { onAck(m); },
  };

  function lead(p) {
    let k = 0;
    p.probabilities.forEach((v, i) => { if (v > p.probabilities[k]) k = i; });
    return { label: p.labels[k], p: p.probabilities[k] };
  }

  function activity(kind, d) {
    switch (kind) {
      case 'goal_sent': return 'driving to the next sampling point';
      case 'goal_result': return +d.status === 4 ? 'arrived at the sampling point' : 'could not reach the sampling point';
      case 'dwell': return 'taking a water sample (3 s)';
      case 'sample': return `sample #${d.seq ?? '?'} done${isNum(d.nh3) ? `: ${mg(d.nh3)} mg/L` : ''}`;
      case 'hold': return 'paused';
      case 'resume': return 'resumed';
      case 'return_home_start': return 'driving back to the start point';
      case 'return_home': return +d.status === 4 ? 'back at the start point' : 'could not drive home';
      case 'done': return 'mission finished';
      default: return null;
    }
  }

  function openIncident() {
    if (S.incident) return;
    S.incident = { openedAt: S.lastAt, notified: {}, actions: {} };
    log('Incident opened. See "Response" for who to notify.', 'alert');
  }

  function receive(m, at) {
    S.lastAt = at;
    const fn = H[m && m.type];
    if (fn) { try { fn(m); } catch (e) { console.error('handler', m.type, e); } }
    changed();
  }

  // ------------------------------------------------------------------ map
  const L = window.L;
  const map = L.map('map', { zoomControl: false, zoomSnap: 0.25, maxZoom: 21, preferCanvas: true });
  L.control.zoom({ position: 'topright' }).addTo(map);
  const street = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 21, maxNativeZoom: 19, attribution: '© OpenStreetMap contributors' });
  const sat = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    { maxZoom: 21, maxNativeZoom: 19, attribution: 'Imagery © Esri, Maxar, Earthstar Geographics' });
  sat.addTo(map);
  L.control.layers({ Satellite: sat, 'Street map': street }, null, { position: 'topright', collapsed: false }).addTo(map);
  for (const [n, z] of [['water', 405], ['plume', 410], ['trail', 420], ['samples', 430], ['marks', 640], ['robot', 650]]) map.createPane(n).style.zIndex = z;
  map.setView([49.4557, 11.0535], 17);

  const pinSvg = (fill) => `<svg xmlns="http://www.w3.org/2000/svg" width="28" height="36" viewBox="0 0 28 36"><path d="M14 35C14 35 2 21 2 13a12 12 0 0 1 24 0c0 8-12 22-12 22z" fill="${fill}" stroke="#fff" stroke-width="2.5"/><circle cx="14" cy="13" r="4.5" fill="#fff"/></svg>`;
  const pinIcon = (fill) => L.divIcon({ html: pinSvg(fill), className: 'pin', iconSize: [28, 36], iconAnchor: [14, 35], tooltipAnchor: [0, -34] });
  const robotIcon = (deg) => L.divIcon({ className: 'robot-icon', iconSize: [34, 34], iconAnchor: [17, 17],
    html: `<svg width="34" height="34" viewBox="0 0 34 34"><g transform="rotate(${deg} 17 17)"><circle cx="17" cy="17" r="10" fill="#023047" stroke="#fff" stroke-width="3"/><path d="M17 3l5 8h-10z" fill="#023047" stroke="#fff" stroke-width="1.5"/></g></svg>` });

  let waterBounds = null;
  const outfallMk = {};
  const outfallInfo = {};
  let srcRing = null;
  fetch('data/water_area.geojson').then((r) => r.json()).then((g) => {
    const lay = L.geoJSON(g, { pane: 'water', style: { color: '#219ebc', weight: 2, fillColor: '#219ebc', fillOpacity: 0.18 } }).addTo(map);
    lay.bindTooltip('Monitored reach of the Pegnitz (the lab arena is a 1:100 model of it)', { sticky: true, className: 'lbl lbl-info' });
    waterBounds = lay.getBounds();
    fit();
  }).catch(() => toast('Could not load the river outline (data/water_area.geojson).'));
  fetch('data/outfalls.geojson').then((r) => r.json()).then((g) => {
    for (const f of g.features) {
      const id = f.properties.id, [lon, lat] = f.geometry.coordinates;
      outfallInfo[id] = { lat, lon, bank: f.properties.bank, synthetic: f.properties.position === 'synthetic' };
      outfallMk[id] = L.marker([lat, lon], { pane: 'marks', icon: pinIcon('#023047') })
        .bindTooltip(`Outfall ${id}`, { direction: 'top', className: 'lbl lbl-perm', permanent: true })
        .bindPopup(`<strong>Outfall ${esc(id)}</strong><br>${esc(f.properties.bank || '')} bank${f.properties.position === 'synthetic' ? '<br>Illustrative position (model, not a real overflow site)' : ''}`)
        .addTo(map);
    }
    changed();
  }).catch(() => {});
  fetch('data/stations.geojson').then((r) => r.json()).then((g) => {
    for (const f of g.features) {
      const [lon, lat] = f.geometry.coordinates;
      L.marker([lat, lon], { pane: 'marks', icon: L.divIcon({ className: 'pin', iconSize: [14, 14], iconAnchor: [7, 7],
        html: '<svg width="14" height="14"><rect x="3" y="3" width="8" height="8" transform="rotate(45 7 7)" fill="#219ebc" stroke="#fff" stroke-width="1.5"/></svg>' }) })
        .bindTooltip(`${esc(f.properties.name)} (${f.properties.kind === 'gauge' ? 'water level gauge' : 'water quality station'})`, { className: 'lbl lbl-info' })
        .addTo(map);
    }
  }).catch(() => {});

  function fit() {
    if (!waterBounds) return;
    const panel = document.querySelector('.requests');
    const left = panel && !panel.classList.contains('collapsed') ? panel.offsetWidth + 30 : 30;
    map.fitBounds(waterBounds, { paddingTopLeft: [left, 70], paddingBottomRight: [30, 90], maxZoom: 19 });
  }
  map.on('zoomend', () => $('map').classList.toggle('labels-off', map.getZoom() < 16.5));

  const trail = L.polyline([], { pane: 'trail', color: '#023047', weight: 3, opacity: 0.55 }).addTo(map);
  const robot = L.marker([0, 0], { pane: 'robot', icon: robotIcon(0) });
  robot.bindTooltip('Robot', { direction: 'right', offset: [14, 0], className: 'lbl lbl-perm', permanent: true });
  const sampleLayer = L.layerGroup().addTo(map);
  const plumeLayer = L.layerGroup().addTo(map);
  const reqLayer = L.layerGroup().addTo(map);
  const pickMk = L.marker([0, 0], { pane: 'marks', icon: pinIcon('#ffb703') }).bindTooltip('New request', { direction: 'top', className: 'lbl', permanent: true });
  let drawn = { samples: 0, trail: -1, plume: null, heading: null, highlight: '' };
  let follow = false, showPlume = true;

  function drawMap() {
    if (S.pose) {
      robot.setLatLng([S.pose.lat, S.pose.lon]);
      const hd = Math.round(S.pose.heading_deg || 0);
      if (hd !== drawn.heading) { robot.setIcon(robotIcon(hd)); drawn.heading = hd; }
      if (!map.hasLayer(robot)) robot.addTo(map);
      if (follow) map.panTo(robot.getLatLng(), { animate: false });
    } else if (map.hasLayer(robot)) robot.remove();
    if (S.trail.length !== drawn.trail) { trail.setLatLngs(S.trail); drawn.trail = S.trail.length; }
    if (S.samples.length < drawn.samples) { sampleLayer.clearLayers(); drawn.samples = 0; }
    for (let i = drawn.samples; i < S.samples.length; i++) {
      const s = S.samples[i], b = bin(s.nh3_n_mg_l);
      L.circleMarker([s.lat, s.lon], { pane: 'samples', radius: 8, color: '#fff', weight: 2, fillColor: BIN_COLORS[b], fillOpacity: 1 })
        .bindTooltip(`Sample ${s.seq}: ammonia ${mg(s.nh3_n_mg_l)} mg/L (${BIN_NAMES[b].toLowerCase()})${isNum(s.do_mg_l) ? `, oxygen ${s.do_mg_l.toFixed(1)} mg/L` : ''}`, { className: 'lbl lbl-info' })
        .addTo(sampleLayer);
    }
    drawn.samples = S.samples.length;
    if (S.plume !== drawn.plume || showPlume !== drawn.showPlume) {
      plumeLayer.clearLayers();
      drawn.plume = S.plume; drawn.showPlume = showPlume;
      if (showPlume && S.plume) {
        const bg = (S.hello && S.hello.scenario && S.hello.scenario.background_nh3_n_mg_l) || 0.05;
        for (const [lat, lon, c] of S.plume) {
          if (c < bg + 0.02) continue;
          const b = bin(c);
          L.circleMarker([lat, lon], { pane: 'plume', radius: 5, stroke: false, fillColor: b ? BIN_COLORS[b] : '#219ebc',
            fillOpacity: Math.min(0.75, 0.15 + c / (TH.nh3_n_severe * 1.6)), interactive: false }).addTo(plumeLayer);
        }
      }
    }
    // outfall highlight: leading candidate, or confirmed source
    const l = S.post && S.samples.length ? lead(S.post) : null;
    const key = S.done ? 'done:' + S.done.label : l && l.p >= 0.5 ? 'lead:' + l.label : '';
    if (key !== drawn.highlight) {
      drawn.highlight = key;
      for (const id of Object.keys(outfallMk)) {
        const isDone = S.done && S.done.label === id, isLead = !S.done && l && l.p >= 0.5 && l.label === id;
        outfallMk[id].setIcon(pinIcon(isDone ? '#b54700' : isLead ? '#fb8500' : '#023047'));
        outfallMk[id].setTooltipContent(isDone ? `Outfall ${id}: source confirmed` : isLead ? `Outfall ${id}: most likely` : `Outfall ${id}`);
        const tt = outfallMk[id].getTooltip();
        if (tt) { tt.options.className = isDone ? 'lbl lbl-src' : 'lbl lbl-perm'; outfallMk[id].closeTooltip(); outfallMk[id].openTooltip(); }
      }
      if (srcRing) { srcRing.remove(); srcRing = null; }
      if (S.done && outfallInfo[S.done.label]) {
        const o = outfallInfo[S.done.label];
        srcRing = L.marker([o.lat, o.lon], { pane: 'marks', interactive: false, icon: L.divIcon({ className: 'pin', iconSize: [60, 60], iconAnchor: [30, 30],
          html: '<svg width="60" height="60"><circle class="pulse" cx="30" cy="30" r="24" fill="none" stroke="#b54700" stroke-width="4"/></svg>' }) }).addTo(map);
      }
    }
    for (const q of REQUESTS) {
      if (q.lat == null || q.marker) continue;
      q.marker = L.marker([q.lat, q.lon], { pane: 'marks', icon: pinIcon('#ffb703') })
        .bindTooltip(`${q.id}: ${q.what}`, { direction: 'top', className: 'lbl' }).addTo(reqLayer);
    }
  }
  listeners.push(drawMap);

  let pickCb = null;
  map.on('click', (e) => {
    if (e.originalEvent.shiftKey) { toast(`Latitude ${e.latlng.lat.toFixed(6)}, longitude ${e.latlng.lng.toFixed(6)}`); return; }
    if (!pickCb) return;
    const cb = pickCb; pickCb = null;
    $('map').classList.remove('picking');
    pickMk.setLatLng(e.latlng).addTo(map);
    cb({ lat: e.latlng.lat, lon: e.latlng.lng });
  });

  // ------------------------------------------------------------------ rail
  function statusLine() {
    const st = S.mission && S.mission.state;
    const l = S.post && S.samples.length ? lead(S.post) : null;
    const polluted = S.samples.length && S.samples[S.samples.length - 1].nh3_n_mg_l >= TH.nh3_n_alert;
    if (!S.hello && !S.mission) return null;
    if (S.done) return ['Source confirmed', `Outfall ${S.done.label} is releasing ammonia into the Pegnitz. Notify the authorities and have the outfall checked.`, 'done'];
    switch (st) {
      case 'HOLD': return ['Paused', 'The robot lost its radio link or its position. The mission continues by itself when it is back.', 'warn'];
      case 'ABORTED': return ['Stopped', 'The mission was stopped before the source was found.', 'fail'];
      case 'DONE': return ['Mission finished', 'The survey is complete.', 'ok'];
      case 'RUNNING':
        if (l && l.p >= 0.5) return ['Pollution found', `Outfall ${l.label} is the most likely source so far (${pct(l.p)}). The robot keeps sampling to confirm.`, 'alert'];
        if (polluted || S.firstAlert) return ['Pollution found', 'Ammonia is above the legal limit. The robot keeps sampling to find where it comes from.', 'alert'];
        return ['Surveying', 'The robot is driving along the river bank and taking water samples. No pollution found yet.', 'ok'];
      default: return ['Ready', 'The robot is ready. No mission is running.', 'ok'];
    }
  }

  function renderRail() {
    const st = statusLine();
    if (st) { $('status-mode').textContent = st[0]; $('status-text').textContent = st[1]; $('status').dataset.tone = st[2]; }
    $('status-act').textContent = S.activity ? `Now: ${S.activity}` : '';
    $('clock').textContent = hm(S.lastAt);

    // outfall bars
    const labels = (S.post && S.post.labels) || ['A', 'B', 'C'];
    const probs = (S.post && S.post.probabilities) || [1 / 3, 1 / 3, 1 / 3];
    const l = S.post && S.samples.length ? lead(S.post) : null;
    $('outfall-bars').innerHTML = labels.map((lab, i) => {
      const p = probs[i] || 0, cls = S.done && S.done.label === lab ? 'confirmed' : l && l.label === lab && p >= 0.5 ? 'lead' : '';
      return `<div class="bar-row ${cls}"><span class="bar-name">Outfall ${esc(lab)}</span><span class="bar-track"><span class="bar-fill" style="width:${(p * 100).toFixed(1)}%"></span></span><span class="bar-pct">${pct(p)}</span></div>`;
    }).join('');
    $('outfall-note').textContent = S.done ? `Confirmed after ${S.done.samples ?? S.samples.length} water samples.`
      : S.samples.length ? `Based on ${S.samples.length} water sample${S.samples.length > 1 ? 's' : ''}. Updated after every sample.`
        : 'Equal chances until the first water sample.';

    // tiles
    const last = S.samples[S.samples.length - 1];
    if (last) {
      const a = last.nh3_n_mg_l, b = bin(a);
      $('v-nh3').textContent = mg(a);
      $('n-nh3').textContent = b >= 2 ? `${BIN_NAMES[b]}: ${times(a)} the limit` : BIN_NAMES[b] + ' (limit 0.6)';
      $('tile-nh3').dataset.level = ['', 'warn', 'alert', 'severe'][b];
      const d = last.do_mg_l;
      if (isNum(d)) {
        $('v-do').textContent = d.toFixed(1);
        $('n-do').textContent = d < TH.do_critical ? 'Critical: fish kill risk' : d < TH.do_low ? 'Low for fish' : 'Healthy for fish';
        $('tile-do').dataset.level = d < TH.do_critical ? 'severe' : d < TH.do_low ? 'warn' : '';
      }
    } else {
      for (const k of ['nh3', 'do']) { $('v-' + k).textContent = '–'; $('n-' + k).textContent = 'No reading yet'; $('tile-' + k).dataset.level = ''; }
    }
    const n = S.samples.length;
    $('v-samples').textContent = n;
    const eur = (v) => '€' + Math.round(v).toLocaleString('en-GB');
    $('n-samples').textContent = n ? `By hand: ${eur(n * MANUAL_COST[0])} to ${eur(n * MANUAL_COST[1])}` : 'By hand: €0';
    if (S.battery && isNum(S.battery.voltage)) {
      $('v-batt').textContent = isNum(S.battery.percentage) ? Math.round(S.battery.percentage * 100) + ' %' : S.battery.voltage.toFixed(1) + ' V';
      $('n-batt').textContent = `${S.battery.voltage.toFixed(2)} V${S.battery.voltage < 11.3 ? ': charge soon' : ''}`;
    } else { $('v-batt').textContent = '–'; $('n-batt').textContent = 'No reading yet'; }

    drawChart();
    renderRiver();
    renderIncident();
    renderLog();
  }
  listeners.push(renderRail);

  let chartN = -1;
  function drawChart() {
    if (S.samples.length === chartN) return;
    chartN = S.samples.length;
    const box = $('chart-nh3'), W = box.clientWidth || 340, Hh = box.clientHeight || 130, pl = 30, pr = 8, pt = 8, pb = 20;
    if (!chartN) { box.innerHTML = '<p class="note">No samples yet.</p>'; return; }
    const ys = S.samples.map((s) => s.nh3_n_mg_l), yMax = Math.max(1, Math.max(...ys) * 1.15);
    const x = (i) => pl + (chartN === 1 ? (W - pl - pr) / 2 : (i * (W - pl - pr)) / (chartN - 1));
    const y = (v) => pt + (1 - v / yMax) * (Hh - pt - pb);
    const ticks = [0, yMax / 2, yMax].map((v) => `<text class="tick" x="${pl - 4}" y="${y(v) + 4}" text-anchor="end">${v.toFixed(1)}</text><line x1="${pl}" x2="${W - pr}" y1="${y(v)}" y2="${y(v)}" stroke="#eef2f6"/>`).join('');
    const path = ys.map((v, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join('');
    const dots = S.samples.map((s, i) => `<circle cx="${x(i)}" cy="${y(s.nh3_n_mg_l)}" r="5" fill="${BIN_COLORS[bin(s.nh3_n_mg_l)]}" stroke="#fff" stroke-width="2"><title>Sample ${s.seq}: ${mg(s.nh3_n_mg_l)} mg/L at ${hms(s.at)}</title></circle>`).join('');
    const xl = S.samples.map((s, i) => (chartN <= 12 || i % Math.ceil(chartN / 10) === 0) ? `<text class="tick" x="${x(i)}" y="${Hh - 4}" text-anchor="middle">${s.seq}</text>` : '').join('');
    box.innerHTML = `<svg viewBox="0 0 ${W} ${Hh}" role="img" aria-label="Ammonia per sample">${ticks}
      <line x1="${pl}" x2="${W - pr}" y1="${y(TH.nh3_n_alert)}" y2="${y(TH.nh3_n_alert)}" stroke="#5f7a8b" stroke-width="1.5" stroke-dasharray="5 4"/>
      <path d="${path}" fill="none" stroke="#fb8500" stroke-width="2"/>${dots}${xl}</svg>`;
  }

  function renderRiver() {
    const sc = S.hello && S.hello.scenario, rv = R.river || {}, g = rv.gauge || {};
    const q = sc && isNum(sc.q_m3s) ? sc.q_m3s : g.mq_m3s;
    const v = q ? q / (22.61 * 1.0) : null;  // width x depth of the reach (data/water_area.geojson)
    const km = rv.downstream_km_to_regnitz || 6.47;
    const eta = v ? (km * 1000) / v : null;
    const etaTxt = eta ? (eta >= 3600 ? `${Math.floor(eta / 3600)} h ${Math.round((eta % 3600) / 60)} min` : `${Math.round(eta / 60)} min`) : '–';
    const rows = [
      ['River flow', q ? `${q.toFixed(1)} m³/s${sc ? '' : ' (long-term mean)'}` : '–'],
      ['Water speed', v ? `about ${(v * 3.6).toFixed(1)} km/h` : '–'],
      ['Reaches the Regnitz in', `${etaTxt} (${km} km downstream)`],
      ['Background ammonia', sc && isNum(sc.background_nh3_n_mg_l) ? `${sc.background_nh3_n_mg_l} mg/L (normal river value)` : '–'],
      ['Gauge', g.name ? `<a href="${esc(g.url)}" target="_blank" rel="noopener">${esc(g.name)}</a>` : '–'],
    ];
    const html = rows.map(([k, val]) => `<dt>${esc(k)}</dt><dd>${val}</dd>`).join('');
    if ($('river-facts').innerHTML !== html) $('river-facts').innerHTML = html;
  }

  function tierNow(t) {
    const l = S.post && S.samples.length ? lead(S.post) : null;
    const severe = S.flags.severe || S.flags.doc;
    if (t === 1) return true;
    if (t === 2) return !!(S.done || (l && l.p >= 0.5));
    if (t === 3) return !!severe;
    return false;
  }

  let incKey = '';
  function renderIncident() {
    const inc = S.incident;
    $('incident').hidden = !inc;
    if (!inc) return;
    const l = S.post && S.samples.length ? lead(S.post) : null;
    const pk = S.peak;
    const severe = S.flags.severe || S.flags.doc;
    $('incident-sum').innerHTML = `${severe ? '<strong>Severe.</strong> ' : ''}Highest ammonia <strong>${mg(pk.nh3_n_mg_l)} mg/L</strong> (${times(pk.nh3_n_mg_l)} the limit) at ${hm(pk.at)}. `
      + (S.done ? `Source confirmed: <strong>Outfall ${esc(S.done.label)}</strong>.` : l ? `Most likely source: Outfall ${esc(l.label)} (${pct(l.p)}).` : '');
    const key = JSON.stringify([inc.notified, inc.actions, !!S.done, l && l.p >= 0.5, severe]);
    if (key === incKey) return;
    incKey = key;
    const tiers = R.escalation || [{ tier: 1, name: 'Police / Fire (Leitstelle)', phone: '110 / 112', verified: true, when: 'Immediately on a confirmed alert.' }];
    $('ladder').innerHTML = tiers.map((t) => {
      const at = inc.notified[t.tier], now = !at && tierNow(t.tier);
      return `<li class="${at ? 'done' : now ? 'now' : ''}"><div class="l-head"><span class="l-name">${t.tier}. ${esc(t.name)}</span>${now ? '<span class="l-phone">notify now</span>' : ''}</div>
        <div class="l-when">${esc(t.when || '')}</div>
        <div class="l-phone">${esc(t.phone || '')}${t.verified === false ? ' (check the number before use)' : ''}</div>
        ${at ? `<div class="l-phone">Marked as notified at ${hm(at)}</div>` : `<button type="button" class="btn btn-small" data-tier="${t.tier}">Mark as notified</button>`}</li>`;
    }).join('');
    const acts = R.actions || ['Repeat the sample to confirm.', 'Report to Police 110 / Fire 112.', 'Secure evidence: position, time, photos, a cooled water sample.'];
    $('actions').innerHTML = acts.map((a, i) => `<li><label><input type="checkbox" data-act="${i}" ${inc.actions[i] ? 'checked' : ''}> <span>${esc(a)}${inc.actions[i] ? ` <span class="l-phone">(${hm(inc.actions[i])})</span>` : ''}</span></label></li>`).join('');
    $('disclaimer').textContent = ((R.public_warning && R.public_warning.disclaimer) || 'This tool cannot send a public warning.') + ' This page never contacts anyone; it records what you did and when.';
  }
  $('ladder').addEventListener('click', (e) => {
    const t = e.target.dataset.tier;
    if (!t || !S.incident) return;
    S.incident.notified[t] = Date.now();
    const tier = (R.escalation || []).find((x) => String(x.tier) === t);
    log(`Marked as notified: ${tier ? tier.name : 'tier ' + t}.`, 'action', Date.now());
    changed();
  });
  $('actions').addEventListener('change', (e) => {
    const i = e.target.dataset.act;
    if (i == null || !S.incident) return;
    if (e.target.checked) { S.incident.actions[i] = Date.now(); log(`Action done: ${(R.actions || [])[i] || 'action ' + i}`, 'action', Date.now()); }
    else delete S.incident.actions[i];
    changed();
  });

  let logKey = '';
  function renderLog() {
    const key = S.log.length + (S.log[0] ? S.log[0].text : '');
    if (key === logKey) return;
    logKey = key;
    $('log').innerHTML = S.log.length ? S.log.map((e) => `<li data-level="${e.level}"><span class="l-time">${hm(e.at)}</span><span class="l-text">${esc(e.text)}</span></li>`).join('')
      : '<li class="empty">Nothing yet.</li>';
  }

  // ------------------------------------------------------------------ requests
  let rtype = 'inspect', spot = null, nReq = 0;
  function setType(t) {
    rtype = t;
    document.querySelectorAll('.tab').forEach((b) => b.setAttribute('aria-selected', String(b.dataset.type === t)));
    document.querySelectorAll('[data-for]').forEach((el) => { if (el.dataset.for.split(' ').includes(t)) el.removeAttribute('data-hidden'); else el.setAttribute('data-hidden', ''); });
    $('req-submit').textContent = t === 'robot' ? 'Send to robot' : 'Send request';
    $('req-submit').className = 'btn btn-block ' + (t === 'robot' ? 'btn-danger' : 'btn-primary');
    $('req-note').textContent = t === 'robot' ? 'Goes straight to the robot (needs operator access when the page is shared).'
      : 'The robot plans its own route, so this request goes to the operator, who can add the stop.';
    if (t !== 'inspect') { pickCb = null; $('map').classList.remove('picking'); $('pick-spot').classList.remove('picking'); }
  }
  document.querySelectorAll('.tab').forEach((b) => b.addEventListener('click', () => setType(b.dataset.type)));
  setType('inspect');
  $('req-toggle').addEventListener('click', () => {
    const p = document.querySelector('.requests'), c = p.classList.toggle('collapsed');
    $('req-toggle').textContent = c ? '+' : '–';
    $('req-toggle').setAttribute('aria-expanded', String(!c));
  });
  $('pick-spot').addEventListener('click', () => {
    const btn = $('pick-spot');
    if (btn.classList.contains('picking')) { pickCb = null; btn.classList.remove('picking'); $('map').classList.remove('picking'); btn.textContent = 'Choose on the map'; return; }
    btn.classList.add('picking'); btn.textContent = 'Click the river now (or cancel)';
    $('map').classList.add('picking');
    pickCb = (p) => {
      spot = p; btn.classList.remove('picking'); btn.textContent = 'Choose a different spot';
      $('pick-hint').textContent = `Spot chosen: ${p.lat.toFixed(5)}, ${p.lon.toFixed(5)}`; $('pick-hint').classList.add('picked');
    };
  });

  $('req-form').addEventListener('submit', (e) => {
    e.preventDefault();
    const reason = $('req-reason').value.trim() || null;
    const prio = document.querySelector('input[name="prio"]:checked').value;
    const check = $('req-check').value;
    const checkTxt = { both: 'ammonia and oxygen', ammonia: 'ammonia', oxygen: 'oxygen' }[check];
    const q = { id: 'R-' + String(++nReq).padStart(2, '0'), at: Date.now(), reason, prio, type: rtype };
    if (rtype === 'inspect') {
      if (!spot) { nReq--; toast('Choose a spot on the map first.'); return; }
      Object.assign(q, { lat: spot.lat, lon: spot.lon, what: `Inspect a spot, check ${checkTxt}` });
    } else if (rtype === 'outfall') {
      const id = $('req-outfall').value, o = outfallInfo[id];
      Object.assign(q, { outfall: id, what: `Investigate Outfall ${id}, check ${checkTxt}` });  // the outfall pin already marks it
    } else {
      q.command = document.querySelector('input[name="robot-cmd"]:checked').value;
      q.what = q.command === 'abort' ? 'Stop the mission' : 'Return home';
    }
    REQUESTS.unshift(q);
    if (SRC.kind === 'replay') { q.status = 'practice'; q.label = 'Practice only: this is a replay, nothing was sent'; }
    else if (q.command) {
      if (sendCommand({ command: q.command })) { q.status = 'pending'; q.label = 'Sent, waiting for the robot…'; }
      else { q.status = 'failed'; q.label = 'Not sent: no connection'; }
    } else { q.status = 'operator'; q.label = 'Logged for the operator'; }
    log(`Request ${q.id}: ${q.what}${reason ? ` (${reason})` : ''}.`, 'action', q.at);
    $('req-reason').value = '';
    if (rtype === 'inspect') { spot = null; pickMk.remove(); $('pick-spot').textContent = 'Choose on the map'; $('pick-hint').textContent = 'Click a point on the river.'; $('pick-hint').classList.remove('picked'); }
    toast(`Request ${q.id} created.`);
    changed();
  });
  function onAck(m) {
    const q = REQUESTS.find((r) => r.command && r.status === 'pending' && (!m.command || m.command === r.command));
    if (!q) return;
    if (m.ok) { q.status = 'sent'; q.label = `Robot accepted: ${q.what.toLowerCase()}`; }
    else { q.status = 'failed'; q.label = /view only/i.test(m.detail || '') ? 'Not allowed: this page is view-only (needs the operator key)' : `Rejected: ${m.detail || 'unknown reason'}`; }
    log(`Request ${q.id}: ${q.label}.`, m.ok ? 'ok' : 'warn');
  }
  let qKey = '';
  function renderQueue() {
    const key = REQUESTS.map((q) => q.id + q.status + q.label).join('|');
    if (key === qKey) return;
    qKey = key;
    $('queue').innerHTML = REQUESTS.length ? REQUESTS.map((q) => `<li><div class="q-top"><span class="q-what">${esc(q.id)} ${esc(q.what)}${q.prio === 'urgent' && !q.command ? ' (urgent)' : ''}</span><span class="q-time">${hm(q.at)}</span></div>
      ${q.reason ? `<div class="q-reason">Reason: ${esc(q.reason)}</div>` : ''}<span class="q-status" data-s="${q.status}">${esc(q.label)}</span></li>`).join('')
      : '<li class="empty">No requests yet.</li>';
  }
  listeners.push(renderQueue);

  // ------------------------------------------------------------------ report + CSV
  function download(name, text, type) {
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([text], { type }));
    a.download = name; document.body.appendChild(a); a.click(); a.remove();
  }
  $('btn-csv').addEventListener('click', () => {
    if (!S.samples.length) { toast('No samples yet.'); return; }
    const rows = ['seq,time,latitude,longitude,ammonia_nh3_n_mg_l,times_legal_limit,level,oxygen_mg_l,qc_flags']
      .concat(S.samples.map((s) => [s.seq, new Date(s.at).toISOString(), s.lat, s.lon, s.nh3_n_mg_l, (s.nh3_n_mg_l / TH.nh3_n_alert).toFixed(2), BIN_NAMES[bin(s.nh3_n_mg_l)], s.do_mg_l, s.qc_flags].join(',')));
    download('plumetrace_samples.csv', rows.join('\n'), 'text/csv');
  });
  $('btn-report').addEventListener('click', () => {
    if (!S.samples.length) { toast('No samples yet.'); return; }
    const pk = S.peak, l = S.post ? lead(S.post) : null, inc = S.incident || { notified: {}, actions: {} };
    const src = S.done ? `Outfall ${S.done.label}, confirmed by the robot` : l ? `Outfall ${l.label} (${pct(l.p)} likely, not yet confirmed)` : 'unknown';
    const tiers = R.escalation || [];
    const notified = Object.entries(inc.notified).map(([t, at]) => { const x = tiers.find((y) => String(y.tier) === t); return `${x ? x.name : 'tier ' + t} at ${hm(at)}`; }).join('; ') || 'none recorded';
    const first = S.samples[0], last = S.samples[S.samples.length - 1];
    const fields = [
      ['Time', `${new Date(first.at).toLocaleString('en-GB')} to ${hm(last.at)}`],
      ['Location (lat, lon)', `${pk.lat.toFixed(6)}, ${pk.lon.toFixed(6)} (highest reading)`],
      ['Water body', 'Pegnitz, Nürnberg (Lederersteg reach, 1:100 lab model)'],
      ['Observation (colour, odour, foam, dead fish)', 'to be added by the field team'],
      ['NH₃-N mg/L', `highest ${mg(pk.nh3_n_mg_l)} (${times(pk.nh3_n_mg_l)} the 0.6 mg/L limit), ${S.samples.filter((s) => s.nh3_n_mg_l >= TH.nh3_n_alert).length} of ${S.samples.length} samples above the limit`],
      ['DO mg/L', S.minDo ? `lowest ${S.minDo.do_mg_l.toFixed(1)}` : '–'],
      ['Suspected source', src],
      ['Estimated quantity', S.post ? `unknown (estimated strength ${(+S.post.map_strength).toFixed(2)}× default)` : 'unknown'],
      ['Reporter', 'PlumeTrace TurtleBot3 (autonomous survey, demo)'],
      ['Notified tiers', notified],
    ];
    const summary = S.done
      ? `Ammonia above the legal limit was measured in the Pegnitz. The highest reading was ${mg(pk.nh3_n_mg_l)} mg/L at ${hm(pk.at)}, ${times(pk.nh3_n_mg_l)} the limit. The digital twin identified Outfall ${S.done.label} as the source, and the robot's survey confirmed it.`
      : S.firstAlert ? `Ammonia above the legal limit was measured in the Pegnitz (highest ${mg(pk.nh3_n_mg_l)} mg/L at ${hm(pk.at)}). ${l ? `Most likely source so far: Outfall ${l.label} (${pct(l.p)}).` : ''} The survey is not finished.`
        : `The robot took ${S.samples.length} samples. Ammonia stayed within the legal limit.`;
    const top = [...S.samples].sort((a, b) => b.nh3_n_mg_l - a.nh3_n_mg_l).slice(0, 8);
    const acts = Object.entries(inc.actions).map(([i, at]) => `<tr><td>${hm(at)}</td><td>${esc((R.actions || [])[i] || '')}</td></tr>`).join('');
    $('report-body').innerHTML = `<h1 id="rep-title">Pollution incident report</h1>
      <p class="r-sub">PlumeTrace river monitoring, Pegnitz in Nürnberg. Created ${esc(new Date().toLocaleString('en-GB'))}.</p>
      <p class="r-summary">${esc(summary)}</p>
      <h2>Report form (Meldebogen fields)</h2>
      <table><tbody>${fields.map(([k, v]) => `<tr><th>${esc(k)}</th><td>${esc(v)}</td></tr>`).join('')}</tbody></table>
      <h2>Highest readings</h2>
      <table><thead><tr><th>Sample</th><th>Time</th><th class="num">NH₃-N (mg/L)</th><th class="num">× limit</th><th class="num">DO (mg/L)</th></tr></thead>
      <tbody>${top.map((s) => `<tr><td>${s.seq}</td><td>${hms(s.at)}</td><td class="num">${mg(s.nh3_n_mg_l)}</td><td class="num">${times(s.nh3_n_mg_l)}</td><td class="num">${isNum(s.do_mg_l) ? s.do_mg_l.toFixed(1) : '–'}</td></tr>`).join('')}</tbody></table>
      ${acts ? `<h2>Actions taken</h2><table><tbody>${acts}</tbody></table>` : ''}
      ${REQUESTS.length ? `<h2>Requests</h2><table><tbody>${REQUESTS.map((q) => `<tr><td>${hm(q.at)}</td><td>${esc(q.id)} ${esc(q.what)}${q.reason ? ` (${esc(q.reason)})` : ''}</td><td>${esc(q.label)}</td></tr>`).join('')}</tbody></table>` : ''}
      <h2>Timeline</h2><table><tbody>${[...S.log].reverse().map((e) => `<tr><td style="width:80px">${hms(e.at)}</td><td>${esc(e.text)}</td></tr>`).join('')}</tbody></table>
      <p class="r-note">Legal limit 0.6 mg/L NH₃-N (OGewV). Prototype: readings are emulated from the robot's position in a 1:100 lab model of this reach; the outfall positions are illustrative. This page contacted nobody: notifications are what the user recorded.</p>`;
    $('report').hidden = false;
    $('r-close').focus();
  });
  $('r-close').addEventListener('click', () => { $('report').hidden = true; });
  $('r-print').addEventListener('click', () => window.print());
  $('report').addEventListener('click', (e) => { if (e.target.id === 'report') $('report').hidden = true; });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') $('report').hidden = true; });

  // ------------------------------------------------------------------ data sources
  const SRC = { kind: 'replay', link: 'replay', ws: null, lastMsg: 0 };
  const RP = { msgs: [], dur: 0, pos: 0, i: 0, playing: false, speed: 2, last: null, base: Date.now(), name: '' };

  function resetAll() {
    S = fresh();
    drawn = { samples: 0, trail: -1, plume: null, heading: null, highlight: '' };
    chartN = -1; incKey = ''; logKey = '';
    sampleLayer.clearLayers(); plumeLayer.clearLayers(); trail.setLatLngs([]);
    if (srcRing) { srcRing.remove(); srcRing = null; }
    changed();
  }

  function loadReplayText(text, name) {
    const msgs = [];
    for (const line of text.split('\n')) {
      if (!line.trim()) continue;
      try { const m = JSON.parse(line); if (m && m.type) msgs.push(m); } catch (e) { /* skip */ }
    }
    if (!msgs.length) throw new Error('No messages in this file.');
    // recordings from the relay or gateway may have only t; fall back to it
    const t0 = isNum(msgs[0].replay_t) ? 0 : msgs.find((m) => isNum(m.t))?.t || 0;
    msgs.forEach((m) => { m._t = isNum(m.replay_t) ? m.replay_t : isNum(m.t) ? m.t - t0 : 0; });
    msgs.sort((a, b) => a._t - b._t);
    RP.msgs = msgs; RP.dur = msgs[msgs.length - 1]._t; RP.name = name;
    seek(0);
  }
  async function loadReplayUrl(url, name) {
    const r = await fetch(url, { cache: 'no-store' });
    if (!r.ok) throw new Error(`${url} not found`);
    loadReplayText(await r.text(), name);
  }
  function seek(sec) {
    resetAll();
    RP.base = Date.now() - sec * 1000;
    RP.pos = Math.max(0, Math.min(sec, RP.dur)); RP.i = 0;
    while (RP.i < RP.msgs.length && RP.msgs[RP.i]._t <= RP.pos) { const m = RP.msgs[RP.i++]; receive(m, RP.base + m._t * 1000); }
    renderSource();
  }
  function tick(now) {
    if (SRC.kind === 'replay' && RP.playing) {
      if (RP.last != null) {
        RP.pos += ((now - RP.last) / 1000) * RP.speed;
        while (RP.i < RP.msgs.length && RP.msgs[RP.i]._t <= RP.pos) { const m = RP.msgs[RP.i++]; receive(m, RP.base + m._t * 1000); }
        if (RP.pos >= RP.dur) { RP.pos = RP.dur; RP.playing = false; }
        renderSource();
      }
      RP.last = now;
    }
    requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
  // replay clock: messages are stamped as if the mission ran at 1x from RP.base
  function setPlaying(on) {
    if (on && RP.pos >= RP.dur) seek(0);
    if (on) RP.base = Date.now() - RP.pos * 1000;
    RP.playing = on; RP.last = null; renderSource();
  }

  let retry = null;
  function wsUrl() {
    return CFG.wsUrl === 'auto' ? (location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws' + location.search
      : (CFG.wsUrl || 'ws://localhost:8765');
  }
  function connect() {
    clearTimeout(retry);
    SRC.link = 'connecting'; renderSource();
    let ws;
    try { ws = new WebSocket(wsUrl()); } catch (e) { SRC.link = 'down'; renderSource(); retry = setTimeout(connect, 2000); return; }
    SRC.ws = ws;
    ws.onopen = () => { SRC.link = 'ok'; renderSource(); };
    ws.onmessage = (ev) => {
      let m; try { m = JSON.parse(ev.data); } catch (e) { return; }
      SRC.lastMsg = Date.now();
      receive(m, Date.now());
    };
    ws.onclose = () => {
      if (SRC.ws !== ws) return;
      SRC.ws = null; SRC.link = 'down'; renderSource();
      if (SRC.kind === 'live') retry = setTimeout(connect, 2000);
    };
  }
  function sendCommand(cmd) {
    if (SRC.kind !== 'live' || !SRC.ws || SRC.ws.readyState !== 1) return false;
    SRC.ws.send(JSON.stringify(Object.assign({ type: 'command' }, cmd)));
    return true;
  }
  function useSource(kind) {
    if (kind === SRC.kind) return;
    SRC.kind = kind;
    reqLayer.clearLayers(); REQUESTS.forEach((q) => { q.marker = null; });
    if (kind === 'live') { RP.playing = false; resetAll(); connect(); }
    else { clearTimeout(retry); if (SRC.ws) { const w = SRC.ws; SRC.ws = null; w.close(); } SRC.link = 'replay'; seek(0); }
    renderSource();
  }

  function renderSource() {
    document.querySelectorAll('.source-btn').forEach((b) => b.setAttribute('aria-checked', String(b.dataset.source === SRC.kind)));
    let text, st;
    if (SRC.kind === 'replay') { text = RP.name || 'Replay'; st = 'replay'; }
    else if (SRC.link === 'ok') {
      const age = SRC.lastMsg ? (Date.now() - SRC.lastMsg) / 1000 : null;
      if (age == null || age > 5) { text = 'Connected, waiting for data'; st = 'warn'; }
      else { text = 'Live: digital twin connected'; st = 'ok'; }
    } else if (SRC.link === 'connecting') { text = 'Connecting…'; st = 'warn'; }
    else { text = 'No connection to the gateway'; st = 'down'; }
    $('link-text').textContent = text; $('link').dataset.state = st;
    $('replay').hidden = SRC.kind !== 'replay';
    if (SRC.kind === 'replay') {
      $('rp-play').textContent = RP.playing ? '❚❚' : '▶';
      $('rp-play').title = RP.playing ? 'Pause' : 'Play';
      const f = (v) => `${Math.floor(v / 60)}:${String(Math.floor(v % 60)).padStart(2, '0')}`;
      $('rp-time').textContent = `${f(RP.pos)} / ${f(RP.dur)}`;
      if (document.activeElement !== $('rp-seek')) $('rp-seek').value = RP.dur ? Math.round((RP.pos / RP.dur) * 1000) : 0;
    }
  }
  setInterval(renderSource, 1000);

  // ------------------------------------------------------------------ controls
  function toast(t) {
    const el = $('toast'); el.textContent = t; el.hidden = false;
    clearTimeout(toast.h); toast.h = setTimeout(() => { el.hidden = true; }, 4000);
  }
  document.querySelectorAll('.source-btn').forEach((b) => b.addEventListener('click', () => useSource(b.dataset.source)));
  document.querySelectorAll('[data-view]').forEach((b) => b.addEventListener('click', () => {
    const v = b.dataset.view;
    if (v === 'follow') {
      follow = b.getAttribute('aria-pressed') !== 'true'; b.setAttribute('aria-pressed', String(follow));
      if (follow && S.pose) map.setView([S.pose.lat, S.pose.lon], Math.max(map.getZoom(), 19));
      return;
    }
    follow = false; document.querySelector('[data-view="follow"]').setAttribute('aria-pressed', 'false');
    if (v === 'overview') fit();
    if (v === 'source') {
      const id = S.done ? S.done.label : S.post && S.samples.length ? lead(S.post).label : null;
      if (!id || !outfallInfo[id]) { toast('No likely source yet.'); return; }
      map.setView([outfallInfo[id].lat, outfallInfo[id].lon], 19.5);
      outfallMk[id].openPopup();
    }
  }));
  $('btn-plume').addEventListener('click', (e) => { showPlume = !showPlume; e.target.setAttribute('aria-pressed', String(showPlume)); changed(); });
  $('legend-bins').innerHTML = BIN_NAMES.map((n, i) => `<li><span class="sw" style="--c:${BIN_COLORS[i]}"></span>${n}${i === 0 ? ` (below ${TH.nh3_n_elevated})` : i === 1 ? ` (${TH.nh3_n_elevated} to ${TH.nh3_n_alert})` : i === 2 ? ` (${TH.nh3_n_alert} to ${TH.nh3_n_severe})` : ` (${TH.nh3_n_severe} or more)`}</li>`).join('');

  $('rp-play').addEventListener('click', () => setPlaying(!RP.playing));
  $('rp-seek').addEventListener('input', (e) => { seek((e.target.value / 1000) * RP.dur); });
  $('rp-speed').addEventListener('change', (e) => { RP.speed = +e.target.value; });
  RP.speed = +$('rp-speed').value;
  $('rp-file').addEventListener('change', async (e) => {
    const f = e.target.files[0]; if (!f) return;
    try { loadReplayText(await f.text(), f.name); toast(`Loaded ${f.name}. Press play.`); } catch (err) { toast(err.message); }
    e.target.value = '';
  });
  const pickSel = $('rp-file-pick');
  (async () => {
    const ok = [];
    // GET, not HEAD: tools/relay.py (websockets) only accepts GET requests
    for (const r of REPLAYS) { try { const h = await fetch(r.file, { cache: 'no-store' }); if (h.ok) ok.push(r); } catch (e) { /* skip */ } }
    pickSel.innerHTML = ok.map((r) => `<option value="${esc(r.file)}">${esc(r.name)}</option>`).join('');
    pickSel.hidden = ok.length < 2;
    const params = new URLSearchParams(location.search);
    if (ok.length) { try { await loadReplayUrl(ok[0].file, ok[0].name); } catch (e) { toast(e.message); } }
    // through tools/relay.py (wsUrl 'auto') the page opens live, like the operator view; ?replay keeps Replay
    if (params.has('live') || params.has('key') || (CFG.wsUrl === 'auto' && !params.has('replay'))) useSource('live');
  })();
  pickSel.addEventListener('change', async () => {
    const r = REPLAYS.find((x) => x.file === pickSel.value);
    if (r) { RP.playing = false; await loadReplayUrl(r.file, r.name); }
  });
  window.addEventListener('resize', () => { chartN = -1; changed(); });
})();
