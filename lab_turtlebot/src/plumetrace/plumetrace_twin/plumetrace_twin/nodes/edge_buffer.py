"""edge_buffer (robot side): sequence numbers and store-and-forward for samples.

/plume/sample_raw -> assign seq -> keep until acknowledged -> /edge/sample_out.
Unacknowledged samples older than `resend_s` are re-sent with is_replay = true.
/edge/ack (std_msgs/UInt32) = highest contiguous seq received by the twin.
Also publishes /edge/heartbeat (UInt32: last seq produced) and /edge/pose (map -> base_footprint)
at 10 Hz so the twin side can tell a live link from a quiet one.
"""
import json
import os

import rclpy
from geometry_msgs.msg import PoseStamped
from rclpy.node import Node
from rclpy.time import Time
from std_msgs.msg import UInt32
from tf2_ros import Buffer, TransformListener

from plumetrace_msgs.msg import PlumeSample


class EdgeBuffer(Node):
    def __init__(self):
        super().__init__('edge_buffer')
        self.declare_parameter('resend_s', 1.0)
        self.declare_parameter('spool', '')  # optional JSONL spool file
        self.resend_s = float(self.get_parameter('resend_s').value)
        spool = self.get_parameter('spool').value
        self.spool = open(spool, 'a') if spool else None
        self.seq = 0
        self.acked = 0
        self.pending = {}  # seq -> [msg, last_sent_s]
        self.out = self.create_publisher(PlumeSample, '/edge/sample_out', 50)
        self.hb = self.create_publisher(UInt32, '/edge/heartbeat', 10)
        self.pose_pub = self.create_publisher(PoseStamped, '/edge/pose', 10)
        self.create_subscription(PlumeSample, '/plume/sample_raw', self.on_sample, 50)
        self.create_subscription(UInt32, '/edge/ack', self.on_ack, 50)
        self.tf = Buffer()
        self.tfl = TransformListener(self.tf, self)
        self.create_timer(0.1, self.tick)
        self.create_timer(0.25, self.resend)

    def now_s(self):
        return self.get_clock().now().nanoseconds * 1e-9

    def on_sample(self, msg):
        self.seq += 1
        msg.seq = self.seq
        msg.is_replay = False
        self.pending[self.seq] = [msg, self.now_s()]
        if self.spool:
            self.spool.write(json.dumps(dict(seq=msg.seq, stamp=msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9,
                                             x=msg.arena_pose.x, y=msg.arena_pose.y, nh3=msg.nh3_n_mg_l)) + '\n')
            self.spool.flush()
        self.out.publish(msg)

    def on_ack(self, msg):
        if msg.data > self.acked:
            self.acked = msg.data
            for s in [s for s in self.pending if s <= self.acked]:
                del self.pending[s]

    def resend(self):
        now = self.now_s()
        for s in sorted(self.pending):
            m, last = self.pending[s]
            if now - last >= self.resend_s:
                m.is_replay = True
                self.out.publish(m)
                self.pending[s][1] = now

    def tick(self):
        self.hb.publish(UInt32(data=self.seq))
        try:
            tr = self.tf.lookup_transform('map', 'base_footprint', Time())
        except Exception:
            return
        ps = PoseStamped()
        ps.header = tr.header
        ps.header.frame_id = 'map'
        ps.pose.position.x = tr.transform.translation.x
        ps.pose.position.y = tr.transform.translation.y
        ps.pose.orientation = tr.transform.rotation
        self.pose_pub.publish(ps)


def main():
    rclpy.init()
    node = EdgeBuffer()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass


if __name__ == '__main__':
    main()
