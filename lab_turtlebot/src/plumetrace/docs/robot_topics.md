# Robot topics and services (stock TurtleBot3 bringup)

What the TurtleBot3 Burger offers on `ROS_DOMAIN_ID=32` with only `ros2 launch turtlebot3_bringup robot.launch.py`
running (recorded on the lablaptop, before any PlumeTrace node was started). Everything else in the system
(Nav2, AMCL, the twin, the gateway) runs on the lablaptop and builds on these topics.

```text
test@2IRR10-NB26:~/Documents/team3e$ ros2 topic list
/battery_state
/cmd_vel
/imu
/joint_states
/magnetic_field
/odom
/parameter_events
/robot_description
/rosout
/scan
/sensor_state
/tf
/tf_static
test@2IRR10-NB26:~/Documents/team3e$ ros2 service list
/diff_drive_controller/describe_parameters
/diff_drive_controller/get_parameter_types
/diff_drive_controller/get_parameters
/diff_drive_controller/get_type_description
/diff_drive_controller/list_parameters
/diff_drive_controller/set_parameters
/diff_drive_controller/set_parameters_atomically
/ld08_driver/describe_parameters
/ld08_driver/get_parameter_types
/ld08_driver/get_parameters
/ld08_driver/get_type_description
/ld08_driver/list_parameters
/ld08_driver/set_parameters
/ld08_driver/set_parameters_atomically
/motor_power
/reset
/reset_odometry
/robot_state_publisher/describe_parameters
/robot_state_publisher/get_parameter_types
/robot_state_publisher/get_parameters
/robot_state_publisher/get_type_description
/robot_state_publisher/list_parameters
/robot_state_publisher/set_parameters
/robot_state_publisher/set_parameters_atomically
/sound
/turtlebot3_node/describe_parameters
/turtlebot3_node/get_parameter_types
/turtlebot3_node/get_parameters
/turtlebot3_node/get_type_description
/turtlebot3_node/list_parameters
/turtlebot3_node/set_parameters
/turtlebot3_node/set_parameters_atomically
```
