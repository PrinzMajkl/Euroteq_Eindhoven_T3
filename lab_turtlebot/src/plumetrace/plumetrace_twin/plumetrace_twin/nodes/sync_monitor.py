"""sync_monitor (twin side): Synced / Stale / Lost per stream, published on /twin/sync at 2 Hz.

Streams: link (/twin/heartbeat), pose (/robot/pose), samples (backlog: samples produced on the robot
but not yet received by the twin), and optionally ghost (ghost model vs robot pose age, MIRROR mode).
Thresholds: stale after 0.5 s, lost after 3 s (simulation time).
"""
import rclpy
from geometry_msgs.msg import PoseStamped
from rclpy.node import Node
from std_msgs.msg import UInt32

from plumetrace_msgs.msg import SyncStatus

SYNCED, STALE, LOST = 0, 1, 2


class SyncMonitor(Node):
    def __init__(self):
        super().__init__('sync_monitor')
        self.declare_parameter('stale_s', 0.5)
        self.declare_parameter('lost_s', 3.0)
        self.declare_parameter('extra_streams', [''])
        self.stale_s = float(self.get_parameter('stale_s').value)
        self.lost_s = float(self.get_parameter('lost_s').value)
        self.last = {'link': None, 'pose': None}
        self.produced = 0
        self.received = 0
        self.backlog_since = None
        self.extra = {}  # name -> last time (fed via /twin/sync_beat/<name>)
        for name in [n for n in self.get_parameter('extra_streams').value if n]:
            self.extra[name] = None
            self.create_subscription(PoseStamped, f'/twin/sync_beat/{name}', self._beat(name), 10)
        self.create_subscription(UInt32, '/twin/heartbeat', self.on_hb, 10)
        self.create_subscription(PoseStamped, '/robot/pose', lambda m: self._mark('pose'), 10)
        self.create_subscription(UInt32, '/plume/ack', self.on_ack, 10)
        self.pub = self.create_publisher(SyncStatus, '/twin/sync', 10)
        self.create_timer(0.5, self.publish)

    def now_s(self):
        return self.get_clock().now().nanoseconds * 1e-9

    def _mark(self, k):
        self.last[k] = self.now_s()

    def _beat(self, name):
        """Extra streams carry the stamp of the data they applied: staleness = data age."""
        def cb(msg):
            st = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
            self.extra[name] = st if st > 0 else self.now_s()
        return cb

    def on_hb(self, msg):
        self._mark('link')
        self.produced = max(self.produced, msg.data)

    def on_ack(self, msg):
        self.received = max(self.received, msg.data)

    def state_of(self, age):
        if age is None or age >= self.lost_s:
            return LOST
        return STALE if age >= self.stale_s else SYNCED

    def publish(self):
        now = self.now_s()
        ages = {k: (None if v is None else now - v) for k, v in self.last.items()}
        if self.received < self.produced:
            if self.backlog_since is None:
                self.backlog_since = now
            ages['samples'] = now - self.backlog_since
        else:
            self.backlog_since = None
            ages['samples'] = 0.0 if ages['link'] is not None else None
        for k, v in self.extra.items():
            ages[k] = None if v is None else now - v
        msg = SyncStatus()
        msg.header.stamp = self.get_clock().now().to_msg()
        for k, age in ages.items():
            msg.streams.append(k)
            msg.states.append(self.state_of(age))
            msg.staleness_s.append(float(age) if age is not None else float('inf'))
        self.pub.publish(msg)


def main():
    rclpy.init()
    node = SyncMonitor()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass


if __name__ == '__main__':
    main()
