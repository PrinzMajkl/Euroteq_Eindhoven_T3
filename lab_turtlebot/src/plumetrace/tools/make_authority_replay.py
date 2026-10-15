#!/usr/bin/env python3
"""Record one offline mission as gateway messages, for the authority view's Replay mode (no ROS needed).

    python3 tools/make_authority_replay.py [--scenario B] [--seed 1] [--strategy sweep] [--out web/data/replay_B.jsonl]

Uses the same plume, sensor model, estimator and sweep/adaptive planner as offline_sim.run_mission, and writes
one JSON message per line in the gateway's format (protocol.py / web/schema.json) with an extra field
`replay_t` (seconds from the start of the recording). Message types: hello, mission, battery, sync, pose,
event (state, goal_sent, goal_result, dwell, sample, done, return_home_start, return_home), sample, alert,
posterior, plume_points. Readings are emulated, as in the lab.
"""
import argparse
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'plumetrace_twin'))

from plumetrace_twin.estimator import CAP, sweep_order  # noqa: E402
from plumetrace_twin.offline_sim import PLAN_OVERHEAD_S, KinematicRobot  # noqa: E402
from plumetrace_twin.reach import ReachFrame  # noqa: E402
from plumetrace_twin.scenario import load_scenario, make_estimator, make_plume  # noqa: E402
from plumetrace_twin.sensor_model import SENSOR_DEFAULTS, SensorModel, probe_point  # noqa: E402

ALERT = 0.6
POSE_EVERY = 5  # simulation steps of 0.1 s -> 2 Hz pose


def r7(v):
    return float(round(float(v), 7))


class Recorder:
    def __init__(self):
        self.out = []
        self.t = 0.0

    def emit(self, msg, t=None):
        t = self.t if t is None else t
        msg = dict(msg)
        msg['replay_t'] = round(t, 2)
        self.out.append(msg)


