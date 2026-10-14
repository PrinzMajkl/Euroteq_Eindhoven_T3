#!/usr/bin/env python3
"""Gazebo TurtleBot3 direct LiDAR navigation + synthetic water sensor (ROS 2 Jazzy).

The sensor is illustrative, NOT a regulatory-grade measurement. Values are
computed from the robot's local X/Y pose, not from hard-coded checkpoint IDs.
"""
import json
import math
import time

import rclpy
from geometry_msgs.msg import TwistStamped
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import BatteryState, LaserScan
from std_msgs.msg import String

# Illustrative spatial NH3-N profile: (metres along initial forward heading, mg/L).
# Add as many points as desired; interpolation works between all of them.
# These concentrations are SYNTHETIC TEST VALUES, not EU limits.
MOCK_PLUME_PROFILE = [
    (0.0, 2.0), (0.10, 2.0), (0.60, 5.0), (0.90, 9.0),
    (1.00, 0.0), (1.50, 0.0),
]


def interpolate_profile(progress_m):
    profile = MOCK_PLUME_PROFILE
    if progress_m <= profile[0][0]:
        return profile[0][1]
    for (x0, y0), (x1, y1) in zip(profile, profile[1:]):
        if progress_m <= x1:
            t = (progress_m - x0) / (x1 - x0)
            return y0 + t * (y1 - y0)
    return profile[-1][1]


