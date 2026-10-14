"""sample_ingest (twin side): de-duplicates /plume/sample by seq, publishes each new sample once on
/twin/samples, and acknowledges with /plume/ack (UInt32 = highest contiguous seq received)."""
import rclpy
from rclpy.node import Node
from std_msgs.msg import UInt32

from plumetrace_msgs.msg import PlumeSample


class SampleIngest(Node):
    def __init__(self):
        super().__init__('sample_ingest')
        self.seen = set()
        self.contig = 0
        self.pub = self.create_publisher(PlumeSample, '/twin/samples', 50)
        self.ack = self.create_publisher(UInt32, '/plume/ack', 10)
        self.create_subscription(PlumeSample, '/plume/sample', self.on_sample, 50)
        self.create_timer(0.5, self.send_ack)

    def on_sample(self, msg):
        if msg.seq in self.seen or msg.seq == 0:
            self.send_ack()
            return
        self.seen.add(msg.seq)
        while self.contig + 1 in self.seen:
            self.contig += 1
        self.pub.publish(msg)
        self.send_ack()

    def send_ack(self):
        self.ack.publish(UInt32(data=self.contig))


def main():
    rclpy.init()
    node = SampleIngest()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass


if __name__ == '__main__':
    main()
