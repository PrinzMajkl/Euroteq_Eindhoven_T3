"""link_gate: stands in for the robot <-> laptop Wi-Fi link.

Relays robot -> twin: /edge/sample_out -> /plume/sample, /edge/heartbeat -> /twin/heartbeat,
/edge/pose -> /robot/pose; twin -> robot: /plume/ack -> /edge/ack.
Service /link_gate/set_enabled (std_srvs/SetBool): false drops everything (simulated link loss).
"""
import rclpy
from geometry_msgs.msg import PoseStamped
from rclpy.node import Node
from std_msgs.msg import UInt32
from std_srvs.srv import SetBool

from plumetrace_msgs.msg import PlumeSample

ROUTES = [
    (PlumeSample, '/edge/sample_out', '/plume/sample'),
    (UInt32, '/edge/heartbeat', '/twin/heartbeat'),
    (PoseStamped, '/edge/pose', '/robot/pose'),
    (UInt32, '/plume/ack', '/edge/ack'),
]


class LinkGate(Node):
    def __init__(self):
        super().__init__('link_gate')
        self.declare_parameter('enabled', True)
        self.enabled = bool(self.get_parameter('enabled').value)
        self.dropped = 0
        for typ, src, dst in ROUTES:
            pub = self.create_publisher(typ, dst, 50)
            self.create_subscription(typ, src, self._relay(pub), 50)
        self.create_service(SetBool, '/link_gate/set_enabled', self.on_set)

    def _relay(self, pub):
        def cb(msg):
            if self.enabled:
                pub.publish(msg)
            else:
                self.dropped += 1
        return cb

    def on_set(self, req, res):
        self.enabled = bool(req.data)
        res.success = True
        res.message = f"link {'enabled' if self.enabled else 'disabled'} (dropped so far: {self.dropped})"
        self.get_logger().info(res.message)
        return res


def main():
    rclpy.init()
    node = LinkGate()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass


if __name__ == '__main__':
    main()
