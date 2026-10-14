#!/usr/bin/env python3
"""PlumeTrace digital twin. ROS 2 Jazzy; operational thresholds are PoC-only.

Peak of synthetic field is an observed hotspot PROXY, not inverse dispersion.
Twin requests Nav2 waypoint via /twin_waypoint; safe_navigation owns Nav2 action.

V3 mission logic:
- Robot continues through the pollution plume.
- Twin continuously records the highest observed NH3-N measurement.
- High pollution / alarm does NOT immediately trigger rerouting.
- Robot continues until pollution falls below the clean-water exit threshold.
- Once clean water is reached, Twin pauses baseline navigation.
- Twin sends the highest observed pollution coordinate to Nav2.
- Nav2 reroutes the robot to that observed hotspot.
- Mission stops after arrival is verified.
"""

import json
import math
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class DigitalTwin(Node):

    def __init__(self):
        super().__init__('pollution_digital_twin')

        # ---------------------------------------------------------
        # Parameters
        # ---------------------------------------------------------
        for key, val in {
            'alert_nh3_mg_l': 0.6,
            'low_do_mg_l': 7.0,
            'exit_nh3_mg_l': 0.1,
            'min_alarm_samples': 2,
            'state_period_sec': 5.0,
            'telemetry_timeout_sec': 3.0,
            'sensor_timeout_sec': 6.0,
            'waypoint_timeout_sec': 120.0,
            'arrival_tolerance_m': 0.25
        }.items():
            self.declare_parameter(key, val)

        self.alert = float(
            self.get_parameter('alert_nh3_mg_l').value
        )

        self.low_do = float(
            self.get_parameter('low_do_mg_l').value
        )

        self.exit = float(
            self.get_parameter('exit_nh3_mg_l').value
        )

        self.min_alarm = int(
            self.get_parameter('min_alarm_samples').value
        )

        self.odom_timeout = float(
            self.get_parameter('telemetry_timeout_sec').value
        )

        self.sensor_timeout = float(
            self.get_parameter('sensor_timeout_sec').value
        )

        self.waypoint_timeout = float(
            self.get_parameter('waypoint_timeout_sec').value
        )

        self.arrival_tolerance = float(
            self.get_parameter('arrival_tolerance_m').value
        )

        # ---------------------------------------------------------
        # Mission / Digital Twin state
        # ---------------------------------------------------------
        self.mode = 'BASELINE_ROUTE'
        self.decision = 'CONTINUE'

        self.samples = []
        self.ids = set()

        self.peak = None
        self.gradient = None

        self.robot = {}
        self.env = {}

        self.last_odom = None
        self.last_sensor = None

        self.alarm_streak = 0
        self.plume_seen = False

        self.target = None
        self.target_sent_at = None

        self.final_published = False
        self.mission_event = None

        # ---------------------------------------------------------
        # Publishers
        # ---------------------------------------------------------
        self.pub = self.create_publisher(
            String,
            '/digital_twin_state',
            10
        )

        self.decision_pub = self.create_publisher(
            String,
            '/navigation_decision',
            10
        )

        self.waypoint_pub = self.create_publisher(
            String,
            '/twin_waypoint',
            10
        )

        # ---------------------------------------------------------
        # Subscribers
        # ---------------------------------------------------------
        self.create_subscription(
            String,
            '/robot_status',
            self.on_robot,
            10
        )

        self.create_subscription(
            String,
            '/pollution',
            self.on_sample,
            10
        )

        self.create_subscription(
            String,
            '/twin_mission_event',
            self.on_mission_event,
            10
        )

        # ---------------------------------------------------------
        # Periodic state publisher
        # ---------------------------------------------------------
        self.create_timer(
            float(
                self.get_parameter(
                    'state_period_sec'
                ).value
            ),
            self.tick
        )

        self.get_logger().info(
            'Digital Twin V3 ready: '
            'explore plume -> clean-water exit -> '
            'Nav2 hotspot waypoint -> arrival'
        )

    # =============================================================
    # Publish helper
    # =============================================================

    def emit(self, pub, obj):
        m = String()

        m.data = (
            json.dumps(obj, allow_nan=False)
            if not isinstance(obj, str)
            else obj
        )

        pub.publish(m)

    # =============================================================
    # Robot telemetry
    # =============================================================

    def on_robot(self, msg):
        try:
            self.robot = json.loads(msg.data)
            self.last_odom = time.monotonic()

        except (ValueError, TypeError):
            self.get_logger().warning(
                'Invalid robot telemetry'
            )
            return

    # =============================================================
    # Pollution sensor
    # =============================================================

    def on_sample(self, msg):

        # Mission already finished
        if self.mode in (
            'COMPLETED',
            'FAILED',
            'STOPPED'
        ):
            return

        # ---------------------------------------------------------
        # Parse sample
        # ---------------------------------------------------------
        try:
            s = json.loads(msg.data)

            sid = int(s['sample_id'])
            a = float(s['nh3_n_mg_l'])
            d = float(s['do_mg_l'])

            x = float(s['x'])
            y = float(s['y'])

            if (
                not all(
                    math.isfinite(z)
                    for z in (a, d, x, y)
                )
                or min(a, d) < 0
            ):
                raise ValueError(
                    'invalid values'
                )

        except (
            KeyError,
            ValueError,
            TypeError
        ) as exc:

            self.get_logger().warning(
                f'Invalid sample: {exc}'
            )
            return

        # ---------------------------------------------------------
        # Ignore duplicate samples
        # ---------------------------------------------------------
        if sid in self.ids:
            return

        self.ids.add(sid)

        self.last_sensor = time.monotonic()

        # ---------------------------------------------------------
        # Calculate pollution gradient
        # ---------------------------------------------------------
        if self.samples:

            p = self.samples[-1]

            delta = math.hypot(
                x - p['x'],
                y - p['y']
            )

            if delta > 0.005:

                self.gradient = (
                    a
                    - float(
                        p['nh3_n_mg_l']
                    )
                ) / delta

        # ---------------------------------------------------------
        # Store sample
        # ---------------------------------------------------------
        self.samples.append(s)

        self.env = {
            'nh3_n_mg_l': a,
            'do_mg_l': d,
            'nearest_obstacle_m':
                self.robot.get(
                    'nearest_obstacle_m'
                )
        }

        # ---------------------------------------------------------
        # Keep highest observed pollution point
        #
        # Example:
        # 2 -> 4 -> 6 -> 8.8 -> 3 -> 0
        #
        # self.peak stays at 8.8 and keeps the x/y
        # where that measurement occurred.
        # ---------------------------------------------------------
        if (
            self.peak is None
            or
            a > float(
                self.peak[
                    'nh3_n_mg_l'
                ]
            )
        ):
            self.peak = dict(s)

        # ---------------------------------------------------------
        # Pollution plume has been encountered
        #
        # IMPORTANT:
        # This does NOT cause rerouting.
        # ---------------------------------------------------------
        if a >= self.alert:
            self.plume_seen = True

        # ---------------------------------------------------------
        # Keep existing alarm calculation
        #
        # This is still useful for monitoring/dashboard,
        # but it no longer triggers rerouting.
        # ---------------------------------------------------------
        combined_alarm = (
            a >= self.alert
            and
            d < self.low_do
        )

        self.alarm_streak = (
            self.alarm_streak + 1
            if combined_alarm
            else 0
        )

        self.get_logger().info(
            f'P{sid}: '
            f'NH3-N={a:.3f}, '
            f'DO={d:.2f}, '
            f'alarm={combined_alarm}, '
            f'streak={self.alarm_streak}'
        )

        # =========================================================
        # CHANGED V3 DECISION LOGIC
        # =========================================================
        #
        # OLD:
        #
        # alarm_streak >= min_alarm
        #       -> PAUSE
        #       -> reroute immediately
        #
        # NEW:
        #
        # pollution detected
        #       -> CONTINUE
        #
        # pollution increases
        #       -> CONTINUE + update self.peak
        #
        # pollution decreases
        #       -> CONTINUE
        #
        # NH3 < exit threshold
        #       -> plume has been passed
        #       -> PAUSE
        #       -> reroute to self.peak
        #
        # =========================================================

        if (
            self.mode == 'BASELINE_ROUTE'
            and
            self.plume_seen
            and
            a < self.exit
        ):

            # -----------------------------------------------------
            # Robot has now passed through the plume and reached
            # clean water.
            # -----------------------------------------------------
            self.mode = 'PAUSED_FOR_ANALYSIS'
            self.decision = 'PAUSE'

            self.emit(
                self.decision_pub,
                'PAUSE'
            )

            # -----------------------------------------------------
            # Highest actually observed pollution measurement.
            #
            # This is the hotspot proxy, not a validated physical
            # source estimate.
            # -----------------------------------------------------
            self.target = {
                'x': float(
                    self.peak['x']
                ),
                'y': float(
                    self.peak['y']
                ),
                'frame_id': 'odom',
                'tolerance_m':
                    self.arrival_tolerance,
                'basis':
                    'PEAK_MEASUREMENT_PROXY'
            }

            self.get_logger().warning(
                'PLUME EXIT: clean water reached. '
                f'Observed hotspot NH3-N='
                f'{float(self.peak["nh3_n_mg_l"]):.3f} '
                f'mg/L at '
                f'({float(self.peak["x"]):.3f}, '
                f'{float(self.peak["y"]):.3f}). '
                'Requesting Nav2 waypoint.'
            )

            # -----------------------------------------------------
            # Send hotspot to Safe Navigation / Nav2
            # -----------------------------------------------------
            self.mode = 'ROUTING_TO_HOTSPOT'
            self.decision = 'NAVIGATE'

            self.target_sent_at = (
                time.monotonic()
            )

            self.emit(
                self.waypoint_pub,
                self.target
            )

        # ---------------------------------------------------------
        # Keep state publishing behavior
        # ---------------------------------------------------------
        self.publish_state(
            log=(
                self.mode
                !=
                'BASELINE_ROUTE'
            )
        )

    # =============================================================
    # Mission / Nav2 event
    # =============================================================

    def on_mission_event(self, msg):

        try:
            e = json.loads(msg.data)

        except ValueError:
            return

        self.mission_event = e

        status = e.get('status')

        if (
            self.mode
            ==
            'ROUTING_TO_HOTSPOT'
        ):

            # -----------------------------------------------------
            # Nav2 reports arrival
            # -----------------------------------------------------
            if status == 'ARRIVED':

                target = (
                    self.target
                    or {}
                )

                x = self.robot.get('x')
                y = self.robot.get('y')

                # Verify using robot odometry
                if (
                    x is not None
                    and
                    y is not None
                    and
                    math.hypot(
                        float(x)
                        - target['x'],
                        float(y)
                        - target['y']
                    )
                    <=
                    self.arrival_tolerance
                    + 0.10
                ):

                    self.mode = 'COMPLETED'
                    self.decision = 'STOP'

                    self.get_logger().info(
                        'ARRIVAL VERIFIED '
                        'from Nav2 success + '
                        'robot odometry'
                    )

                else:

                    self.mode = 'FAILED'
                    self.decision = 'STOP'

                    self.get_logger().warning(
                        'Nav2 arrival reported '
                        'but odometry outside '
                        'tolerance'
                    )

                self.emit(
                    self.decision_pub,
                    'STOP'
                )

            # -----------------------------------------------------
            # Nav2 failure
            # -----------------------------------------------------
            elif status in (
                'FAILED',
                'REJECTED',
                'NAV2_UNAVAILABLE',
                'TIMEOUT'
            ):

                self.mode = 'FAILED'
                self.decision = 'STOP'

                self.emit(
                    self.decision_pub,
                    'STOP'
                )

                self.get_logger().warning(
                    f'Route failed: {e}'
                )

        self.publish_state(
            log=True
        )

    # =============================================================
    # Periodic update
    # =============================================================

    def tick(self):

        # ---------------------------------------------------------
        # Nav2 waypoint timeout
        # ---------------------------------------------------------
        if (
            self.mode
            ==
            'ROUTING_TO_HOTSPOT'
            and
            self.target_sent_at
            is not None
        ):

            if (
                time.monotonic()
                -
                self.target_sent_at
                >
                self.waypoint_timeout
            ):

                self.mode = 'FAILED'
                self.decision = 'STOP'

                self.emit(
                    self.decision_pub,
                    'STOP'
                )

                self.mission_event = {
                    'status': 'TIMEOUT',
                    'reason':
                        'waypoint timeout'
                }

        # ---------------------------------------------------------
        # Final state already published
        # ---------------------------------------------------------
        if (
            self.mode in (
                'COMPLETED',
                'FAILED',
                'STOPPED'
            )
            and
            self.final_published
        ):
            return

        self.publish_state(
            log=True
        )

        if self.mode in (
            'COMPLETED',
            'FAILED',
            'STOPPED'
        ):
            self.final_published = True

    # =============================================================
    # Digital Twin state
    #
    # IMPORTANT:
    # Output structure intentionally kept the SAME as original V3
    # because the dashboard already consumes these fields.
    # =============================================================

    def publish_state(
        self,
        log=False
    ):

        t = time.monotonic()

        robot_age = (
            None
            if self.last_odom is None
            else
            t - self.last_odom
        )

        sensor_age = (
            None
            if self.last_sensor is None
            else
            t - self.last_sensor
        )

        peak = self.peak

        state = {

            'timestamp':
                self.get_clock()
                .now()
                .nanoseconds
                / 1e9,

            # -----------------------------------------------------
            # SAME robot structure
            # -----------------------------------------------------
            'robot': {
                k: self.robot.get(k)

                for k in (
                    'x',
                    'y',
                    'yaw',
                    'velocity_mps',
                    'status',
                    'battery_percent',
                    'battery_voltage_v',
                    'battery_source',
                    'battery_is_simulated',
                    'battery_estimated_remaining_min'
                )
            },

            # -----------------------------------------------------
            # SAME environment structure
            # -----------------------------------------------------
            'environment': {
                **self.env,

                'nearest_obstacle_m':
                    self.robot.get(
                        'nearest_obstacle_m'
                    )
            },

            # -----------------------------------------------------
            # SAME pollution structure
            # -----------------------------------------------------
            'pollution': {

                'alarm':
                    self.mode
                    !=
                    'BASELINE_ROUTE'
                    and
                    self.plume_seen,

                'gradient_mg_l_per_m':
                    self.gradient,

                'estimated_source_x':
                    None,

                'estimated_source_y':
                    None,

                'suspected_hotspot_x':
                    peak['x']
                    if peak
                    else None,

                'suspected_hotspot_y':
                    peak['y']
                    if peak
                    else None,

                'sample_count':
                    len(
                        self.samples
                    ),

                'sensor_origin':
                    'SYNTHETIC_POSITION_BASED',

                'measurement_accuracy':
                    'NOT_VALIDATED'
            },

            # -----------------------------------------------------
            # SAME synchronization structure
            # -----------------------------------------------------
            'synchronization': {

                'robot_telemetry_fresh':
                    robot_age
                    is not None
                    and
                    robot_age
                    <=
                    self.odom_timeout,

                'sensor_data_fresh':
                    sensor_age
                    is not None
                    and
                    sensor_age
                    <=
                    self.sensor_timeout,

                'robot_telemetry_age_sec':
                    round(
                        robot_age,
                        2
                    )
                    if
                    robot_age
                    is not None
                    else None,

                'sensor_data_age_sec':
                    round(
                        sensor_age,
                        2
                    )
                    if
                    sensor_age
                    is not None
                    else None,

                'last_sample_id':
                    self.samples[-1][
                        'sample_id'
                    ]
                    if
                    self.samples
                    else None,

                'battery_available':
                    self.robot.get(
                        'battery_percent'
                    )
                    is not None
            },

            # -----------------------------------------------------
            # SAME mission structure
            # -----------------------------------------------------
            'mission': {

                'current_target':
                    self.target,

                'mode':
                    self.mode,

                'decision':
                    self.decision,

                'last_nav2_event':
                    self.mission_event
            }
        }

        self.emit(
            self.pub,
            state
        )

        if log:

            self.get_logger().info(
                'Digital Twin state: '
                +
                json.dumps(
                    state,
                    allow_nan=False
                )
            )


# =============================================================
# Main
# =============================================================

def main():

    rclpy.init()

    node = DigitalTwin()

    try:
        rclpy.spin(node)

    except KeyboardInterrupt:
        pass

    finally:

        node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()