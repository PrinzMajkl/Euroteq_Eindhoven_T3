# EuroTeQ Eindhoven - Track 3 (T3)

Repository for the EuroTeQ project (Eindhoven, T3).

## Repository Structure

```text
Euroteq_Eindhoven_T3/
├── code/                    # Source code, prototypes, scripts, and technical implementation
│   └── README.md
├── presentation/            # Presentation materials, slide outlines, and brainstorming
│   └── slides_brainstorm.md
└── general_information/     # Project brief, requirements, background notes, and references
    └── README.md
```

## Folder Overview

- **[`code/`](code/)**: Contains the project implementation, scripts, tests, and environment configurations.
- **[`presentation/`](presentation/)**: Houses presentation preparation, slide structure, speech notes, and brainstorming.
- **[`general_information/`](general_information/)**: Centralized knowledge base for project scope, mentor/team inputs, requirements, and background research.

## ROS Topics and services
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


- All documentation, code, and presentation materials must be maintained in **English**.
- For detailed agent and workflow rules, see [AGENTS.md](AGENTS.md).
