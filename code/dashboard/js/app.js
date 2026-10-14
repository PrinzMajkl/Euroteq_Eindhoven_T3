// PlumeTrace authority dashboard: wiring.
import { CONFIG } from './config.js';
import { state, onChange } from './store.js';
import { source, replay, onSource, useSource, setPlaying, seek, loadReplayUrl, loadReplayText } from './data.js';
import { initMap, updateMap, view, setToast, clearRequestMarkers, useMode } from './map.js';
import { render, renderSource } from './panels.js';
import { initRequests, renderRequests } from './requests.js';
import { initReport } from './report.js';

const $ = (id) => document.getElementById(id);

let toastTimer;
function toast(text) {
  const el = $('toast');
  el.textContent = text;
  el.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { el.hidden = true; }, 4000);
}

async function main() {
  setToast(toast);
  try {
    await initMap($('map'));
  } catch (e) {
    console.error(e);
    toast('The map could not start. Check the internet connection.');
  }

  onChange((s) => {
    updateMap(s);
    render(s);
    renderRequests();
    renderSource(source, replay, s);
  });
  onSource((src, rp) => renderSource(src, rp, state));

  // Data source switch
  for (const b of document.querySelectorAll('.source-btn')) {
    b.addEventListener('click', () => {
      clearRequestMarkers();
      useSource(b.dataset.source);
    });
  }

  // Map views
  for (const b of document.querySelectorAll('[data-view]')) {
    b.addEventListener('click', () => {
      const kind = b.dataset.view;
      if (kind === 'hotspot' && !state.peak) { toast('No readings yet.'); return; }
      const following = kind === 'follow' && b.getAttribute('aria-pressed') !== 'true';
      document.querySelector('[data-view="follow"]').setAttribute('aria-pressed', String(following));
      view(following ? 'follow' : kind === 'follow' ? 'none' : kind, false, state);
    });
  }

  // 2D map <-> Cesium 3D view
  $('btn-3d').addEventListener('click', async () => {
    const btn = $('btn-3d');
    const want = btn.getAttribute('aria-pressed') === 'true' ? '2d' : '3d';
    btn.disabled = true;
    if (want === '3d') {
      toast(CONFIG.CESIUM_ION_TOKEN ? 'Loading the 3D view…'
        : 'Loading the 3D view. Add your Cesium ion token in config.js for terrain and 3D buildings.');
    }
    const got = await useMode(want);
    btn.setAttribute('aria-pressed', String(got === '3d'));
    btn.textContent = got === '3d' ? '2D map' : '3D view';
    document.querySelector('[data-view="follow"]').setAttribute('aria-pressed', 'false');
    view('overview', false, state);
    btn.disabled = false;
  });

  // Replay controls
  $('rp-play').addEventListener('click', () => setPlaying(!replay.playing));
  $('rp-seek').addEventListener('input', (e) => seek((e.target.value / 1000) * replay.duration));
  $('rp-speed').addEventListener('change', (e) => { replay.speed = Number(e.target.value); });
  replay.speed = Number($('rp-speed').value);
  $('rp-file').addEventListener('change', async (e) => {
    const f = e.target.files[0];
    if (!f) return;
    try {
      loadReplayText(await f.text(), f.name);
      toast(`Loaded ${f.name}. Press play.`);
    } catch (err) {
      toast(err.message);
    }
    e.target.value = '';
  });

  initRequests(toast);
  initReport(toast);

  // Live link health is time-based, so refresh it every second.
  setInterval(() => renderSource(source, replay, state), 1000);

  // Start: ?live opens the live robot view, otherwise the demo replay.
  const params = new URLSearchParams(location.search);
  try {
    await loadReplayUrl(CONFIG.REPLAY_FILE);
  } catch (e) {
    toast(e.message);
  }
  if (params.has('live')) useSource('live');
  renderSource(source, replay, state);
}

main();
