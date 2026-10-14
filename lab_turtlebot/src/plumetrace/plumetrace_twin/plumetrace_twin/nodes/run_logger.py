"""run_logger: CSV logs of a mission in ~/plumetrace_runs/<YYYYMMDD-HHMMSS>/ (or the run_dir parameter).

samples.csv   one row per sample received by the twin (/twin/samples), with WGS84 position
posterior.csv one row per posterior update (/twin/posterior)
events.csv    mission events (/mission/events) and state changes (/mission/state)
pose.csv      robot pose (map -> base_footprint) at 5 Hz, for the CZML replay track
"""
import csv
import json
import os

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.time import Time
from std_msgs.msg import String
from tf2_ros import Buffer, TransformListener

from plumetrace_msgs.msg import MissionState, PlumeSample, Posterior

from ..reach import ReachFrame
from ..simtools import make_run_dir, quat_to_yaw


def stamp_s(h):
    return h.stamp.sec + h.stamp.nanosec * 1e-9


class RunLogger(Node):
    def __init__(self):
        super().__init__('run_logger')
        self.declare_parameter('run_dir', '')
        d = self.get_parameter('run_dir').value or make_run_dir()
        os.makedirs(d, exist_ok=True)
        self.dir = d
        self.frame = ReachFrame.load()
        self.files = {}
        self.w = {}
        self._open('samples', ['seq', 't', 'arena_x', 'arena_y', 'arena_theta', 'river_x', 'river_y', 'lat', 'lon',
                               'nh3_n_mg_l', 'do_mg_l', 'qc_flags', 'is_replay'])
        self._open('posterior', ['t', 'p_A', 'p_B', 'p_C', 'map_label', 'map_strength'])
        self._open('events', ['t', 'type', 'state', 'data'])
        self._open('pose', ['t', 'x', 'y', 'yaw', 'lat', 'lon'])
        self.last_state = None
        self.tf = Buffer()
        self.tfl = TransformListener(self.tf, self)
        self.create_subscription(PlumeSample, '/twin/samples', self.on_sample, 50)
        self.create_subscription(Posterior, '/twin/posterior', self.on_post, 20)
        self.create_subscription(String, '/mission/events', self.on_event, 50)
        self.create_subscription(MissionState, '/mission/state', self.on_state, 10)
        self.create_timer(0.2, self.on_pose)
        self.last_post = None
        self.get_logger().info(f'logging to {d}')

    def _open(self, name, header):
        f = open(os.path.join(self.dir, f'{name}.csv'), 'w', newline='')
        self.files[name] = f
        self.w[name] = csv.writer(f)
        self.w[name].writerow(header)
        f.flush()

    def _row(self, name, row):
        self.w[name].writerow(row)
        self.files[name].flush()

    def now_s(self):
        return self.get_clock().now().nanoseconds * 1e-9

    def on_sample(self, m):
        lat, lon, _ = self.frame.river_to_geodetic(np.array([m.river_xy.x, m.river_xy.y]))
        self._row('samples', [m.seq, f'{stamp_s(m.header):.3f}', f'{m.arena_pose.x:.4f}', f'{m.arena_pose.y:.4f}',
                              f'{m.arena_pose.theta:.4f}', f'{m.river_xy.x:.3f}', f'{m.river_xy.y:.3f}', f'{float(lat):.8f}',
                              f'{float(lon):.8f}', f'{m.nh3_n_mg_l:.4f}', f'{m.do_mg_l:.4f}', m.qc_flags, int(m.is_replay)])

    def on_post(self, m):
        key = (tuple(round(v, 5) for v in m.probabilities), m.map_label)
        if key == self.last_post:
            return
        self.last_post = key
        p = dict(zip(m.labels, m.probabilities))
        self._row('posterior', [f'{stamp_s(m.header):.3f}'] + [f"{p.get(k, 0.0):.5f}" for k in 'ABC']
                  + [m.map_label, f'{m.map_strength:.4f}'])

    def on_event(self, m):
        e = json.loads(m.data)
        self._row('events', [e.get('t', f'{self.now_s():.3f}'), e.get('type'), e.get('state'), m.data])

    def on_state(self, m):
        if m.state != self.last_state:
            self.last_state = m.state
            self._row('events', [f'{stamp_s(m.header):.3f}', 'mission_state', m.state,
                                 json.dumps(dict(mode=m.mode, samples=m.samples_taken, scenario=m.scenario))])

    def on_pose(self):
        try:
            tr = self.tf.lookup_transform('map', 'base_footprint', Time())
        except Exception:
            return
        t = tr.transform
        lat, lon, _ = self.frame.arena_to_geodetic(np.array([t.translation.x, t.translation.y]))
        self._row('pose', [f'{self.now_s():.3f}', f'{t.translation.x:.4f}', f'{t.translation.y:.4f}',
                           f'{quat_to_yaw(t.rotation):.4f}', f'{float(lat):.8f}', f'{float(lon):.8f}'])


def main():
    rclpy.init()
    node = RunLogger()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass


if __name__ == '__main__':
    main()
