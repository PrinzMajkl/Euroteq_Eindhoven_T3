import math
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan
from nav_msgs.msg import Odometry
from geometry_msgs.msg import TwistStamped


class SafeNavigation(Node):

    def __init__(self):
        super().__init__('safe_navigation')

        # Conservative settings for initial Gazebo testing
        self.safe_distance = 0.60
        self.stop_distance = 0.45
        self.forward_speed = 0.03
        self.turn_speed = 0.25

        self.scan = None
        self.scan_time = None

        self.start = None
        self.previous = None
        self.current = None
        self.total_distance = 0.0

        self.turning = False
        self.turn_direction = 1.0

        self.create_subscription(
            LaserScan,
            '/scan',
            self.scan_callback,
            qos_profile_sensor_data
        )

        self.create_subscription(
            Odometry,
            '/odom',
            self.odom_callback,
            qos_profile_sensor_data
        )

        self.publisher = self.create_publisher(
            TwistStamped,
            '/cmd_vel',
            10
        )

        self.create_timer(0.1, self.control)

    def scan_callback(self, msg):
        self.scan = msg
        self.scan_time = time.monotonic()

    def odom_callback(self, msg):
        p = msg.pose.pose.position
        current = (p.x, p.y)

        if self.start is None:
            self.start = current

        if self.previous is not None:
            step = math.hypot(
                current[0] - self.previous[0],
                current[1] - self.previous[1]
            )

            if step < 0.20:
                self.total_distance += step

        self.previous = current
        self.current = current

    def sector(self, low, high):
        if self.scan is None:
            return None

        values = []

        for i, d in enumerate(self.scan.ranges):
            angle = math.degrees(
                self.scan.angle_min +
                i * self.scan.angle_increment
            )
            angle = (angle + 180) % 360 - 180

            if low <= angle <= high:
                if math.isfinite(d):
                    if self.scan.range_min <= d <= self.scan.range_max:
                        values.append(d)
                elif math.isinf(d) and d > 0:
                    values.append(float('inf'))

        return min(values) if values else None

    def send_command(self, linear, angular):
        msg = TwistStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'base_link'
        msg.twist.linear.x = float(linear)
        msg.twist.angular.z = float(angular)
        self.publisher.publish(msg)

    def control(self):

        if (
            self.scan is None
            or self.scan_time is None
            or time.monotonic() - self.scan_time > 1.0
            or self.current is None
        ):
            self.send_command(0.0, 0.0)
            return

        front = self.sector(-35, 35)
        left = self.sector(35, 100)
        right = self.sector(-100, -35)

        if front is None or left is None or right is None:
            self.send_command(0.0, 0.0)
            return

        # If already turning, keep turning until front is clear.
        if self.turning:
            if front > self.safe_distance + 0.15:
                self.turning = False
            else:
                self.send_command(
                    0.0,
                    self.turn_direction * self.turn_speed
                )
                return

        if front < self.safe_distance:
            self.turning = True
            self.turn_direction = 1.0 if left >= right else -1.0

            self.send_command(
                0.0,
                self.turn_direction * self.turn_speed
            )

            action = 'TURN LEFT' if self.turn_direction > 0 else 'TURN RIGHT'

        else:
            self.send_command(self.forward_speed, 0.0)
            action = 'FORWARD'

        sx, sy = self.start
        x, y = self.current

        displacement = math.hypot(x - sx, y - sy)

        self.get_logger().info(
            f'{action} | '
            f'front={front:.2f}m | '
            f'left={left:.2f}m | '
            f'right={right:.2f}m | '
            f'from_start={displacement:.2f}m | '
            f'travelled={self.total_distance:.2f}m',
            throttle_duration_sec=1.0
        )

    def stop(self):
        if rclpy.ok():
            try:
                self.send_command(0.0, 0.0)
            except Exception as e:
                self.get_logger().warning(f'Unable to send stop: {e}')


def main():
    rclpy.init()
    node = SafeNavigation()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.stop()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
