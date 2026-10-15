// Data sources: live WebSocket from gateway_node.py, or replay of a JSONL run.
import { CONFIG } from './config.js';
import { process, reset, ackRequest, changed } from './store.js';

export const source = {
  kind: 'replay',          // 'live' | 'replay'
  link: 'replay',          // live: 'connecting' | 'ok' | 'down'
  ros: false,
  direct: false,
  ws: null,
};

const subs = new Set();
export function onSource(fn) { subs.add(fn); }
const notify = () => subs.forEach((fn) => fn(source, replay));

// ---------------- Live ----------------
let retry = null;

function connect() {
  clearTimeout(retry);
  source.link = 'connecting';
  notify();
  let ws;
  try {
    ws = new WebSocket(CONFIG.WS_URL);
  } catch (e) {
    source.link = 'down';
    notify();
    retry = setTimeout(connect, 2000);
    return;
  }
  source.ws = ws;
  ws.onopen = () => { source.link = 'ok'; notify(); };
  ws.onmessage = (ev) => {
    let msg;
    try { msg = JSON.parse(ev.data); } catch { return; }
    if (msg.topic === '/gateway/hello') {
      source.ros = !!msg.data.ros;
      source.direct = !!msg.data.direct;
      notify();
      return;
    }
    if (msg.topic === '/gateway/ack') { ackRequest(msg.data); return; }
    process(msg);
  };
  ws.onclose = () => {
    if (source.ws !== ws) return;
    source.link = 'down';
    source.ws = null;
    notify();
    if (source.kind === 'live') retry = setTimeout(connect, 2000);
  };
}

export function sendRequest(request) {
  if (source.kind !== 'live' || !source.ws || source.ws.readyState !== 1) return false;
  source.ws.send(JSON.stringify({ kind: 'request', request }));
  return true;
}

// ---------------- Replay ----------------
export const replay = {
  messages: [],
  name: '',
  duration: 0,
  pos: 0,         // seconds into the run
  index: 0,       // next message to play
  playing: false,
  speed: 2,
  last: null,
};

export async function loadReplayUrl(url) {
  const res = await fetch(url, { cache: 'no-store' });
  if (!res.ok) throw new Error(`Could not load ${url} (${res.status})`);
  loadReplayText(await res.text(), url.split('/').pop());
}

export function loadReplayText(text, name) {
  const msgs = [];
  for (const line of text.split('\n')) {
    const l = line.trim();
    if (!l) continue;
    try {
      const m = JSON.parse(l);
      if (m && m.topic) msgs.push(m);
    } catch { /* skip bad lines */ }
  }
  if (!msgs.length) throw new Error('No messages found in this file.');
  const t0 = msgs[0].t || 0;
  msgs.forEach((m) => { m.t = (m.t || 0) - t0; });
  msgs.sort((a, b) => a.t - b.t);
  replay.messages = msgs;
  replay.name = name;
  replay.duration = msgs[msgs.length - 1].t;
  seek(0);
}

export function seek(sec) {
  reset();
  replay.pos = Math.max(0, Math.min(sec, replay.duration));
  replay.index = 0;
  while (replay.index < replay.messages.length && replay.messages[replay.index].t <= replay.pos) {
    playMsg(replay.messages[replay.index++]);
  }
  notify();
  changed();
}

function playMsg(m) {
  if (m.topic === '/dashboard_request' || m.topic.startsWith('/gateway/')) return;
  process(m);
}

export function setPlaying(on) {
  if (on && replay.pos >= replay.duration) seek(0);
  replay.playing = on;
  replay.last = null;
  notify();
}

function tick(now) {
  if (source.kind === 'replay' && replay.playing) {
    if (replay.last != null) {
      replay.pos += ((now - replay.last) / 1000) * replay.speed;
      while (replay.index < replay.messages.length && replay.messages[replay.index].t <= replay.pos) {
        playMsg(replay.messages[replay.index++]);
      }
      if (replay.pos >= replay.duration) {
        replay.pos = replay.duration;
        replay.playing = false;
      }
      notify();
    }
    replay.last = now;
  }
  requestAnimationFrame(tick);
}
requestAnimationFrame(tick);

// ---------------- Switching ----------------
export function useSource(kind) {
  if (kind === source.kind) return;
  source.kind = kind;
  if (kind === 'live') {
    replay.playing = false;
    reset();
    connect();
  } else {
    clearTimeout(retry);
    if (source.ws) { const ws = source.ws; source.ws = null; ws.close(); }
    source.link = 'replay';
    seek(0);
  }
  notify();
}
