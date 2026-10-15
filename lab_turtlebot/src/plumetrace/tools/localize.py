#!/usr/bin/env python3
"""Let the TurtleBot find out where it is on the fixed map by itself, then (optionally) drive to the start mark.

    python3 tools/localize.py [--go-home] [--force-global] [--min-fit 0.65] [--timeout 120] [--sim-time]

Needs lab_nav (map server + AMCL + Nav2) running, as in every lab_mission launch. Steps:
  1. Check the pose AMCL has now (normally the start mark): if the laser scan already fits the map there,
     the robot is localised and nothing moves (skip with --force-global).
  2. Otherwise global localisation: AMCL spreads its particles over the whole map
     (/reinitialize_global_localization) and the robot turns slowly on the spot until AMCL agrees on one pose.
  3. The pose is accepted only if the scan fits the map there AND fits clearly better than at the mirrored
     pose (turned 180 deg about the arena centre). The arena is a near-symmetric rectangle, so AMCL can lock on
     the mirror; when the mirror fits clearly better, AMCL is reset to it (/initialpose). Up to three attempts.
  4. Costmaps are cleared (they filled with obstacles drawn at wrong poses during the search).
  5. --go-home: Nav2 drives the robot to the start mark (start_pose in config/reach_frame.yaml).

The robot only turns on the spot until it is localised; it drives only in step 5, through Nav2.
Exit code 0 when localised (and home, with --go-home), 1 otherwise. Ctrl-C stops the robot.
"""
import argparse
import math
import os
import sys
import threading
import time

import rclpy
from geometry_msgs.msg import PoseWithCovarianceStamped, Quaternion, Twist, TwistStamped
from nav_msgs.msg import OccupancyGrid
from rclpy.duration import Duration
from rclpy.parameter import Parameter
from rclpy.signals import SignalHandlerOptions
from rclpy.qos import QoSDurabilityPolicy, QoSProfile, QoSReliabilityPolicy, qos_profile_sensor_data
from rclpy.time import Time
from sensor_msgs.msg import LaserScan
from std_srvs.srv import Empty
from tf2_ros import Buffer, TransformListener

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get('PLUMETRACE_REPO', os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, 'plumetrace_twin'))
from plumetrace_twin.scanfit import DistanceField, fit_score, judge, mirror_pose, scan_endpoints  # noqa: E402

GOAL_SUCCEEDED = 4
LASER_MAX = 3.5  # same as AMCL's laser_max_range


def yaw_of(q):
    return math.atan2(2.0 * (q.w * q.z + q.x * q.y), 1.0 - 2.0 * (q.y * q.y + q.z * q.z))


