from setuptools import setup

package_name = 'plumetrace_twin'

# Node name -> module:function. Every node lives in plumetrace_twin/nodes/.
NODES = {
    'emulated_sensor': 'plumetrace_twin.nodes.emulated_sensor:main',
    'edge_buffer': 'plumetrace_twin.nodes.edge_buffer:main',
    'link_gate': 'plumetrace_twin.nodes.link_gate:main',
    'sample_ingest': 'plumetrace_twin.nodes.sample_ingest:main',
    'sync_monitor': 'plumetrace_twin.nodes.sync_monitor:main',
    'twin_core': 'plumetrace_twin.nodes.twin_core:main',
    'mission_controller': 'plumetrace_twin.nodes.mission_controller:main',
    'obstacle_registry': 'plumetrace_twin.nodes.obstacle_registry:main',
    'obstacle_detector': 'plumetrace_twin.nodes.obstacle_detector:main',
    'virtual_obstacle_cloud': 'plumetrace_twin.nodes.virtual_obstacle_cloud:main',
    'run_logger': 'plumetrace_twin.nodes.run_logger:main',
}

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name, package_name + '.nodes'],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='anoushk',
    maintainer_email='anoushkger@gmail.com',
    description='PlumeTrace twin core',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={'console_scripts': [f'{k} = {v}' for k, v in NODES.items()]},
)
