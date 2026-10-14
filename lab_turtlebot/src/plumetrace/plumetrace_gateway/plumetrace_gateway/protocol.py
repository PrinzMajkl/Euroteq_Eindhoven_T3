"""PlumeTrace gateway protocol: JSON messages to the city view and allow-listed commands from it.

Server -> client types: hello, pose, sample, posterior, plume_points, plume_true, event, obstacles,
sync, alert, mission, ack.
Client -> server: {"type": "command", "command": <name>, ...} with name in COMMANDS; anything else is
rejected with an ack {ok: false}. Positions are WGS84 (lat, lon); obstacle heights are scaled x100
(arena -> river) for Cesium. Schema: web/schema.json.
"""
import json
import math

import numpy as np

COMMANDS = ('abort', 'return_home', 'add_nogo', 'remove_nogo', 'add_obstacle', 'remove_obstacle')
ALERT_MG_L = 0.6
SYNC_NAMES = ('SYNCED', 'STALE', 'LOST')
ORIGINS = ('REAL', 'VIRTUAL')
MODES = ('REROUTE', 'STOP')


def r6(v):
    return float(round(float(v), 7))


def latlon(frame, arena_xy):
    lat, lon, _ = frame.arena_to_geodetic(np.asarray(arena_xy, dtype=float))
    return r6(lat), r6(lon)


def pose_msg(frame, t, x, y, yaw):
    lat, lon = latlon(frame, [x, y])
    rx, ry = frame.arena_to_river([x, y])
    heading = (90.0 - math.degrees(frame.arena_yaw_to_river(yaw))) % 360.0  # compass, from north
    return dict(type='pose', t=round(t, 3), lat=lat, lon=lon, heading_deg=round(heading, 2),
                arena=dict(x=round(x, 4), y=round(y, 4), yaw=round(yaw, 4)),
                river=dict(x=round(float(rx), 3), y=round(float(ry), 3)))


def sample_msg(frame, s):
    """s: plumetrace_msgs/PlumeSample."""
    lat, lon, _ = frame.river_to_geodetic(np.array([s.river_xy.x, s.river_xy.y]))
    return dict(type='sample', seq=int(s.seq), t=round(s.header.stamp.sec + s.header.stamp.nanosec * 1e-9, 3),
                lat=r6(lat), lon=r6(lon), nh3_n_mg_l=round(float(s.nh3_n_mg_l), 4),
                do_mg_l=round(float(s.do_mg_l), 4), qc_flags=int(s.qc_flags), is_replay=bool(s.is_replay),
                river=dict(x=round(s.river_xy.x, 3), y=round(s.river_xy.y, 3)),
                arena=dict(x=round(s.arena_pose.x, 4), y=round(s.arena_pose.y, 4)))


def posterior_msg(p):
    return dict(type='posterior', labels=list(p.labels), probabilities=[round(float(v), 5) for v in p.probabilities],
                map_label=p.map_label, map_strength=round(float(p.map_strength), 4))


def alert_msg(sample, post):
    likely, prob = None, None
    if post is not None and len(post['probabilities']):
        k = int(np.argmax(post['probabilities']))
        likely, prob = post['labels'][k], post['probabilities'][k]
    txt = f"NH₃-N above {ALERT_MG_L} mg/L · {sample['lat']:.6f}, {sample['lon']:.6f}"
    if likely is not None:
        txt += f' · likely outfall {likely} ({prob * 100:.0f} %)'
    return dict(type='alert', t=sample['t'], seq=sample['seq'], nh3_n_mg_l=sample['nh3_n_mg_l'],
                lat=sample['lat'], lon=sample['lon'], likely_outfall=likely,
                probability=None if prob is None else round(float(prob), 4), message=txt)


def obstacles_msg(frame, arr, t):
    obs = []
    for o in arr.obstacles:
        fp = [list(latlon(frame, [p.x, p.y])) for p in o.footprint.points]
        obs.append(dict(id=o.id, origin=ORIGINS[o.origin] if o.origin < 2 else 'REAL',
                        mode=MODES[o.mode] if o.mode < 2 else 'REROUTE',
                        height_m=round(float(o.height_m) * frame.scale, 2), confidence=round(float(o.confidence), 3),
                        footprint=fp))
    return dict(type='obstacles', t=round(t, 3), obstacles=obs)