class RecordingRobot(KinematicRobot):
    """KinematicRobot that reports its pose, battery and mission heartbeat while it moves."""

    def __init__(self, rec, hooks, *a, **kw):
        super().__init__(*a, **kw)
        self.rec, self.hooks, self.n = rec, hooks, 0

    def _step(self):
        super()._step()
        self.n += 1
        self.rec.t = self.t
        if self.n % POSE_EVERY == 0:
            self.hooks['pose'](self)
        if self.n % 10 == 0:
            self.hooks['second'](self)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--scenario', default='B')
    ap.add_argument('--seed', type=int, default=1)
    ap.add_argument('--strategy', default='sweep', choices=['sweep', 'adaptive'])
    ap.add_argument('--out', default=None)
    args = ap.parse_args()
    out = args.out or os.path.join(HERE, '..', 'web', 'data', f'replay_{args.scenario}.jsonl')

    frame = ReachFrame.load()
    sc = load_scenario(args.scenario, seed=args.seed)
    rng = np.random.default_rng(args.seed)
    sen = dict(SENSOR_DEFAULTS)
    plume = make_plume(frame, sc)
    sensor = SensorModel(np.random.default_rng(args.seed * 1000 + 7), tau=sen['lag_s'],
                         noise_rel=sen['noise_rel'], noise_abs=sen['noise_abs'])
    est = make_estimator(frame, sc, noise_rel=sen['noise_rel'], noise_abs=sen['noise_abs'])
    tf = float(sc['time_factor'])
    rec = Recorder()

    # plume_points grid, as in gateway._plume_grid
    ss = np.linspace(2.0, frame.length - 2.0, 32)
    nn = np.linspace(-frame.width / 2 + 0.3, frame.width / 2 - 0.05, 31)
    S, N = np.meshgrid(ss, nn)
    grid_river = frame.from_sn(S.ravel(), N.ravel())
    glat, glon, _ = frame.river_to_geodetic(grid_river)
    grid_unit = est.unit_excess(grid_river)

    state = dict(state='IDLE', samples=0, battery=0.93)

    def latlon_arena(x, y):
        lat, lon, _ = frame.arena_to_geodetic(np.array([x, y], dtype=float))
        return r7(lat), r7(lon)

    def pose(robot):
        lat, lon = latlon_arena(robot.x, robot.y)
        rx, ry = frame.arena_to_river([robot.x, robot.y])
        heading = (90.0 - math.degrees(frame.arena_yaw_to_river(robot.yaw))) % 360.0
        rec.emit(dict(type='pose', t=round(robot.t, 3), lat=lat, lon=lon, heading_deg=round(heading, 2),
                      arena=dict(x=round(robot.x, 4), y=round(robot.y, 4), yaw=round(robot.yaw, 4)),
                      river=dict(x=round(float(rx), 3), y=round(float(ry), 3))))

    def second(robot):
        state['battery'] = max(0.0, state['battery'] - 0.0004)
        pct = state['battery']
        rec.emit(dict(type='battery', t=round(robot.t, 3), voltage=round(11.0 + 1.6 * pct, 2), percentage=round(pct, 3)))
        rec.emit(dict(type='mission', mode='SIM', state=state['state'], samples_taken=state['samples'], scenario='',
                      time_factor=tf, reach=frame.name))
        rec.emit(dict(type='sync', streams=[dict(name=n, state='SYNCED', staleness_s=0.2)
                                            for n in ('link', 'pose', 'samples')]))

    def event(kind, **data):
        rec.emit(dict(type='event', t=round(rec.t, 3), kind=kind, data=dict(data, state=state['state'])))

    def posterior_msg():
        marg = est.marginal()
        lab, p, q = est.map_estimate()
        return dict(type='posterior', labels=list(est.labels), probabilities=[round(float(v), 5) for v in marg],
                    map_label=lab, map_strength=round(float(q), 4))

    def plume_points(post):
        p = np.array(post['probabilities'], dtype=float)
        v = est.p.c_bg + post['map_strength'] * (p[:, None] * grid_unit).sum(axis=0)
        pts = [[r7(a), r7(b), round(float(c), 4)] for a, b, c in zip(glat, glon, v)]
        rec.emit(dict(type='plume_points', t=round(rec.t, 3), units='mg/L NH3-N', points=pts))

    hooks = dict(pose=pose, second=second)
    x0, y0, yaw0 = frame.arena['start_pose']
    robot = RecordingRobot(rec, hooks, frame, plume, sensor, tf, x0, y0, yaw0)

    rec.emit(dict(type='hello', reach=frame.name, reach_id=frame.reach_id, time_factor=tf,
                  origin=dict(lat=frame.lat0, lon=frame.lon0, h=frame.h0), scale=frame.scale,
                  commands=['abort', 'return_home', 'add_nogo', 'remove_nogo', 'add_obstacle', 'remove_obstacle'],
                  alert_mg_l=ALERT, replay=True,
                  scenario=dict(q_m3s=float(sc['flow']['q_m3s']), background_nh3_n_mg_l=sc['background']['nh3_n_mg_l'],
                                background_do_mg_l=sc['background']['do_mg_l'], time_factor=tf),
                  sensor=sen))
    first = posterior_msg()
    rec.emit(first)
    robot.wait(3.0)
    state['state'] = 'RUNNING'
    event('state', new='RUNNING')

    cands = frame.sampling_points()
    order = sweep_order(frame, cands, (x0, y0)) if args.strategy == 'sweep' else None
    sampled = []
    seq = 0
    done_label = None
    for k in range(CAP):
        if args.strategy == 'sweep':
            if k >= len(order):
                break
            idx = order[k]
        else:
            res = est.plan((robot.x, robot.y), cands, sampled, rng)
            if res is None:
                break
            idx = res[0]
        c = cands[idx]
        robot.wait(PLAN_OVERHEAD_S)
        wx, wy = c['waypoint']
        event('goal_sent', x=round(wx, 3), y=round(wy, 3), yaw=round(c['yaw'], 3))
        robot.drive_to(wx, wy, c['yaw'])
        event('goal_result', status=4)
        event('dwell')
        value = robot.dwell(int(round(sen['dwell_s'])))
        seq += 1
        state['samples'] = seq
        px, py = probe_point(robot.x, robot.y, robot.yaw)
        river = frame.arena_to_river([px, py])
        lat, lon, _ = frame.river_to_geodetic(np.asarray(river))
        do = float(plume.puffs.dissolved_oxygen(value))
        sample = dict(type='sample', seq=seq, t=round(robot.t, 3), lat=r7(lat), lon=r7(lon),
                      nh3_n_mg_l=round(value, 4), do_mg_l=round(do, 4), qc_flags=0, is_replay=False,
                      river=dict(x=round(float(river[0]), 3), y=round(float(river[1]), 3)),
                      arena=dict(x=round(robot.x, 4), y=round(robot.y, 4)))
        rec.emit(sample)
        est.update(river, value)
        sampled.append(c['waypoint'])
        post = posterior_msg()
        if value > ALERT:
            k_best = int(np.argmax(post['probabilities']))
            likely, prob = post['labels'][k_best], post['probabilities'][k_best]
            rec.emit(dict(type='alert', t=sample['t'], seq=seq, nh3_n_mg_l=sample['nh3_n_mg_l'], lat=sample['lat'],
                          lon=sample['lon'], likely_outfall=likely, probability=round(float(prob), 4),
                          message=f"NH₃-N above {ALERT} mg/L · {sample['lat']:.6f}, {sample['lon']:.6f} · "
                                  f"likely outfall {likely} ({prob * 100:.0f} %)"))
        rec.emit(post)
        event('sample', seq=seq, nh3=round(value, 4))
        plume_points(post)
        if args.strategy != 'sweep' and est.localised():
            done_label = post['map_label']
            break

    post = posterior_msg()
    done_label = done_label or post['map_label']
    event('done', final='DONE', samples=seq, map_label=done_label,
          probabilities=[round(v, 4) for v in post['probabilities']])
    state['state'] = 'DONE'
    event('state', new='DONE')
    robot.wait(2.0)
    event('return_home_start')
    robot.drive_to(x0, y0, yaw0)
    event('return_home', status=4)
    robot.wait(3.0)

    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, 'w') as f:
        for m in rec.out:
            f.write(json.dumps(m, ensure_ascii=False, allow_nan=False) + '\n')
    print(f'{out}: {len(rec.out)} messages, {robot.t:.0f} s, {seq} samples, result {done_label} '
          f'(truth {sc["active_outfall"]}), p = {max(post["probabilities"]):.3f}')


if __name__ == '__main__':
    main()
