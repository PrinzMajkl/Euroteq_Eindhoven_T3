"""localization_monitor: watches the robot's position on the map during a mission and fixes it when it is lost.

While /mission/state is RUNNING it compares the laser scan with the map at AMCL's pose every `period_s` seconds,
and with the pose turned 180 deg about the arena centre (the arena is near-symmetric, see scanfit.py).
The robot counts as lost after `lost_checks` checks in a row where the pose does not fit (`lost_fit`) or its mirror
fits clearly better (`margin`). A pose that fits but is not clearly better than its mirror only reads SUSPECT
(normal along the outer walls of the near-symmetric arena). Then:
  1. /localization/status LOST: mission_controller cancels the Nav2 goal and holds (state HOLD, event hold
     with reason localization).
  2. RELOCALIZING: first without moving (AMCL updates on the spot; reset to the mirrored pose if that fits clearly
     better), else the global search: AMCL spreads its particles over the map and the robot turns on the spot.
     Costmaps are cleared afterwards.
  3. OK: mission_controller resumes and re-sends the goal. FAILED (after `attempts` searches): the mission is
     aborted, so tools/run_abc.py moves on (and localises again before the next mission).
/localization/status is std_msgs/String JSON: {"state": "OK"|"SUSPECT"|"LOST"|"RELOCALIZING"|"FAILED", "fit": ..,
"fit_mirror": ..}. SUSPECT is informational (mission_controller ignores it). The robot only turns once the mission
reports HOLD (Nav2 idle); if it does not within 30 s the monitor reports FAILED instead of turning.
published on every check and on every change.
"""
import json
import threading
import time
from types import SimpleNamespace

import rclpy
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from std_msgs.msg import String

from plumetrace_msgs.msg import MissionState

from ..localizer import Localizer
from ..scanfit import judge


class LocalizationMonitor(Node):
    def __init__(self):
        super().__init__('localization_monitor')
        p = {'enabled': True, 'period_s': 3.0, 'lost_fit': 0.5, 'lost_checks': 3, 'margin': 0.08,
             'min_fit': 0.65, 'keep_fit': 0.75, 'spin_speed': 0.4, 'turns': 2.0, 'attempts': 2,
             'max_std_xy': 0.12, 'max_std_yaw': 0.15}
        for k, v in p.items():
            self.declare_parameter(k, v)
        self.param_names = list(p)
        g = {k: self.get_parameter(k).value for k in p}
        self.cfg = SimpleNamespace(**g, home_timeout=180.0, force_global=False)
        self.loc = Localizer(self, self.cfg, say=lambda m: self.get_logger().info(m.strip()))
        self.status_pub = self.create_publisher(String, '/localization/status', 10)
        self.mission_state = None
        self.create_subscription(MissionState, '/mission/state', self.on_state, 10)
        self.status = 'OK'
        if g['enabled']:
            threading.Thread(target=self.loop, daemon=True).start()

    def on_state(self, msg):
        self.mission_state = msg.state

    def publish(self, state, **kw):
        self.status = state
        self.status_pub.publish(String(data=json.dumps(dict(state=state, **kw))))

    def loop(self):
        c = self.cfg
        while not self.loc.wait_inputs(timeout=30.0):
            pass
        bad = 0
        while rclpy.ok():
            for k in self.param_names:  # re-read: `ros2 param set /localization_monitor lost_fit 0.4` works mid-run
                setattr(c, k, self.get_parameter(k).value)
            time.sleep(c.period_s)
            if self.mission_state != 'RUNNING':
                bad = 0
                continue
            fit, fit_m = self.loc.scan_fit(n=2, wait=2.0)
            if fit is None:
                continue
            verdict = judge(fit, fit_m, c.lost_fit, c.margin)
            bad = bad + 1 if (fit < c.lost_fit or verdict == 'mirrored') else 0
            self.publish('OK' if verdict == 'ok' else 'SUSPECT', fit=round(fit, 2), fit_mirror=round(fit_m, 2))
            if bad >= c.lost_checks:
                bad = 0
                self.recover(fit, fit_m)

    def recover(self, fit, fit_m):
        c = self.cfg
        self.get_logger().warn(f'robot lost: scan fit {fit:.2f}, at the mirrored pose {fit_m:.2f}; holding the '
                               'mission and re-localising')
        self.publish('LOST', fit=round(fit, 2), fit_mirror=round(fit_m, 2))
        end = time.time() + 30.0  # mission_controller cancels the goal (or finishes the dwell, up to 20 s) and holds
        while self.mission_state != 'HOLD' and time.time() < end:
            time.sleep(0.1)
        if self.mission_state != 'HOLD':  # Nav2 may still be driving: never turn against it
            self.get_logger().error('mission did not hold within 30 s; not turning, aborting the mission instead')
            self.publish('FAILED', fit=round(fit, 2), fit_mirror=round(fit_m, 2))
            return
        time.sleep(1.0)
        self.publish('RELOCALIZING')
        if self.loc.cmd_pub is None:
            self.loc.make_cmd_pub()
        ok = False
        try:
            self.loc.settle()
            ok = self.loc.accept(c.keep_fit, 'on the spot') or self.loc.global_search()
        finally:
            self.loc.stop()
        if ok:
            for name in ('/global_costmap/clear_entirely_global_costmap',
                         '/local_costmap/clear_entirely_local_costmap'):
                self.loc.clear_costmap(name)
            self.get_logger().info('re-localised: resuming the mission')
            self.publish('OK')
        else:
            self.get_logger().error('re-localisation failed: the mission will be aborted')
            self.publish('FAILED')


def main():
    rclpy.init()
    node = LocalizationMonitor()
    ex = MultiThreadedExecutor(num_threads=3)
    ex.add_node(node)
    try:
        ex.spin()
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        node.loc.stop()


if __name__ == '__main__':
    main()