def sync_msg(s):
    return dict(type='sync', streams=[dict(name=n, state=SYNC_NAMES[min(int(st), 2)],
                                           staleness_s=(round(float(a), 3) if math.isfinite(a) else None))
                                      for n, st, a in zip(s.streams, s.states, s.staleness_s)])


def mission_msg(ms, time_factor, reach_name):
    return dict(type='mission', mode=ms.mode, state=ms.state, samples_taken=int(ms.samples_taken),
                scenario=ms.scenario, time_factor=float(time_factor), reach=reach_name)


def plume_points_msg(kind, t, grid_ll, values):
    """kind: 'plume_points' (estimator field) or 'plume_true' (synthetic truth), same grid and order."""
    pts = [[r6(a), r6(b), round(float(c), 4)] for (a, b), c in zip(grid_ll, values)]
    return dict(type=kind, t=round(t, 3), units='mg/L NH3-N', points=pts)


def event_msg(raw, t):
    """/mission/events JSON string -> event message; None when malformed."""
    try:
        d = json.loads(raw)
    except (TypeError, ValueError):
        return None
    if not isinstance(d, dict) or not isinstance(d.get('type'), str):
        return None
    return dict(type='event', t=round(t, 3), kind=d['type'], data={k: v for k, v in d.items() if k not in ('type', 't')})


def hello_scenario(sc):
    bg = sc.get('background') or {}
    # no scenario id: scenario files are named after their leaking outfall
    return dict(q_m3s=float(sc['flow']['q_m3s']),
                background_nh3_n_mg_l=bg.get('nh3_n_mg_l'), background_do_mg_l=bg.get('do_mg_l'),
                time_factor=float(sc['time_factor']))


def validate_command(msg):
    """Return (ok, reason). Only the allow-listed commands with well-formed arguments pass."""
    if not isinstance(msg, dict) or msg.get('type') != 'command':
        return False, 'not a command'
    c = msg.get('command')
    if c not in COMMANDS:
        return False, f'command {c!r} not allowed'
    if c in ('add_nogo', 'add_obstacle'):
        poly = msg.get('polygon')
        if poly is None and c == 'add_obstacle' and 'center' in msg:
            ctr = msg['center']
            if not (isinstance(ctr, (list, tuple)) and len(ctr) == 2):
                return False, 'center must be [lat, lon]'
        elif not (isinstance(poly, list) and len(poly) >= 3 and all(isinstance(p, (list, tuple)) and len(p) == 2
                                                                      for p in poly)):
            return False, 'polygon must be >= 3 [lat, lon] pairs'
        if c == 'add_obstacle' and msg.get('mode', 'REROUTE') not in MODES:
            return False, 'mode must be REROUTE or STOP'
    if c in ('remove_nogo', 'remove_obstacle') and not isinstance(msg.get('id'), str):
        return False, 'id required'
    return True, ''


def command_to_registry(frame, msg, new_id):
    """Translate an add/remove command to a registry op (arena frame)."""
    c = msg['command']
    if c.startswith('remove'):
        return dict(op='remove', id=msg['id'])
    if 'polygon' in msg and msg['polygon'] is not None:
        lat = np.array([p[0] for p in msg['polygon']], dtype=float)
        lon = np.array([p[1] for p in msg['polygon']], dtype=float)
        arena = frame.river_to_arena(frame.geodetic_to_river(lat, lon))
    else:
        cx, cy = frame.river_to_arena(frame.geodetic_to_river(*msg['center']))
        h = float(msg.get('size_m', 25.0)) / frame.scale / 2  # river metres -> arena half side
        arena = np.array([[cx - h, cy - h], [cx + h, cy - h], [cx + h, cy + h], [cx - h, cy + h]])
    kind = 'nogo' if c == 'add_nogo' else 'obstacle'
    oid = msg.get('id') or f'{kind}-{new_id}'
    return dict(op='add', id=oid, kind=kind, mode='REROUTE' if kind == 'nogo' else msg.get('mode', 'REROUTE'),
                height_m=0.0 if kind == 'nogo' else float(msg.get('height_m', 30.0)) / frame.scale,
                footprint=[[round(float(x), 4), round(float(y), 4)] for x, y in arena])
