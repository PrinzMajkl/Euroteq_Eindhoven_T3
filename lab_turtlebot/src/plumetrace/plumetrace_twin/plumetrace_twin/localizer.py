"""Self-localisation on the fixed map: shared by tools/localize.py (before each mission) and the
localization_monitor node (during a mission).

Localizer(node, args) needs a node that is being spun by an executor in another thread (callbacks arrive while
its methods wait). args carries the thresholds: min_fit, keep_fit, margin, spin_speed, turns, attempts,
max_std_xy, max_std_yaw, home_timeout (see tools/localize.py for their meaning and defaults).

  accept(threshold, label)  scan fits at AMCL's pose and clearly better than at the mirrored pose; if the
                            mirror fits clearly better, AMCL is reset to it. No motion.
  global_search()           AMCL spreads its particles over the whole map, the robot turns on the spot until
                            AMCL settles, then accept(). Up to `attempts` times.
  run()                     accept(keep_fit) (unless force_global), else global_search(); clears costmaps.
  go_home()                 Nav2 to start_pose in config/reach_frame.yaml.
"""
import math
import threading
import time

from geometry_msgs.msg import PoseWithCovarianceStamped, Quaternion, Twist, TwistStamped
from nav_msgs.msg import OccupancyGrid
from rclpy.duration import Duration
from rclpy.qos import QoSDurabilityPolicy, QoSProfile, QoSReliabilityPolicy, qos_profile_sensor_data
from rclpy.time import Time
from sensor_msgs.msg import LaserScan
from std_srvs.srv import Empty
from tf2_ros import Buffer, TransformListener

from .scanfit import DistanceField, fit_score, judge, mirror_pose, scan_endpoints

GOAL_SUCCEEDED = 4
LASER_MAX = 3.5  # same as AMCL's laser_max_range


def yaw_of(q):
    return math.atan2(2.0 * (q.w * q.z + q.x * q.y), 1.0 - 2.0 * (q.y * q.y + q.z * q.z))


class Localizer:
    def __init__(self, node, args, say=None):
        self.node = node
        self.args = args
        self.say = say or (lambda m: print(m, flush=True))
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
            self.say(f'  {label}: no scan fit (no map -> laser transform yet)')
            return 'unsure'
        verdict = judge(fit, fit_m, threshold, self.args.margin)
        self.say(f'  {label}: scan fit {fit:.2f}, at the mirrored pose {fit_m:.2f} (need {threshold:.2f} and '
              f'{self.args.margin:.2f} better than the mirror) -> {verdict}')
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
        self.say(f'  AMCL locked on the mirrored pose: resetting it to x {mx:+.2f} y {my:+.2f} '
              f'yaw {math.degrees(myaw):+.0f} deg')
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
            self.say(f'  {label}: x {p[0]:+.2f} m  y {p[1]:+.2f} m  yaw {math.degrees(p[2]):+.0f} deg   '
                  f'(std {s[0]:.2f} m, {s[1]:.2f} m, {math.degrees(s[2]):.0f} deg)')

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
        self.say(f'  no data on {", ".join(missing)} after {timeout:.0f} s: is lab_nav (or lab_mission) running?')
        return False

    def global_search(self):
        a = self.args
        turn_time = 2.0 * math.pi / a.spin_speed
        for attempt in range(1, a.attempts + 1):
            if not self.call(self.reinit):
                self.say('  AMCL service /reinitialize_global_localization not available')
                return False
            time.sleep(0.5)
            with self.lock:
                start_count = self.pose_count
            self.say(f'  attempt {attempt}/{a.attempts}: particles spread over the whole map; turning on the spot')
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
                self.say('  AMCL has not settled on one pose yet')
                continue
            if self.accept(a.min_fit, 'AMCL pose'):
                return True
            self.say('  the scan does not match the map well enough there: trying again')
        return False

    def run(self):
        a = self.args
        self.say('localize: waiting for /map, /scan and /amcl_pose ...')
        if not self.wait_inputs():
            return False
        self.make_cmd_pub()
        ok = False
        try:
            if not a.force_global:
                self.report('current AMCL pose')
                ok = self.accept(a.keep_fit, 'current pose')
                if ok:
                    self.say('  already localised: no global search needed')
            if not ok:
                ok = self.global_search()
        finally:
            self.stop()
        if not ok:
            self.say('localize: FAILED. Set the pose by hand: RViz "2D Pose Estimate", or put the robot on the start mark '
                  'and restart the launch.')
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
        from .reach import ReachFrame
        from .simtools import Nav2Client
        x, y, yaw = ReachFrame.load().arena['start_pose']
        nav = self.nav = Nav2Client(self.node)  # kept so tools/localize.py can cancel it on Ctrl-C
        if not nav.wait(30.0):
            self.say('  Nav2 navigate_to_pose is not available')
            return False
        self.say(f'  driving to the start mark ({x:.2f}, {y:.2f}, yaw {math.degrees(yaw):.0f} deg) ...')
        st, sec = nav.go(x, y, yaw, timeout=self.args.home_timeout)
        self.say(f'  {"on the start mark" if st == GOAL_SUCCEEDED else f"did not reach the start mark (status {st})"}'
              f' after {sec:.0f} s')
        return st == GOAL_SUCCEEDED
