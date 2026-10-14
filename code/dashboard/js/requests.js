// "Request an inspection" panel: build a request, send it, show its progress.
import { CONFIG } from './config.js';
import { state, addRequest, setRequest, fmt } from './store.js';
import { source, sendRequest } from './data.js';
import { pickSpot, cancelPick, hidePickMarker } from './map.js';

const $ = (id) => document.getElementById(id);
let type = 'inspect';
let spot = null;
let counter = 0;

const CHECK_TEXT = { ammonia: 'ammonia', oxygen: 'oxygen', both: 'ammonia and oxygen' };

export function initRequests(toast) {
  const sel = $('req-outfall');
  for (const o of CONFIG.OUTFALLS) {
    const opt = document.createElement('option');
    opt.value = o.id;
    opt.textContent = `${o.name}: ${o.note}`;
    sel.appendChild(opt);
  }

  for (const tab of document.querySelectorAll('.tab')) {
    tab.addEventListener('click', () => setType(tab.dataset.type));
  }
  setType('inspect');

  $('req-toggle').addEventListener('click', () => {
    const panel = document.querySelector('.requests');
    const collapsed = panel.classList.toggle('collapsed');
    $('req-toggle').setAttribute('aria-expanded', String(!collapsed));
    $('req-toggle').textContent = collapsed ? '+' : '–';
    $('req-toggle').title = collapsed ? 'Show panel' : 'Hide panel';
  });

  $('pick-spot').addEventListener('click', () => {
    const btn = $('pick-spot');
    if (btn.classList.contains('picking')) {
      cancelPick();
      btn.classList.remove('picking');
      btn.textContent = spot ? 'Choose a different spot' : 'Choose on the map';
      return;
    }
    btn.classList.add('picking');
    btn.textContent = 'Click the river now (or cancel)';
    $('pick-hint').textContent = 'Click inside the dashed outline on the map.';
    $('pick-hint').classList.remove('picked');
    pickSpot((p) => {
      spot = p;
      btn.classList.remove('picking');
      btn.textContent = 'Choose a different spot';
      $('pick-hint').textContent = `Spot chosen (arena ${p.x.toFixed(2)} m, ${p.y.toFixed(2)} m).`;
      $('pick-hint').classList.add('picked');
    });
  });

  $('req-form').addEventListener('submit', (ev) => {
    ev.preventDefault();
    submit(toast);
  });
}

function setType(t) {
  type = t;
  for (const tab of document.querySelectorAll('.tab')) {
    tab.setAttribute('aria-selected', String(tab.dataset.type === t));
  }
  for (const el of document.querySelectorAll('[data-for]')) {
    const show = el.dataset.for.split(' ').includes(t);
    if (show) el.removeAttribute('data-type-hidden'); else el.setAttribute('data-type-hidden', '');
  }
  const btn = $('req-submit');
  btn.textContent = t === 'stop' ? 'Stop the robot now' : 'Send request';
  btn.classList.toggle('stop', t === 'stop');
  if (t !== 'inspect') { cancelPick(); $('pick-spot').classList.remove('picking'); }
}

function submit(toast) {
  const reason = $('req-reason').value.trim();
  const priority = document.querySelector('input[name="prio"]:checked').value;
  const check = $('req-check').value;
  const req = {
    id: `R-${String(++counter).padStart(3, '0')}`,
    type,
    created: new Date().toISOString(),
    requested_by: 'River authority dashboard',
    reason: reason || null,
  };

  if (type === 'inspect') {
    if (!spot) { counter--; toast('Choose a spot on the map first.'); return; }
    Object.assign(req, { x: round(spot.x), y: round(spot.y), frame_id: 'odom', check, priority });
    req.what = `Inspect a spot, check ${CHECK_TEXT[check]}`;
  } else if (type === 'outfall') {
    const o = CONFIG.OUTFALLS.find((q) => q.id === $('req-outfall').value);
    Object.assign(req, { outfall: o.id, x: o.x, y: o.y, frame_id: 'odom', check, priority });
    req.what = `Investigate ${o.name}, check ${CHECK_TEXT[check]}`;
  } else {
    req.priority = 'urgent';
    req.what = 'Stop the robot';
  }

  const local = { ...req, time: Date.now() / 1000, status: 'pending', label: 'Sending…' };
  addRequest(local);

  if (source.kind === 'replay') {
    setRequest(local, 'practice', 'Practice only: replay is running, nothing was sent');
  } else if (!sendRequest(req)) {
    setRequest(local, 'failed', 'Not delivered: no connection to the gateway');
  }

  // Reset the form for the next request
  $('req-reason').value = '';
  if (type === 'inspect') {
    spot = null;
    hidePickMarker();
    $('pick-spot').textContent = 'Choose on the map';
    $('pick-hint').textContent = 'Click a point inside the dashed outline on the river.';
    $('pick-hint').classList.remove('picked');
  }
  toast(type === 'stop' ? 'Stop request sent.' : `Request ${req.id} created.`);
}

const round = (v) => Math.round(v * 1000) / 1000;

let lastKey = '';
export function renderRequests() {
  const key = state.requests.map((q) => q.id + q.status + q.label).join('|');
  if (key === lastKey) return;
  lastKey = key;
  const list = $('queue');
  list.innerHTML = '';
  if (!state.requests.length) {
    list.innerHTML = '<li class="empty">No requests yet.</li>';
    return;
  }
  for (const q of state.requests) {
    const li = document.createElement('li');
    li.innerHTML = `<div class="q-top"><span class="q-what"></span><span class="q-time"></span></div>
      <div class="q-reason"></div><span class="q-status"></span>`;
    li.querySelector('.q-what').textContent = `${q.id} ${q.what}${q.priority === 'urgent' && q.type !== 'stop' ? ' (urgent)' : ''}`;
    li.querySelector('.q-time').textContent = fmt.hm(q.time);
    li.querySelector('.q-reason').textContent = q.reason ? `Reason: ${q.reason}` : '';
    const st = li.querySelector('.q-status');
    st.dataset.s = q.status;
    st.textContent = q.label;
    list.appendChild(li);
  }
}
