"""The lab arena in Gazebo with a TurtleBot3 Burger (simulation of the real lab setup).

    ros2 launch plumetrace_sim lab_world.launch.py [gui:=true] [x_pose:=0.0] [y_pose:=0.0]
        [static_boards:=true] [headless_rendering:=false]
World: worlds/lab_arena.world (the course's new_world.world, unchanged). With static_boards:=true (default)
a copy with every board fixed to the floor is written to the temp folder and loaded instead, so the robot
cannot push the arena apart; static_boards:=false loads the file as it is.
headless_rendering:=true lets the LiDAR render through EGL when no display is reachable (use with gui:=false).
Robot model, spawner, bridge and robot_state_publisher come from turtlebot3_gazebo. /cmd_vel is TwistStamped,
as on the real robot.
"""
import os
import tempfile

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (AppendEnvironmentVariable, DeclareLaunchArgument, IncludeLaunchDescription,
                            OpaqueFunction)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def gz_server(context):
    sim = get_package_share_directory('plumetrace_sim')
    gz = os.path.join(get_package_share_directory('ros_gz_sim'), 'launch', 'gz_sim.launch.py')
    world = os.path.join(sim, 'worlds', 'lab_arena.world')
    if LaunchConfiguration('static_boards').perform(context).lower() == 'true':
        with open(world) as f:
            text = f.read().replace('<static>false</static>', '<static>true</static>')
        world = os.path.join(tempfile.gettempdir(), f'plumetrace_lab_arena_static_{os.getuid()}.world')
        with open(world, 'w') as f:
            f.write(text)
    flags = '-r -s -v2'
    if LaunchConfiguration('headless_rendering').perform(context).lower() == 'true':
        flags += ' --headless-rendering'
    return [IncludeLaunchDescription(PythonLaunchDescriptionSource(gz),
                                     launch_arguments={'gz_args': f'{flags} {world}',
                                                       'on_exit_shutdown': 'true'}.items())]


def generate_launch_description():
    tb3 = get_package_share_directory('turtlebot3_gazebo')
    gz = os.path.join(get_package_share_directory('ros_gz_sim'), 'launch', 'gz_sim.launch.py')
    return LaunchDescription([
        DeclareLaunchArgument('gui', default_value='true'),
        DeclareLaunchArgument('x_pose', default_value='0.0'),
        DeclareLaunchArgument('y_pose', default_value='0.0'),
        DeclareLaunchArgument('static_boards', default_value='true'),
        DeclareLaunchArgument('headless_rendering', default_value='false'),
        AppendEnvironmentVariable('GZ_SIM_RESOURCE_PATH', os.path.join(tb3, 'models')),
        OpaqueFunction(function=gz_server),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(gz),
                                 launch_arguments={'gz_args': '-g -v2', 'on_exit_shutdown': 'true'}.items(),
                                 condition=IfCondition(LaunchConfiguration('gui'))),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(tb3, 'launch', 'robot_state_publisher.launch.py')),
            launch_arguments={'use_sim_time': 'true'}.items()),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(tb3, 'launch', 'spawn_turtlebot3.launch.py')),
            launch_arguments={'x_pose': LaunchConfiguration('x_pose'), 'y_pose': LaunchConfiguration('y_pose')}.items()),
    ])
