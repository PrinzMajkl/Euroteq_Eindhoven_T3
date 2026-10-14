"""Offline mission simulator (no ROS, no physics): kinematic robot + puff plume truth + emulated sensor.

The robot turns in place towards the next waypoint (1 rad/s), drives straight at 0.15 m/s, turns
to face the water, then dwells 3 s (readings at +1, +2, +3 s). The lag state runs at 10 Hz along
the probe path. The estimator sees the reported pose = true pose + localisation error (sigma 0.015 m,
0.02 rad, as measured for AMCL in A4). Plume clock = time factor x simulation time.
"""
import math
import time

import numpy as np

from .estimator import CAP, SourceEstimator, lawnmower_order
from .scenario import make_estimator, make_plume
from .sensor_model import SensorModel, probe_point

V, W, DT = 0.15, 1.0, 0.1
POSE_SIGMA, YAW_SIGMA = 0.015, 0.02
PLAN_OVERHEAD_S = 1.0  # Nav2 planning / goal hand-over per sample


def wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


class KinematicRobot:
    def __init__(self, frame, plume, sensor, time_factor, x, y, yaw):
        self.frame, self.plume, self.sensor, self.tf = frame, plume, sensor, time_factor
        self.x, self.y, self.yaw = x, y, yaw
        self.t = 0.0

    def _step(self):
        self.t += DT
        self.plume.advance_to(self.tf * self.t)
        c = float(self.plume.at_arena_xy(probe_point(self.x, self.y, self.yaw)[None, :])[0])
        self.sensor.step(DT, c)

    def wait(self, seconds):
        for _ in range(int(round(seconds / DT))):
            self._step()

    def turn_to(self, yaw):
        while abs(wrap(yaw - self.yaw)) > 1e-3:
            d = wrap(yaw - self.yaw)
            self.yaw = wrap(self.yaw + math.copysign(min(abs(d), W * DT), d))
            self._step()

    def drive_to(self, x, y, yaw):
        d = math.hypot(x - self.x, y - self.y)
        if d > 1e-3:
            self.turn_to(math.atan2(y - self.y, x - self.x))
            n = max(1, int(math.ceil(d / (V * DT))))
            x0, y0 = self.x, self.y
            for k in range(1, n + 1):
                self.x, self.y = x0 + (x - x0) * k / n, y0 + (y - y0) * k / n
                self._step()
        self.turn_to(yaw)

    def dwell(self, n=3):
        vals = []
        for _ in range(n):
            self.wait(1.0)
            vals.append(self.sensor.read())
        return float(np.mean(vals))


def run_mission(frame, sc, seed, strategy='adaptive', cap=CAP):
    rng = np.random.default_rng(seed)
    plume = make_plume(frame, sc)
    sensor = SensorModel(np.random.default_rng(seed * 1000 + 7))
    x0, y0, yaw0 = frame.arena['start_pose']
    robot = KinematicRobot(frame, plume, sensor, float(sc['time_factor']), x0, y0, yaw0)
    est = make_estimator(frame, sc)
    cands = frame.sampling_points()
    order = lawnmower_order(cands) if strategy == 'lawnmower' else None
    sampled, rows, update_s = [], [], []
    localised_at = None
    for k in range(cap):
        t_plan = time.perf_counter()
        if strategy == 'lawnmower':
            if k >= len(order):
                break
            idx = order[k]
        else:
            res = est.plan((robot.x, robot.y), cands, sampled, rng)
            if res is None:
                break
            idx = res[0]
        plan_s = time.perf_counter() - t_plan
        c = cands[idx]
        robot.wait(PLAN_OVERHEAD_S)
        robot.drive_to(c['waypoint'][0], c['waypoint'][1], c['yaw'])
        value = robot.dwell()
        ex, ey = robot.x + rng.normal(0, POSE_SIGMA), robot.y + rng.normal(0, POSE_SIGMA)
        eyaw = robot.yaw + rng.normal(0, YAW_SIGMA)
        river = frame.arena_to_river(probe_point(ex, ey, eyaw))
        t_up = time.perf_counter()
        marg = est.update(river, value)
        update_s.append(time.perf_counter() - t_up + plan_s)
        sampled.append(c['waypoint'])
        lab, p, q = est.map_estimate()
        rows.append(dict(k=k + 1, idx=idx, t=round(robot.t, 1), value=round(value, 4),
                         probs=[round(float(v), 4) for v in marg], map=lab, p=round(p, 4), q=round(q, 3)))
        if localised_at is None and est.localised():
            localised_at = (k + 1, robot.t, lab)
            break
    truth = sc['active_outfall']
    return dict(scenario=sc['scenario'], seed=seed, strategy=strategy,
                localised=localised_at is not None,
                samples=localised_at[0] if localised_at else None,
                time_s=round(localised_at[1], 1) if localised_at else None,
                label=localised_at[2] if localised_at else est.map_estimate()[0],
                correct=bool(localised_at and localised_at[2] == truth),
                max_update_s=round(max(update_s), 4) if update_s else 0.0,
                mean_update_s=round(float(np.mean(update_s)), 4) if update_s else 0.0,
                total_samples=len(rows), rows=rows)
