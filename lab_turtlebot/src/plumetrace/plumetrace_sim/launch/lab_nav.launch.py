"""Navigation for the TurtleBot3 (ROS 2 Jazzy): map server + AMCL + keepout filter + Nav2 (+ collision monitor).

Real robot (default, wall-clock time): the robot runs the stock bringup
(ros2 launch turtlebot3_bringup robot.launch.py) and this launch runs on the lablaptop.
Simulation: the same launch with use_sim_time:=true next to lab_world.launch.py (sim_mission.launch.py does it).
    ros2 launch plumetrace_sim lab_nav.launch.py [map:=<yaml>] [stamped:=true] [collision_monitor:=false]
        [x:=0.0 y:=0.0 yaw:=0.0] [rviz:=true] [use_sim_time:=false]
        [xy_goal_tolerance:=0.03] [yaw_goal_tolerance:=0.10]
The robot must stand at the start pose (x, y, yaw in the arena frame; the start mark is 0, 0, 0) when this
starts. Write x, y and yaw with a decimal point (0.0, not 0): AMCL wants floating-point values.
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, TimerAction
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from nav2_common.launch import RewrittenYaml


def default_map(sim):
    """The map saved by tools/lab_save_map.sh when it exists, else the map generated from the world file."""
    repo = os.environ.get('PLUMETRACE_REPO', '')
    lab = os.path.join(repo, 'lab', 'maps', 'lab_arena.yaml')
    return lab if repo and os.path.isfile(lab) else os.path.join(sim, 'maps', 'arena.yaml')


def generate_launch_description():
    sim = get_package_share_directory('plumetrace_sim')
    cm = LaunchConfiguration('collision_monitor')
    x, y, yaw = LaunchConfiguration('x'), LaunchConfiguration('y'), LaunchConfiguration('yaw')
    # /cmd_vel as TwistStamped (stock Jazzy bringup) or Twist: one switch for every Nav2 publisher.
    # use_sim_time: one switch for every node (false = real robot, true = Gazebo's /clock).
    params = RewrittenYaml(source_file=LaunchConfiguration('params_file'),
                           param_rewrites={'enable_stamped_cmd_vel': LaunchConfiguration('stamped'),
                                           'use_sim_time': LaunchConfiguration('use_sim_time'),
                                           'xy_goal_tolerance': LaunchConfiguration('xy_goal_tolerance'),
                                           'yaw_goal_tolerance': LaunchConfiguration('yaw_goal_tolerance')},
                           convert_types=True)
    wall = {'use_sim_time': ParameterValue(LaunchConfiguration('use_sim_time'), value_type=bool)}
    nav_nodes = ['controller_server', 'smoother_server', 'planner_server', 'behavior_server', 'bt_navigator']
    # controller output goes through the collision monitor when it is enabled
    ctrl_out = PythonExpression(["'cmd_vel_raw' if '", cm, "' == 'true' else 'cmd_vel'"])

    return LaunchDescription([
        DeclareLaunchArgument('map', default_value=default_map(sim)),
        DeclareLaunchArgument('params_file', default_value=os.path.join(sim, 'params', 'nav2_burger.yaml')),
        DeclareLaunchArgument('mask', default_value=os.path.join(sim, 'maps', 'keepout_mask.yaml')),
        DeclareLaunchArgument('stamped', default_value='true', description='/cmd_vel is TwistStamped'),
        DeclareLaunchArgument('collision_monitor', default_value='false'),
        DeclareLaunchArgument('x', default_value='0.0'),
        DeclareLaunchArgument('y', default_value='0.0'),
        DeclareLaunchArgument('yaw', default_value='0.0'),
        DeclareLaunchArgument('rviz', default_value='false'),
        DeclareLaunchArgument('use_sim_time', default_value='false', description='true only with Gazebo'),
        DeclareLaunchArgument('xy_goal_tolerance', default_value='0.03', description='metres'),
        DeclareLaunchArgument('yaw_goal_tolerance', default_value='0.10', description='radians'),

        # localisation
        Node(package='nav2_map_server', executable='map_server', name='map_server', output='screen',
             parameters=[params, {'yaml_filename': LaunchConfiguration('map')}]),
        Node(package='nav2_amcl', executable='amcl', name='amcl', output='screen',
             parameters=[params, {'initial_pose': {'x': x, 'y': y, 'z': 0.0, 'yaw': yaw}}]),
        TimerAction(period=2.0, actions=[
            Node(package='nav2_lifecycle_manager', executable='lifecycle_manager',
                 name='lifecycle_manager_localization', output='screen',
                 parameters=[wall, {'autostart': True, 'node_names': ['map_server', 'amcl']}])]),

        # keepout filter (the taped river is a no-go zone)
        Node(package='nav2_map_server', executable='map_server', name='filter_mask_server', output='log',
             parameters=[params, {'yaml_filename': LaunchConfiguration('mask')}]),
        Node(package='nav2_map_server', executable='map_server', name='soft_mask_server', output='log',
             parameters=[params, {'yaml_filename': os.path.join(sim, 'maps', 'keepout_soft.yaml')}]),
        Node(package='nav2_map_server', executable='costmap_filter_info_server', name='costmap_filter_info_server',
             output='log', parameters=[params]),
        TimerAction(period=2.0, actions=[
            Node(package='nav2_lifecycle_manager', executable='lifecycle_manager', name='lifecycle_manager_filters',
                 output='screen', parameters=[wall, {'autostart': True,
                                                     'node_names': ['filter_mask_server', 'soft_mask_server',
                                                                    'costmap_filter_info_server']}])]),

        # navigation
        TimerAction(period=3.0, actions=[
            Node(package='nav2_controller', executable='controller_server', output='screen', parameters=[params],
                 remappings=[('cmd_vel', ctrl_out)]),
            Node(package='nav2_smoother', executable='smoother_server', name='smoother_server', output='log',
                 parameters=[params]),
            Node(package='nav2_planner', executable='planner_server', name='planner_server', output='screen',
                 parameters=[params]),
            Node(package='nav2_behaviors', executable='behavior_server', name='behavior_server', output='log',
                 parameters=[params], remappings=[('cmd_vel', ctrl_out)]),
            Node(package='nav2_bt_navigator', executable='bt_navigator', name='bt_navigator', output='screen',
                 parameters=[params]),
        ]),
        # collision monitor: controller -> cmd_vel_raw -> collision_monitor -> cmd_vel
        Node(package='nav2_collision_monitor', executable='collision_monitor', name='collision_monitor',
             output='screen', parameters=[params], condition=IfCondition(cm)),
        TimerAction(period=4.0, actions=[
            Node(package='nav2_lifecycle_manager', executable='lifecycle_manager', name='lifecycle_manager_monitor',
                 output='log', parameters=[wall, {'autostart': True, 'node_names': ['collision_monitor']}],
                 condition=IfCondition(cm))]),
        TimerAction(period=6.0, actions=[
            Node(package='nav2_lifecycle_manager', executable='lifecycle_manager', name='lifecycle_manager_navigation',
                 output='screen', parameters=[wall, {'autostart': True, 'node_names': nav_nodes}])]),

        Node(package='rviz2', executable='rviz2', output='log', parameters=[wall],
             arguments=['-d', os.path.join(sim, 'rviz', 'plumetrace.rviz')],
             condition=IfCondition(LaunchConfiguration('rviz'))),
    ])