class Localizer:
    def __init__(self, node, args):
        self.node = node
        self.args = args
        self.lock = threading.Lock()
        self.field = None
        self.pose = None        # latest /amcl_pose message
        self.pose_count = 0     # /amcl_pose messages received (AMCL publishes one per filter update)
        self.scans = []         # recent scans
        self.tf = Buffer(cache_time=Duration(seconds=20))
        self.tf_listener = TransformListener(self.tf, node)
        latched = QoSProfile(depth=1, durability=QoSDurabilityPolicy.TRANSIENT_LOCAL,
                             reliability=QoSReliabilityPolicy.RELIABLE)
        node.create_subscription(OccupancyGrid, '/map', self.on_map, latched)
        node.create_subscription(PoseWithCovarianceStamped, '/amcl_pose', self.on_pose, 10)
        node.create_subscription(LaserScan, '/scan', self.on_scan, qos_profile_sensor_data)
        self.reinit = node.create_client(Empty, '/reinitialize_global_localization')
        self.nomotion = node.create_client(Empty, '/request_nomotion_update')
        self.initial_pub = node.create_publisher(PoseWithCovarianceStamped, '/initialpose', 10)
        self.cmd_pub = None
        self.stamped = None

    # --- inputs ---------------------------------------------------------------------------------------
    def on_map(self, msg):
        info = msg.info
        try:
            field = DistanceField(msg.data, info.width, info.height, info.resolution,
                                  info.origin.position.x, info.origin.position.y)
        except ValueError:
            return
        with self.lock:
            self.field = field

    def on_pose(self, msg):
        with self.lock:
            self.pose = msg
            self.pose_count += 1

    def on_scan(self, msg):
        with self.lock:
            self.scans = (self.scans + [msg])[-5:]

    # --- helpers --------------------------------------------------------------------------------------
    def std(self):
        """(std x, std y, std yaw) of AMCL's latest pose, or None."""
        with self.lock:
            p = self.pose
        if p is None:
            return None
        c = p.pose.covariance
        return math.sqrt(max(c[0], 0.0)), math.sqrt(max(c[7], 0.0)), math.sqrt(max(c[35], 0.0))

    def pose_xyyaw(self):
        with self.lock:
            p = self.pose
        if p is None:
            return None
        q = p.pose.pose
        return q.position.x, q.position.y, yaw_of(q.orientation)

    def scan_fit(self, n=3, wait=4.0):
        """(fit, fit at the mirrored pose): mean over the next n scans, each placed with the map -> laser
        transform at its stamp. (None, None) without map, scans or transform."""
        with self.lock:
            field = self.field
        if field is None:
            return None, None
        scores, mirrored, seen, end = [], [], set(), time.time() + wait
        while len(scores) < n and time.time() < end:
            with self.lock:
                scans = list(self.scans)
            for s in scans:
                key = (s.header.stamp.sec, s.header.stamp.nanosec)
                if key in seen:
                    continue
                seen.add(key)
                try:
                    tf = self.tf.lookup_transform('map', s.header.frame_id, Time.from_msg(s.header.stamp),
                                                  timeout=Duration(seconds=0.5))
                except Exception:  # extrapolation (small clock offset): use the latest transform instead
                    try:
                        tf = self.tf.lookup_transform('map', s.header.frame_id, Time())
                    except Exception:
                        continue
                t = tf.transform
                pose = (t.translation.x, t.translation.y, yaw_of(t.rotation))
                for p, out in ((pose, scores), (mirror_pose(*pose, field.centre), mirrored)):
                    pts = scan_endpoints(s.ranges, s.angle_min, s.angle_increment, *p, s.range_min,
                                         min(s.range_max, LASER_MAX))
                    out.append(fit_score(field, pts))
            time.sleep(0.15)
        if not scores:
            return None, None
        return sum(scores) / len(scores), sum(mirrored) / len(mirrored)

    def assess(self, threshold, label):
        """'ok', 'mirrored' or 'unsure' for AMCL's current pose; prints the two fits."""
        fit, fit_m = self.scan_fit()
        if fit is None:
            print(f'  {label}: no scan fit (no map -> laser transform yet)', flush=True)
            return 'unsure'
        verdict = judge(fit, fit_m, threshold, self.args.margin)
        print(f'  {label}: scan fit {fit:.2f}, at the mirrored pose {fit_m:.2f} (need {threshold:.2f} and '
              f'{self.args.margin:.2f} better than the mirror) -> {verdict}', flush=True)
        return verdict

    def flip_to_mirror(self):
        """Reset AMCL to the mirrored pose (the arena's 180 deg ambiguity), then let it settle without moving."""
        with self.lock:
            field = self.field
        x, y, yaw = self.pose_xyyaw()
        mx, my, myaw = mirror_pose(x, y, yaw, field.centre)
        msg = PoseWithCovarianceStamped()
        msg.header.frame_id = 'map'
        msg.header.stamp = Time().to_msg()  # zero stamp: AMCL uses the latest transform
        msg.pose.pose.position.x, msg.pose.pose.position.y = mx, my
        msg.pose.pose.orientation = Quaternion(z=math.sin(myaw / 2), w=math.cos(myaw / 2))
        cov = [0.0] * 36
        cov[0] = cov[7] = 0.05 ** 2
        cov[35] = 0.08 ** 2
        msg.pose.covariance = cov
        print(f'  AMCL locked on the mirrored pose: resetting it to x {mx:+.2f} y {my:+.2f} '
              f'yaw {math.degrees(myaw):+.0f} deg', flush=True)
        with self.lock:
            before = self.pose_count
        self.initial_pub.publish(msg)
        end = time.time() + 3.0
        while time.time() < end:
            with self.lock:
                if self.pose_count != before:
                    break
            time.sleep(0.1)
        self.settle()

    def settle(self):
        for _ in range(3):  # a few updates without motion sharpen the estimate
            self.call(self.nomotion, timeout=2.0)
            time.sleep(0.3)
        time.sleep(0.5)

    def accept(self, threshold, label):
        """True when AMCL's pose is right; fixes a mirror lock once."""
        verdict = self.assess(threshold, label)
        if verdict == 'mirrored':
            self.flip_to_mirror()
            verdict = self.assess(threshold, label + ' after the reset')
        return verdict == 'ok'

    def call(self, client, timeout=5.0):
        if not client.wait_for_service(timeout_sec=timeout):
            return False
        fut = client.call_async(Empty.Request())
        end = time.time() + timeout
        while not fut.done() and time.time() < end:
            time.sleep(0.05)
        return fut.done()

    def make_cmd_pub(self):
        """Publish /cmd_vel with the type the robot subscribes with (TwistStamped on the stock Jazzy bringup)."""
        types = []
        end = time.time() + 5.0
        while not types and time.time() < end:
            types = dict(self.node.get_topic_names_and_types()).get('/cmd_vel', [])
            time.sleep(0.2)
        self.stamped = 'geometry_msgs/msg/Twist' not in types
        self.cmd_pub = self.node.create_publisher(TwistStamped if self.stamped else Twist, '/cmd_vel', 10)
        time.sleep(0.5)  # discovery

    def turn(self, wz):
        if self.cmd_pub is None:
            return
        tw = Twist()
        tw.angular.z = float(wz)
        if self.stamped:
            msg = TwistStamped()
            msg.header.stamp = self.node.get_clock().now().to_msg()
            msg.header.frame_id = 'base_link'
            msg.twist = tw
            self.cmd_pub.publish(msg)
        else:
            self.cmd_pub.publish(tw)

    def stop(self):
        for _ in range(5):
            self.turn(0.0)
            time.sleep(0.05)

    def converged(self):
        s = self.std()
        return s is not None and s[0] < self.args.max_std_xy and s[1] < self.args.max_std_xy and \
            s[2] < self.args.max_std_yaw

    def report(self, label):
        p, s = self.pose_xyyaw(), self.std()
        if p and s:
            print(f'  {label}: x {p[0]:+.2f} m  y {p[1]:+.2f} m  yaw {math.degrees(p[2]):+.0f} deg   '
                  f'(std {s[0]:.2f} m, {s[1]:.2f} m, {math.degrees(s[2]):.0f} deg)', flush=True)

    # --- the procedure --------------------------------------------------------------------------------
    def wait_inputs(self, timeout=30.0):
        end, kick = time.time() + timeout, time.time() + 2.0
        while time.time() < end:
            with self.lock:
                ok = self.field is not None and self.scans and self.pose is not None
                no_pose = self.pose is None
            if ok:
                return True
            if no_pose and time.time() > kick:
                # AMCL publishes /amcl_pose only after a filter update, and a robot standing still triggers none:
                # ask for one update without motion (also brings the pose to a late subscriber like this one)
                kick = time.time() + 2.0
                self.call(self.nomotion, timeout=1.0)
            time.sleep(0.3)
        with self.lock:
            missing = [n for n, v in (('/map', self.field), ('/scan', self.scans), ('/amcl_pose', self.pose))
                       if not v]
        print(f'  no data on {", ".join(missing)} after {timeout:.0f} s: is lab_nav (or lab_mission) running?',
              flush=True)
        return False

    def global_search(self):
        a = self.args
        turn_time = 2.0 * math.pi / a.spin_speed
        for attempt in range(1, a.attempts + 1):
            if not self.call(self.reinit):
                print('  AMCL service /reinitialize_global_localization not available', flush=True)
                return False
            time.sleep(0.5)
            with self.lock:
                start_count = self.pose_count
            print(f'  attempt {attempt}/{a.attempts}: particles spread over the whole map; turning on the spot',
                  flush=True)
            t0, good, last = time.time(), 0, start_count
            while time.time() - t0 < a.turns * turn_time:
                self.turn(a.spin_speed)
                time.sleep(0.1)
                with self.lock:
                    count = self.pose_count
                if count != last:  # a new filter update
                    last = count
                    good = good + 1 if self.converged() else 0
                    if good >= 3 and time.time() - t0 > 0.75 * turn_time:
                        break
            self.stop()
            self.settle()
            self.report('AMCL')
            if not self.converged():
                print('  AMCL has not settled on one pose yet', flush=True)
                continue
            if self.accept(a.min_fit, 'AMCL pose'):
                return True
            print('  the scan does not match the map well enough there: trying again', flush=True)
        return False

    def run(self):
        a = self.args
        print('localize: waiting for /map, /scan and /amcl_pose ...', flush=True)
        if not self.wait_inputs():
            return False
        self.make_cmd_pub()
        ok = False
        try:
            if not a.force_global:
                self.report('current AMCL pose')
                ok = self.accept(a.keep_fit, 'current pose')
                if ok:
                    print('  already localised: no global search needed', flush=True)
            if not ok:
                ok = self.global_search()
        finally:
            self.stop()
        if not ok:
            print('localize: FAILED. Set the pose by hand: RViz "2D Pose Estimate", or put the robot on the start mark '
                  'and restart the launch.', flush=True)
            return False
        for name in ('/global_costmap/clear_entirely_global_costmap', '/local_costmap/clear_entirely_local_costmap'):
            self.clear_costmap(name)
        self.report('localised')
        return True

    def clear_costmap(self, name):
        try:
            from nav2_msgs.srv import ClearEntireCostmap
        except ImportError:
            return
        c = self.node.create_client(ClearEntireCostmap, name)
        if c.wait_for_service(timeout_sec=3.0):
            fut = c.call_async(ClearEntireCostmap.Request())
            end = time.time() + 5.0
            while not fut.done() and time.time() < end:
                time.sleep(0.05)

    def go_home(self):
        from plumetrace_twin.reach import ReachFrame
        from plumetrace_twin.simtools import Nav2Client
        x, y, yaw = ReachFrame.load().arena['start_pose']
        nav = Nav2Client(self.node)
        if not nav.wait(30.0):
            print('  Nav2 navigate_to_pose is not available', flush=True)
            return False
        print(f'  driving to the start mark ({x:.2f}, {y:.2f}, yaw {math.degrees(yaw):.0f} deg) ...', flush=True)
        st, sec = nav.go(x, y, yaw, timeout=self.args.home_timeout)
        print(f'  {"on the start mark" if st == GOAL_SUCCEEDED else f"did not reach the start mark (status {st})"}'
              f' after {sec:.0f} s', flush=True)
        return st == GOAL_SUCCEEDED


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--go-home', action='store_true', help='drive to the start mark once localised')
    ap.add_argument('--force-global', action='store_true', help='always run the global search, even if the '
                    'current pose already fits')
    ap.add_argument('--min-fit', type=float, default=0.65, help='scan fit needed after the global search (0..1)')
    ap.add_argument('--keep-fit', type=float, default=0.75, help='scan fit at which the current pose is kept '
                    'without moving (0..1)')
    ap.add_argument('--margin', type=float, default=0.08, help='how much better the pose must fit than its '
                    'mirror (0..1)')
    ap.add_argument('--spin-speed', type=float, default=0.4, help='rad/s while searching')
    ap.add_argument('--turns', type=float, default=2.0, help='turns per attempt at most')
    ap.add_argument('--attempts', type=int, default=3)
    ap.add_argument('--max-std-xy', type=float, default=0.08, help='m')
    ap.add_argument('--max-std-yaw', type=float, default=0.15, help='rad')
    ap.add_argument('--home-timeout', type=float, default=180.0)
    ap.add_argument('--sim-time', action='store_true', help='Gazebo: use_sim_time:=true')
    args = ap.parse_args()

    # no rclpy SIGINT handler: Ctrl-C raises KeyboardInterrupt with the context still valid, so stop() reaches the robot
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    node = rclpy.create_node('plumetrace_localize')
    if args.sim_time:
        node.set_parameters([Parameter('use_sim_time', value=True)])
    loc = Localizer(node, args)
    threading.Thread(target=rclpy.spin, args=(node,), daemon=True).start()
    ok = False
    try:
        ok = loc.run()
        if ok and args.go_home:
            ok = loc.go_home()
    except KeyboardInterrupt:
        print('\nCtrl-C: stopping the robot', flush=True)
    finally:
        loc.stop()
        node.destroy_node()
        rclpy.try_shutdown()
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