class SafeNavigation(Node):
    def __init__(self):
        super().__init__('safe_navigation')
        self.declare_parameter('safe_distance_m', 0.60)
        self.declare_parameter('forward_speed_mps', 0.10)
        self.declare_parameter('turn_speed_radps', 0.25)
        self.declare_parameter('sensor_interval_sec', 2.0)
        self.declare_parameter('sensor_distance_step_m', 0.08)
        self.declare_parameter('plume_width_m', 1.5)
        self.declare_parameter('simulate_battery_if_absent', True)
        self.declare_parameter('initial_sim_battery_percent', 95.0)
        self.declare_parameter('sim_battery_runtime_min', 90.0)
        self.declare_parameter('waypoint_timeout_sec', 110.0)
        self.declare_parameter('turn_in_place_error_rad', 0.30)
        self.safe_distance = float(self.get_parameter('safe_distance_m').value)
        self.forward_speed = float(self.get_parameter('forward_speed_mps').value)
        self.turn_speed = float(self.get_parameter('turn_speed_radps').value)
        self.sensor_interval = float(self.get_parameter('sensor_interval_sec').value)
        self.sensor_distance_step = float(self.get_parameter('sensor_distance_step_m').value)
        self.plume_width = float(self.get_parameter('plume_width_m').value)
        if self.sensor_interval <= 0 or self.sensor_distance_step <= 0 or self.plume_width <= 0:
            raise ValueError('Sensor interval, distance step, and plume width must be positive')

        self.scan = None
        self.scan_time = None
        self.start = None
        self.start_yaw = None
        self.previous = None
        self.current = None
        self.yaw = 0.0
        self.speed = 0.0
        self.total_distance = 0.0
        self.turning = False
        self.turn_direction = 1.0
        self.finished = False  # STOP is latched for this run
        self.sample_id = 0
        self.last_sample_at = time.monotonic()
        self.last_sample_distance = 0.0
        self.robot_status = 'WAITING_FOR_ODOM'
        self.battery_percentage = None  # real /battery_state only; Gazebo may not publish it
        self.battery_voltage_v = None
        self.battery_last_update = None
        self.sim_battery_initial = min(100.,max(0.,float(self.get_parameter('initial_sim_battery_percent').value)))
        self.sim_battery_runtime_min = max(1.,float(self.get_parameter('sim_battery_runtime_min').value))
        self.simulate_battery = bool(self.get_parameter('simulate_battery_if_absent').value)
        self.battery_start = time.monotonic()
        self.pause_for_twin = False
        self.target = None
        self.goal_started = None
        self.arrival_tolerance = 0.25
        self.avoid_until = 0.0
        self.avoid_turn_direction = 1.0
        self.event_pub=self.create_publisher(String,'/twin_mission_event',10)
        self.create_subscription(String,'/twin_waypoint',self.waypoint_callback,10)

        self.pollution_pub = self.create_publisher(String, '/pollution', 10)
        self.status_pub = self.create_publisher(String, '/robot_status', 10)
        self.publisher = self.create_publisher(TwistStamped, '/cmd_vel', 10)
        self.create_subscription(String, '/navigation_decision', self.decision_callback, 10)
        self.create_subscription(LaserScan, '/scan', self.scan_callback, qos_profile_sensor_data)
        self.create_subscription(BatteryState, '/battery_state', self.battery_callback, qos_profile_sensor_data)
        self.create_subscription(Odometry, '/odom', self.odom_callback, qos_profile_sensor_data)
        self.create_timer(0.1, self.control)
        self.create_timer(0.5, self.publish_status)
        self.create_timer(0.2, self.sample_if_needed)
        self.get_logger().info('Safe navigation + position-based mock sensor ready')

    def battery_callback(self, msg):
        # BatteryState percentage is 0..1 (not 0..100). NaN means unavailable.
        self.battery_percentage = round(msg.percentage * 100, 2) if math.isfinite(msg.percentage) and 0 <= msg.percentage <= 1 else None
        self.battery_voltage_v = round(msg.voltage, 2) if math.isfinite(msg.voltage) and msg.voltage >= 0 else None
        self.battery_last_update = time.monotonic()

    def scan_callback(self, msg):
        self.scan = msg
        self.scan_time = time.monotonic()

    def odom_callback(self, msg):
        p = msg.pose.pose.position
        q = msg.pose.pose.orientation
        current = (p.x, p.y)
        yaw = math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))
        if self.start is None:
            self.start = current
            self.start_yaw = yaw
        if self.previous is not None:
            step = math.hypot(current[0] - self.previous[0], current[1] - self.previous[1])
            if step < 0.20:
                self.total_distance += step
        self.previous = current
        self.current = current
        self.yaw = yaw
        v = msg.twist.twist.linear
        self.speed = math.hypot(v.x, v.y)

    def sector(self, low, high):
        if self.scan is None:
            return None
        values = []
        for i, d in enumerate(self.scan.ranges):
            a = math.degrees(self.scan.angle_min + i * self.scan.angle_increment)
            a = (a + 180) % 360 - 180
            if low <= a <= high:
                if math.isfinite(d) and self.scan.range_min <= d <= self.scan.range_max:
                    values.append(d)
                elif math.isinf(d) and d > 0:
                    values.append(float('inf'))
        return min(values) if values else None

    def finite_front_distance(self):
        front = self.sector(-35, 35)
        return front if front is not None and math.isfinite(front) else None

    def send_command(self, linear, angular):
        msg = TwistStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'base_link'
        msg.twist.linear.x = float(linear)
        msg.twist.angular.z = float(angular)
        self.publisher.publish(msg)

    def event(self,status,reason=None):
        payload={'status':status,'timestamp':self.get_clock().now().nanoseconds/1e9}
        if reason:payload['reason']=reason
        m=String();m.data=json.dumps(payload);self.event_pub.publish(m)
        self.get_logger().info('Mission event: '+m.data)

    def decision_callback(self, msg):
        command = msg.data.strip().upper()
        if command == 'PAUSE' and not self.finished:
            self.pause_for_twin = True
            self.robot_status = 'PAUSED_FOR_TWIN'
            self.send_command(0.0, 0.0)
        elif command == 'STOP':
            self.finished = True
            self.target = None
            self.pause_for_twin = True
            self.robot_status = 'STOPPED_BY_TWIN'
            self.send_command(0.0, 0.0)
            self.get_logger().warning('STOP latched')

    def waypoint_callback(self, msg):
        if self.finished or self.target is not None:
            return
        try:
            target = json.loads(msg.data)
            x, y = float(target['x']), float(target['y'])
            tolerance = float(target.get('tolerance_m', 0.25))
            if target.get('frame_id') != 'odom' or not all(map(math.isfinite, (x, y, tolerance))):
                raise ValueError('Target must be finite and in frame_id=odom')
            if not 0.10 <= tolerance <= 0.50:
                raise ValueError('Target tolerance outside safe allowed range')
        except (ValueError, TypeError, KeyError) as e:
            self.event('REJECTED', str(e))
            return
        self.target = (x, y)
        self.arrival_tolerance = tolerance
        self.goal_started = time.monotonic()
        self.pause_for_twin = False
        self.turning = False
        self.avoid_until = 0.0
        self.robot_status = 'NAVIGATING_TO_HOTSPOT'
        self.event('ACCEPTED')
        self.get_logger().warning(f'No-Nav2 hotspot target accepted: x={x:.2f}, y={y:.2f}')

    @staticmethod
    def angle_error(target_angle, current_angle):
        return math.atan2(math.sin(target_angle - current_angle),
                          math.cos(target_angle - current_angle))

    def fail_goal(self, reason):
        self.finished = True
        self.target = None
        self.robot_status = 'GOAL_FAILED'
        self.send_command(0.0, 0.0)
        self.event('FAILED', reason)

    def publish_status(self):
        now=time.monotonic()
        real_battery=self.battery_last_update is not None and now-self.battery_last_update<10
        if real_battery and self.battery_percentage is not None:
            battery=self.battery_percentage
            voltage=self.battery_voltage_v
            source='ROS_BATTERY_STATE'
            simulated=False
            remaining=None
        elif self.simulate_battery:
            # Educational approximation only: fixed total operating duration.
            elapsed_min=(now-self.battery_start)/60.0
            consumption_per_min=self.sim_battery_initial/self.sim_battery_runtime_min
            battery=round(max(0.,self.sim_battery_initial-elapsed_min*consumption_per_min),2)
            voltage=None
            source='SIMULATED_RUNTIME_MODEL'
            simulated=True
            remaining=round(battery/consumption_per_min,1)
        else:
            battery=None;voltage=None;source='UNAVAILABLE';simulated=False;remaining=None
        msg = String()
        msg.data = json.dumps({
            'timestamp': self.get_clock().now().nanoseconds / 1e9,
            'x': self.current[0] if self.current else None,
            'y': self.current[1] if self.current else None,
            'yaw': self.yaw,
            'velocity_mps': self.speed,
            'distance_m': round(self.total_distance, 3),
            'nearest_obstacle_m': self.finite_front_distance(),
            'status': self.robot_status,
            'finished': self.finished,
            'battery_percent': battery,
            'battery_voltage_v': voltage,
            'battery_source': source,
            'battery_is_simulated': simulated,
            'battery_estimated_remaining_min': remaining,
        }, allow_nan=False)
        self.status_pub.publish(msg)

    def sample_if_needed(self):
        if self.current is None or self.finished or self.pause_for_twin or self.target is not None:
            return
        now = time.monotonic()
        # One sample when time OR movement criterion is met; no finite checkpoint list.
        if (now - self.last_sample_at < self.sensor_interval and
                self.total_distance - self.last_sample_distance < self.sensor_distance_step):
            return
        dx = self.current[0] - self.start[0]
        dy = self.current[1] - self.start[1]
        along = dx * math.cos(self.start_yaw) + dy * math.sin(self.start_yaw)
        lateral = -dx * math.sin(self.start_yaw) + dy * math.cos(self.start_yaw)
        lateral_factor = math.exp(-0.5 * (lateral / self.plume_width) ** 2)
        ammonia = max(0.0, interpolate_profile(along) * lateral_factor)
        oxygen = max(0.0, 8.5 - 0.45 * ammonia)
        self.sample_id += 1
        payload = {
            'sample_id': self.sample_id,
            'timestamp': self.get_clock().now().nanoseconds / 1e9,
            'x': round(self.current[0], 4),
            'y': round(self.current[1], 4),
            'distance_m': round(self.total_distance, 4),
            'nh3_n_mg_l': round(ammonia, 4),
            'do_mg_l': round(oxygen, 3),
            'sensor_type': 'SYNTHETIC_POSITION_BASED',
        }
        msg = String()
        msg.data = json.dumps(payload)
        self.pollution_pub.publish(msg)
        self.last_sample_at = now
        self.last_sample_distance = self.total_distance
        self.get_logger().info('Sensor sample: ' + msg.data)

    def control(self):
        if self.finished:
            self.send_command(0.0, 0.0)
            return
        if self.current is None:
            self.robot_status = 'WAITING_FOR_ODOM'
            self.send_command(0.0, 0.0)
            return
        if self.scan is None or self.scan_time is None or time.monotonic() - self.scan_time > 1.5:
            self.robot_status = 'WAITING_FOR_SCAN'
            self.send_command(0.0, 0.0)
            return
        front = self.sector(-30, 30)
        left = self.sector(35, 100)
        right = self.sector(-100, -35)
        if front is None or left is None or right is None:
            self.robot_status = 'WAITING_FOR_SCAN'
            self.send_command(0.0, 0.0)
            return

        # Target navigation is a simple odometry controller with reactive LiDAR
        # avoidance. No map or global path planning: it can fail in a maze/U-shape.
        if self.target is not None:
            distance = math.hypot(self.target[0] - self.current[0],
                                  self.target[1] - self.current[1])
            if distance <= self.arrival_tolerance:
                self.send_command(0.0, 0.0)
                self.robot_status = 'GOAL_REACHED'
                self.finished = True
                self.target = None
                self.event('ARRIVED')
                return
            if time.monotonic() - self.goal_started > float(self.get_parameter('waypoint_timeout_sec').value):
                self.fail_goal('Direct waypoint controller timed out')
                return
            desired = math.atan2(self.target[1] - self.current[1],
                                 self.target[0] - self.current[0])
            error = self.angle_error(desired, self.yaw)
            if front < self.safe_distance:
                if time.monotonic() > self.avoid_until:
                    self.avoid_turn_direction = 1.0 if left >= right else -1.0
                self.avoid_until = time.monotonic() + 0.8
                self.robot_status = 'AVOIDING_OBSTACLE'
                self.send_command(0.0, self.avoid_turn_direction * self.turn_speed)
            elif time.monotonic() < self.avoid_until:
                self.robot_status = 'CLEARING_OBSTACLE'
                self.send_command(min(self.forward_speed, 0.06),
                                  self.avoid_turn_direction * self.turn_speed * 0.45)
            elif abs(error) > float(self.get_parameter('turn_in_place_error_rad').value):
                self.robot_status = 'TURNING_TO_HOTSPOT'
                self.send_command(0.0, max(-self.turn_speed,
                                            min(self.turn_speed, 1.5 * error)))
            else:
                self.robot_status = 'NAVIGATING_TO_HOTSPOT'
                v = min(self.forward_speed, max(0.035, distance * 0.5))
                self.send_command(v, max(-self.turn_speed, min(self.turn_speed, 1.3 * error)))
            self.get_logger().info(
                f'{self.robot_status} | distance_to_goal={distance:.2f}m | '
                f'front={front:.2f}m | heading_error={error:.2f}rad',
                throttle_duration_sec=1.0)
            return

        if self.pause_for_twin:
            self.robot_status = 'PAUSED_FOR_TWIN'
            self.send_command(0.0, 0.0)
            return
        # Retain V3 baseline exploration behavior.
        if self.turning:
            if front > self.safe_distance + 0.15:
                self.turning = False
            else:
                self.robot_status = 'TURNING'
                self.send_command(0.0, self.turn_direction * self.turn_speed)
                return
        if front < self.safe_distance:
            self.turning = True
            self.turn_direction = 1.0 if left >= right else -1.0
            self.robot_status = 'TURNING'
            self.send_command(0.0, self.turn_direction * self.turn_speed)
        else:
            self.robot_status = 'MOVING'
            self.send_command(self.forward_speed, 0.0)
        self.get_logger().info(
            f'{self.robot_status} | front={front:.2f}m | left={left:.2f}m | '
            f'right={right:.2f}m | travelled={self.total_distance:.2f}m',
            throttle_duration_sec=1.0)

    def stop(self):
        if rclpy.ok():
            self.send_command(0.0, 0.0)


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
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
