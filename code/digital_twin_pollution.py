#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_msgs.msg import String

class DigitalTwin(Node):
    def __init__(self):
        super().__init__('pollution_digital_twin')
        self.samples = {}
        self.last_status = ''
        self.pub = self.create_publisher(String, '/navigation_decision', 10)
        self.create_subscription(String, '/pollution', self.on_sample, 10)
        self.create_subscription(String, '/robot_status', self.on_status, 10)
        self.get_logger().info('Digital Twin ready')

    def on_status(self, msg):
        self.last_status = msg.data

    def on_sample(self, msg):
        try:
            point, value, distance = msg.data.split(',')
            if point in self.samples:
                return
            value = float(value)
            distance = float(distance)
            self.samples[point] = {'ammonia_mg_l': value, 'distance_m': distance}
        except (ValueError, IndexError):
            self.get_logger().warning('Invalid pollution sample')
            return
        self.get_logger().info(f'{point}: {value} mg/L at travelled {distance:.2f} m')
        self.get_logger().info(f'Virtual state: {self.samples}; robot: {self.last_status}')
        decision = 'STOP' if point == 'P3' and value == 0.0 else 'CONTINUE'
        if point == 'P3':
            hotspot = max(self.samples, key=lambda p: self.samples[p]['ammonia_mg_l'])
            self.get_logger().info(f'Suspected hotspot: {hotspot} (not confirmed source)')
        out = String()
        out.data = decision
        self.pub.publish(out)
        self.get_logger().info(f'Digital Twin decision: {decision}')

def main():
    rclpy.init()
    node = DigitalTwin()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
