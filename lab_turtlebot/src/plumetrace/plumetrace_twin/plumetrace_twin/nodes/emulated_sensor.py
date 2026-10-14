"""emulated_sensor: NH3-N / DO probe on the robot, fed by the synthetic plume.

The lag state follows the true concentration at the probe point at 10 Hz (the robot's
localised pose from TF). A dwell starts on /sensor/trigger (std_msgs/UInt32 = request id): readings at
+1, +2, +3 s (1 Hz); the mean is published as plumetrace_msgs/PlumeSample on /plume/sample_raw.
The sample carries the robot's own localisation (map -> base_footprint) and the probe point in the
river frame. Plume clock = time_factor x simulation time since the node started.
"""
import math

import numpy as np
import rclpy
from geometry_msgs.msg import Point, Pose2D
from rclpy.node import Node
from rclpy.time import Time
from std_msgs.msg import UInt32
from tf2_ros import Buffer, TransformListener

from plumetrace_msgs.msg import PlumeSample

from ..reach import ReachFrame
from ..scenario import load_scenario, make_plume
from ..sensor_model import QC_MOVED, QC_OFF_BANK, QC_POSE_STALE, SensorModel, probe_point
from ..simtools import quat_to_yaw


class EmulatedSensor(Node):
    def __init__(self):
        super().__init__('emulated_sensor')
        self.declare_parameter('scenario', 'A')
        self.declare_parameter('seed', 1)
        self.declare_parameter('dwell_s', 3.0)
        self.declare_parameter('lag_s', 2.0)
        sc = load_scenario(self.get_parameter('scenario').value, self.get_parameter('seed').value)
        self.sc = sc
        self.frame = ReachFrame.load()
        self.water = self.frame.water_polygon_arena()
        self.plume = make_plume(self.frame, sc)
        self.time_factor = float(sc['time_factor'])
        seed = int(sc['noise_seed'])
        self.model = SensorModel(np.random.default_rng(seed * 1000 + 7), tau=self.get_parameter('lag_s').value)
        self.dwell_s = float(self.get_parameter('dwell_s').value)
        self.tf = Buffer()
        self.tfl = TransformListener(self.tf, self)
        self.t0 = None
        self.dwell = None  # dict(start, readings, pose0, req)
        self.pub = self.create_publisher(PlumeSample, '/plume/sample_raw', 10)
        self.create_subscription(UInt32, '/sensor/trigger', self.on_trigger, 10)
        self.last_step = None
        self.create_timer(0.1, self.tick)
        self.get_logger().info(f"scenario {sc['scenario']} (outfall {sc['active_outfall']}), seed {seed}")

    # --- helpers ---------------------------------------------------------
    def now_s(self):
        return self.get_clock().now().nanoseconds * 1e-9

    def river_time(self):
        return self.time_factor * (self.now_s() - self.t0)

    def est_pose(self):
        """(x, y, yaw, age_s) of map -> base_footprint, or None."""
        try:
            tr = self.tf.lookup_transform('map', 'base_footprint', Time())
        except Exception:
            return None
        t = tr.transform
        age = self.now_s() - (tr.header.stamp.sec + tr.header.stamp.nanosec * 1e-9)
        return t.translation.x, t.translation.y, quat_to_yaw(t.rotation), age

    def true_pose(self):
        p = self.est_pose()
        return p[:3] if p else None

    # --- loop -------------------------------------------------------------
    def tick(self):
        now = self.now_s()
        if now <= 0.0:
            return
        if self.t0 is None:
            self.t0 = now
            self.last_step = now
        tp = self.true_pose()
        if tp is None:
            return
        dt = now - self.last_step
        self.last_step = now
        self.plume.advance_to(self.river_time())
        c_true = float(self.plume.at_arena_xy(probe_point(*tp)[None, :])[0])
        self.model.step(max(dt, 0.0), c_true)
        if self.dwell is not None:
            d = self.dwell
            k = len(d['readings'])
            if now - d['start'] >= (k + 1) * 1.0 - 1e-6 and k < round(self.dwell_s):
                d['readings'].append(self.model.read())
                if len(d['readings']) == round(self.dwell_s):
                    self.finish_dwell()

    def on_trigger(self, msg):
        if self.t0 is None:
            return
        if self.dwell is not None:
            self.get_logger().warn('trigger ignored: dwell in progress')
            return
        self.dwell = dict(start=self.now_s(), readings=[], pose0=self.est_pose(), req=msg.data)

    def finish_dwell(self):
        d = self.dwell
        self.dwell = None
        pose = self.est_pose()
        msg = PlumeSample()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'map'
        msg.seq = 0  # assigned by edge_buffer
        qc = 0
        if pose is None:
            qc |= QC_POSE_STALE
            pose = (math.nan, math.nan, math.nan, math.inf)
        if pose[3] > 0.5:
            qc |= QC_POSE_STALE
        if d['pose0'] is not None and math.hypot(pose[0] - d['pose0'][0], pose[1] - d['pose0'][1]) > 0.01:
            qc |= QC_MOVED
        msg.arena_pose = Pose2D(x=float(pose[0]), y=float(pose[1]), theta=float(pose[2]))
        pp = probe_point(pose[0], pose[1], pose[2])
        from shapely.geometry import Point as SPoint
        if self.water.exterior.distance(SPoint(pp[0], pp[1])) > 0.05:
            qc |= QC_OFF_BANK
        rxy = self.frame.arena_to_river(pp)
        msg.river_xy = Point(x=float(rxy[0]), y=float(rxy[1]), z=0.0)
        c = float(np.mean(d['readings']))
        msg.nh3_n_mg_l = c
        msg.do_mg_l = float(self.plume.puffs.dissolved_oxygen(c))
        msg.qc_flags = qc
        msg.is_replay = False
        self.pub.publish(msg)
        self.get_logger().info(f"sample req {d['req']}: NH3-N {c:.3f} mg/L at river ({rxy[0]:.1f}, {rxy[1]:.1f}) qc {qc}")


def main():
    rclpy.init()
    node = EmulatedSensor()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass


if __name__ == '__main__':
    main()
