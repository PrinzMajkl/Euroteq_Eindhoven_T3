"""Map the lab arena with the TurtleBot3 (slam_toolbox; wall-clock time unless use_sim_time:=true).

Put the robot on the start mark (arena 0, 0, facing +x: 1.0 m from the wall behind it and 1.0 m from the
wall on its left), then:
    ros2 launch plumetrace_sim lab_map.launch.py [rviz:=true] [use_sim_time:=false]
Drive it round the arena with the teleop keyboard, then save with tools/lab_save_map.sh.
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    sim = get_package_share_directory('plumetrace_sim')
    slam = get_package_share_directory('slam_toolbox')
    return LaunchDescription([
        DeclareLaunchArgument('rviz', default_value='true'),
        DeclareLaunchArgument('use_sim_time', default_value='false', description='true only with Gazebo'),
        DeclareLaunchArgument('slam_params_file', default_value=os.path.join(sim, 'params', 'slam_lab.yaml')),
        # slam_toolbox's own launch brings its node up (it is a lifecycle node on Jazzy)
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(slam, 'launch', 'online_async_launch.py')),
            launch_arguments={'use_sim_time': LaunchConfiguration('use_sim_time'),
                              'slam_params_file': LaunchConfiguration('slam_params_file')}.items()),
        Node(package='rviz2', executable='rviz2', output='log',
             parameters=[{'use_sim_time': ParameterValue(LaunchConfiguration('use_sim_time'), value_type=bool)}],
             arguments=['-d', os.path.join(sim, 'rviz', 'plumetrace.rviz')],
             condition=IfCondition(LaunchConfiguration('rviz'))),
    ])
