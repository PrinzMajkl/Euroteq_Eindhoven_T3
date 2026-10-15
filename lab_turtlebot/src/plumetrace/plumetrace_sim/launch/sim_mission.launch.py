"""PlumeTrace mission in the simulated lab arena: Gazebo (lab_world) + the same lab_mission as on the real robot.

    ros2 launch plumetrace_sim sim_mission.launch.py scenario:=B seed:=1 [strategy:=adaptive|sweep] [autostart:=true] [gui:=true]
        [rviz:=true] [headless_rendering:=false] [gateway_host:=localhost] [record:=true] [mission:=true]
Only two things differ from the real robot: Gazebo stands in for the robot bringup, and every node uses
Gazebo's clock (use_sim_time:=true). The parameter file, the nodes and the maps are the same. The map is always
the one generated from the world file (maps/arena.yaml), never a map saved in the real lab.
"""
import os
import time

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    sim = get_package_share_directory('plumetrace_sim')
    world_args = ['gui', 'static_boards', 'headless_rendering']
    mission_args = ['scenario', 'seed', 'strategy', 'mission', 'autostart', 'gateway', 'gateway_host', 'record',
                    'rviz', 'collision_monitor', 'run_dir', 'xy_goal_tolerance', 'yaw_goal_tolerance']
    defaults = dict(gui='true', static_boards='true', headless_rendering='false', scenario='B', seed='1',
                    strategy='adaptive', mission='true', autostart='true', gateway='true',
                    gateway_host='localhost', record='true', rviz='true', collision_monitor='false',
                    xy_goal_tolerance='0.03', yaw_goal_tolerance='0.10')
    defaults['run_dir'] = os.path.join(os.environ.get('PLUMETRACE_RUNS', os.path.expanduser('~/plumetrace_runs')),
                                       time.strftime('%Y%m%d-%H%M%S') + '-sim')
    fixed = {'use_sim_time': 'true', 'stamped': 'true', 'map': os.path.join(sim, 'maps', 'arena.yaml'),
             'x': '0.0', 'y': '0.0', 'yaw': '0.0'}
    return LaunchDescription(
        [DeclareLaunchArgument(k, default_value=v) for k, v in defaults.items()] + [
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(os.path.join(sim, 'launch', 'lab_world.launch.py')),
                launch_arguments={k: LaunchConfiguration(k) for k in world_args}.items()),
            # Nav2 and the twin start once Gazebo publishes /clock, /scan and the odom transform
            TimerAction(period=8.0, actions=[IncludeLaunchDescription(
                PythonLaunchDescriptionSource(os.path.join(sim, 'launch', 'lab_mission.launch.py')),
                launch_arguments=dict({k: LaunchConfiguration(k) for k in mission_args}, **fixed).items())]),
        ])
