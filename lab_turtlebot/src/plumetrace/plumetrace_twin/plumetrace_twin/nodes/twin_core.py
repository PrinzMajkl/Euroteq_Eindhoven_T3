"""twin_core: source estimator + next-sample planner on ROS.

Subscribes /twin/samples (PlumeSample, de-duplicated). After every sample it updates the grid
filter, publishes /twin/posterior (Posterior) and plans the next goal, published on /twin/next_goal
(PoseStamped, frame map; frame_id 'none' = nothing left to sample). /twin/plan_request (Empty)
asks for a goal without a new sample (mission start). Strategy 'adaptive' (expected entropy
reduction per metre, top 3 checked with Nav2 ComputePathToPose; ends at 95 %) or 'sweep' (fixed stops up- and
downstream of every outfall along the bank from the end nearest the robot; ends after the last stop).
The twin never sees the active outfall: only the reach geometry and the flow.
"""
import json
import threading
import time

import numpy as np
import rclpy
from geometry_msgs.msg import PoseStamped
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.time import Time
from std_msgs.msg import Empty, String
from tf2_ros import Buffer, TransformListener

from plumetrace_msgs.msg import PlumeSample, Posterior

from ..estimator import CAP, sweep_order
from ..reach import ReachFrame
from ..scenario import load_scenario, make_estimator
from ..sensor_model import QC_OFF_BANK, SENSOR_DEFAULTS
from ..simtools import Nav2Client, pose_stamped


class TwinCore(Node):
    def __init__(self):
        super().__init__('twin_core')
        self.declare_parameter('scenario', 'A')   # used for the flow only
        self.declare_parameter('strategy', 'adaptive')
        self.declare_parameter('seed', 1)
        self.declare_parameter('use_nav2_paths', True)
        self.declare_parameter('noise_rel', SENSOR_DEFAULTS['noise_rel'])  # the sensor's noise, for the likelihood
        self.declare_parameter('noise_abs', SENSOR_DEFAULTS['noise_abs'])
        sc = load_scenario(self.get_parameter('scenario').value)
        self.frame = ReachFrame.load()
        self.est = make_estimator(self.frame, sc, noise_rel=float(self.get_parameter('noise_rel').value),
                                  noise_abs=float(self.get_parameter('noise_abs').value))
        self.strategy = self.get_parameter('strategy').value
        if self.strategy not in ('adaptive', 'sweep'):
            raise ValueError(f"strategy must be 'adaptive' or 'sweep', not {self.strategy!r}")
        self.rng = np.random.default_rng(int(self.get_parameter('seed').value) + 101)
        self.cands = self.frame.sampling_points()
        self.order = None  # sweep: fixed on the first plan, from where the robot is then
        self.sampled = []
        self.lock = threading.Lock()
        self.cb = ReentrantCallbackGroup()
        self.nav = Nav2Client(self) if self.get_parameter('use_nav2_paths').value else None
        self.tf = Buffer()
        self.tfl = TransformListener(self.tf, self)
        self.post_pub = self.create_publisher(Posterior, '/twin/posterior', 10)
        self.goal_pub = self.create_publisher(PoseStamped, '/twin/next_goal', 10)
        self.info_pub = self.create_publisher(String, '/twin/planner_info', 10)
        self.create_subscription(PlumeSample, '/twin/samples', self.on_sample, 50, callback_group=self.cb)
        self.create_subscription(Empty, '/twin/plan_request', lambda _: self.plan_async(), 10, callback_group=self.cb)
        self.create_timer(1.0, self.publish_posterior, callback_group=self.cb)
        self.update_times = []

    def robot_xy(self):
        try:
            t = self.tf.lookup_transform('map', 'base_footprint', Time()).transform.translation
            return np.array([t.x, t.y])
        except Exception:
            return np.array(self.frame.arena['start_pose'][:2])

    def on_sample(self, msg):
        t0 = time.perf_counter()
        with self.lock:
            if not (msg.qc_flags & QC_OFF_BANK):
                self.est.update(np.array([msg.river_xy.x, msg.river_xy.y]), float(msg.nh3_n_mg_l))
            self.sampled.append(np.array([msg.arena_pose.x, msg.arena_pose.y]))
            dt = time.perf_counter() - t0
        self.publish_posterior()
        self.get_logger().info(f'sample seq {msg.seq}: {msg.nh3_n_mg_l:.3f} mg/L, posterior '
                               f'{np.round(self.est.marginal(), 3).tolist()} (update {dt * 1000:.0f} ms)')
        self.plan_async(update_s=dt)

    def publish_posterior(self):
        with self.lock:
            m = self.est.marginal()
            lab, p, q = self.est.map_estimate()
        msg = Posterior()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'map'
        msg.labels = list(self.est.labels)
        msg.probabilities = [float(v) for v in m]
        msg.map_label = lab
        msg.map_strength = float(q)
        self.post_pub.publish(msg)

    def plan_async(self, update_s=0.0):
        threading.Thread(target=self.plan, args=(update_s,), daemon=True).start()

    def plan(self, update_s=0.0):
        t0 = time.perf_counter()
        with self.lock:
            n = len(self.sampled)
            if self.strategy == 'sweep':
                if self.order is None:
                    self.order = sweep_order(self.frame, self.cands, self.robot_xy())
                done = n >= len(self.order)
            else:
                done = self.est.localised() or n >= CAP
            info = {}
            idx = None
            if not done:
                if self.strategy == 'sweep':
                    idx = self.order[n]
                    info = dict(stop=n + 1, stops=len(self.order))
                else:
                    path_len = None
                    if self.nav is not None:
                        def path_len(c):
                            return self.nav.path_length(c['waypoint'][0], c['waypoint'][1], c['yaw'])
                    res = self.est.plan(self.robot_xy(), self.cands, self.sampled, self.rng, path_len=path_len)
                    if res is not None:
                        idx, info = res
        plan_s = time.perf_counter() - t0
        if idx is None:
            ps = PoseStamped()
            ps.header.frame_id = 'none'
            ps.header.stamp = self.get_clock().now().to_msg()
        else:
            c = self.cands[idx]
            ps = pose_stamped(self, c['waypoint'][0], c['waypoint'][1], c['yaw'])
        self.goal_pub.publish(ps)
        info.update(index=idx, samples=n, plan_s=round(plan_s, 3), update_s=round(update_s, 4),
                    strategy=self.strategy, done=done)
        self.info_pub.publish(String(data=json.dumps(info)))


def main():
    rclpy.init()
    node = TwinCore()
    ex = MultiThreadedExecutor(num_threads=4)
    ex.add_node(node)
    try:
        ex.spin()
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass


if __name__ == '__main__':
    main()
