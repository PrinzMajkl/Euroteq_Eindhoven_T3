"""PlumeTrace mission: lab_nav (Nav2) + robot-side and twin-side nodes + gateway.

Real robot (default): everything runs on the lablaptop; the robot only runs the stock bringup.
Simulation: sim_mission.launch.py includes this launch with use_sim_time:=true next to Gazebo.
    ros2 launch plumetrace_sim lab_mission.launch.py scenario:=A seed:=1 [autostart:=false]
        [strategy:=adaptive|lawnmower] [stamped:=true] [collision_monitor:=false] [map:=<yaml>]
        [gateway:=true] [gateway_host:=localhost] [record:=true] [rviz:=true] [use_sim_time:=false]
        [xy_goal_tolerance:=0.03] [yaw_goal_tolerance:=0.10] [nav:=true] [loc_monitor:=true]
nav:=false leaves out lab_nav (map server, AMCL, Nav2): for a lab_nav that is already running, as tools/run_abc.py
does so that Nav2 and the robot's position on the map stay up between missions.
loc_monitor:=true (default) runs localization_monitor: during the mission it checks the robot's position on the
map and holds the mission to re-localise when the robot is lost.
With autostart:=false (default) the mission waits for:
    ros2 topic pub --once /mission/start std_msgs/msg/Empty "{}"
"""
import os
import time

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


BAG_TOPICS = ['/localization/status', '/plume/sample_raw', '/plume/sample', '/twin/samples', '/twin/posterior', '/twin/next_goal',
              '/twin/planner_info', '/twin/sync', '/twin/obstacles', '/twin/heartbeat', '/twin/command',
              '/twin/registry_cmd', '/mission/state', '/mission/events', '/sensor/trigger', '/edge/heartbeat',
              '/edge/sample_out', '/edge/ack', '/plume/ack', '/robot/pose', '/obstacles/detections',
              '/virtual_obstacles/cloud', '/virtual_obstacles/stop_cloud', '/tf', '/tf_static', '/scan', '/odom',
              '/amcl_pose', '/plan', '/cmd_vel', '/cmd_vel_raw']


def default_map(sim):
    """The map saved by tools/lab_save_map.sh when it exists, else the map generated from the world file."""
    repo = os.environ.get('PLUMETRACE_REPO', '')
    lab = os.path.join(repo, 'lab', 'maps', 'lab_arena.yaml')
    return lab if repo and os.path.isfile(lab) else os.path.join(sim, 'maps', 'arena.yaml')


def generate_launch_description():
    sim = get_package_share_directory('plumetrace_sim')
    sc, seed = LaunchConfiguration('scenario'), LaunchConfiguration('seed')
    wall = {'use_sim_time': ParameterValue(LaunchConfiguration('use_sim_time'), value_type=bool)}
    run_dir = LaunchConfiguration('run_dir')
    default_run = os.path.join(os.environ.get('PLUMETRACE_RUNS', os.path.expanduser('~/plumetrace_runs')),
                               time.strftime('%Y%m%d-%H%M%S'))
    nav_args = ['map', 'stamped', 'collision_monitor', 'x', 'y', 'yaw', 'rviz', 'use_sim_time', 'xy_goal_tolerance',
                'yaw_goal_tolerance']

    def twin(exe, params=None, **kw):
        return Node(package='plumetrace_twin', executable=exe, output='screen',
                    parameters=[wall] + ([params] if params else []), **kw)

    return LaunchDescription([
        DeclareLaunchArgument('scenario', default_value='A'),
        DeclareLaunchArgument('show_true_plume', default_value='false',
                              description='stream the true plume to the dashboard before the mission is done'),
        DeclareLaunchArgument('seed', default_value='1'),
        DeclareLaunchArgument('strategy', default_value='adaptive'),
        DeclareLaunchArgument('mission', default_value='true'),
        DeclareLaunchArgument('autostart', default_value='false'),
        DeclareLaunchArgument('gateway', default_value='true'),
        DeclareLaunchArgument('gateway_host', default_value='localhost',
                              description='0.0.0.0 lets other machines on the network open the city view'),
        DeclareLaunchArgument('record', default_value='true', description='CSV logs + rosbag in run_dir'),
        DeclareLaunchArgument('run_dir', default_value=default_run),
        DeclareLaunchArgument('map', default_value=default_map(sim)),
        DeclareLaunchArgument('stamped', default_value='true'),
        DeclareLaunchArgument('collision_monitor', default_value='false'),
        DeclareLaunchArgument('x', default_value='0.0'),
        DeclareLaunchArgument('y', default_value='0.0'),
        DeclareLaunchArgument('yaw', default_value='0.0'),
        DeclareLaunchArgument('rviz', default_value='false'),
        DeclareLaunchArgument('use_sim_time', default_value='false', description='true only with Gazebo'),
        DeclareLaunchArgument('xy_goal_tolerance', default_value='0.03', description='metres'),
        DeclareLaunchArgument('yaw_goal_tolerance', default_value='0.10', description='radians'),
        DeclareLaunchArgument('nav', default_value='true', description='false: use a lab_nav that is already running'),
        DeclareLaunchArgument('loc_monitor', default_value='true', description='re-localise when lost during the mission'),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(sim, 'launch', 'lab_nav.launch.py')),
            launch_arguments={k: LaunchConfiguration(k) for k in nav_args}.items(),
            condition=IfCondition(LaunchConfiguration('nav'))),
        # robot side (runs here; the probe reads the plume at the robot's localised pose)
        twin('emulated_sensor', {'scenario': sc, 'seed': seed}),
        twin('edge_buffer'),
        twin('link_gate'),
        # twin side
        twin('sample_ingest'),
        twin('sync_monitor'),
        twin('twin_core', {'scenario': sc, 'seed': seed, 'strategy': LaunchConfiguration('strategy')}),
        twin('obstacle_registry'),
        twin('obstacle_detector', {'map_yaml': LaunchConfiguration('map')}),
        twin('virtual_obstacle_cloud'),
        twin('mission_controller', {'scenario': sc, 'autostart': LaunchConfiguration('autostart'), 'mode': 'MIXED'},
             condition=IfCondition(LaunchConfiguration('mission'))),
        twin('localization_monitor', condition=IfCondition(PythonExpression(
            ["'", LaunchConfiguration('loc_monitor'), "' == 'true' and '", LaunchConfiguration('mission'), "' == 'true'"]))),
        twin('run_logger', {'run_dir': run_dir}, condition=IfCondition(LaunchConfiguration('record'))),
        ExecuteProcess(cmd=['ros2', 'bag', 'record', '-o', PythonExpression(["'", run_dir, "' + '/bag'"])] + BAG_TOPICS,
                       output='log', condition=IfCondition(LaunchConfiguration('record'))),
        Node(package='plumetrace_gateway', executable='gateway', output='screen',
             parameters=[wall, {'scenario': sc, 'host': LaunchConfiguration('gateway_host'),
                                          'show_true_plume': LaunchConfiguration('show_true_plume')}],
             condition=IfCondition(LaunchConfiguration('gateway'))),
    ])
