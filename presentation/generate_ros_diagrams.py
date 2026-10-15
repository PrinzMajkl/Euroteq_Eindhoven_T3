"""Draw the two rqt_graph-style ROS 2 diagrams for the technical-solution slides.

    python3 presentation/generate_ros_diagrams.py

Writes presentation/assets/ros_architecture_graph.png and presentation/assets/state_sync_graph.png.
Node, topic, action and service names are taken from lab_turtlebot/src/plumetrace (nodes, gateway, relay).
Style follows rqt_graph: nodes are ellipses, topics are boxes; actions and services are amber, the
WebSocket path is navy. Colours match the deck (navy #0B3350, amber #F5B301, light blue #E8F5FA).
"""
import os

import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse, FancyArrowPatch, FancyBboxPatch

NAVY, AMBER, LIGHT, GREY, WHITE = '#0B3350', '#F5B301', '#E8F5FA', '#7A8A99', '#FFFFFF'
TEAL = '#2A9BC0'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')
plt.rcParams['font.family'] = 'DejaVu Sans'


class Graph:
    def __init__(self, w, h, size):
        self.fig, self.ax = plt.subplots(figsize=size)
        self.ax.set_xlim(0, w)
        self.ax.set_ylim(0, h)
        self.ax.set_aspect('equal')
        self.ax.axis('off')
        self.p = {}

    def band(self, y0, y1, label, w):
        self.ax.add_patch(FancyBboxPatch((0.15, y0), w - 0.3, y1 - y0, boxstyle='round,pad=0,rounding_size=0.25',
                                         fc=LIGHT, ec='none', zorder=0))
        self.ax.text(0.4, y1 - 0.22, label, fontsize=9, fontweight='bold', color=TEAL, va='top', zorder=1)

    def node(self, key, x, y, text=None, w=None, fc=NAVY, tc=WHITE):
        text = text or key
        w = w or 0.15 * len(text) + 0.6
        e = Ellipse((x, y), w, 0.78, fc=fc, ec=NAVY, lw=1.2, zorder=3)
        self.ax.add_patch(e)
        self.ax.text(x, y, text, ha='center', va='center', fontsize=8.5, color=tc, fontweight='bold', zorder=4)
        self.p[key] = e

    def box(self, key, x, y, text=None, kind='topic', w=None):
        text = text or key
        w = w or 0.145 * len(text) + 0.5
        fc, ec, tc, ls = {'topic': (WHITE, NAVY, NAVY, '-'), 'action': (AMBER, AMBER, NAVY, '-'),
                          'service': (WHITE, AMBER, NAVY, '--'), 'web': (TEAL, TEAL, WHITE, '-')}[kind]
        b = FancyBboxPatch((x - w / 2, y - 0.27), w, 0.54, boxstyle='round,pad=0,rounding_size=0.08',
                           fc=fc, ec=ec, lw=1.2, ls=ls, zorder=3)
        self.ax.add_patch(b)
        self.ax.text(x, y, text, ha='center', va='center', fontsize=8, color=tc, zorder=4,
                     family='DejaVu Sans Mono' if kind in ('topic', 'service', 'action') else 'DejaVu Sans',
                     fontweight='bold' if kind in ('action', 'web') else 'normal')
        self.p[key] = b

    def edge(self, a, b, color=GREY, rad=0.0, ls='-', lw=1.1):
        self.ax.add_patch(FancyArrowPatch(self.center(a), self.center(b), arrowstyle='-|>', color=color, lw=lw,
                                          ls=ls, mutation_scale=11, patchA=self.p[a], patchB=self.p[b],
                                          shrinkA=1, shrinkB=1, connectionstyle=f'arc3,rad={rad}', zorder=2))

    def center(self, k):
        p = self.p[k]
        if isinstance(p, Ellipse):
            return p.center
        return p.get_x() + p.get_width() / 2, p.get_y() + p.get_height() / 2

    def legend(self, x, y):
        items = [('node', NAVY, 'ellipse'), ('topic', WHITE, 'box'), ('action', AMBER, 'box'),
                 ('service', WHITE, 'dash'), ('WebSocket', TEAL, 'box')]
        for i, (label, fc, shape) in enumerate(items):
            xi = x + i * 1.85
            if shape == 'ellipse':
                self.ax.add_patch(Ellipse((xi, y), 0.5, 0.3, fc=fc, ec=NAVY, lw=1))
            else:
                ec = AMBER if label in ('action', 'service') else (TEAL if label == 'WebSocket' else NAVY)
                self.ax.add_patch(FancyBboxPatch((xi - 0.25, y - 0.14), 0.5, 0.28, boxstyle='round,pad=0,rounding_size=0.05',
                                                 fc=fc, ec=ec, lw=1, ls='--' if shape == 'dash' else '-'))
            self.ax.text(xi + 0.35, y, label, fontsize=8, color=NAVY, va='center')

    def save(self, name):
        path = os.path.join(OUT, name)
        self.fig.savefig(path, dpi=220, bbox_inches='tight', pad_inches=0.15, facecolor=WHITE)
        plt.close(self.fig)
        return path


def architecture():
    W = 12.4
    g = Graph(W, 12.6, (9, 9.2))
    g.band(10.25, 12.3, 'ROBOT  ·  TurtleBot3 Burger', W)
    g.band(6.45, 10.05, 'NAVIGATION  ·  Nav2', W)
    g.band(2.95, 6.25, 'DIGITAL TWIN  ·  PlumeTrace', W)
    g.band(0.1, 2.75, 'WEB', W)

    g.node('turtlebot3_node', 6.2, 11.55)
    g.box('/scan', 1.2, 10.65)
    g.box('/odom', 4.4, 10.65)
    g.box('/cmd_vel', 10.6, 10.65)
    g.node('amcl', 2.9, 9.0)
    g.node('planner_server', 4.9, 7.9)
    g.node('bt_navigator', 7.4, 9.0)
    g.node('controller_server', 10.6, 9.0)
    for t in ('/scan', '/odom'):
        g.edge('turtlebot3_node', t)
    g.edge('/scan', 'amcl')
    g.edge('/odom', 'amcl')
    g.edge('controller_server', '/cmd_vel')
    g.edge('/cmd_vel', 'turtlebot3_node')
    g.edge('bt_navigator', 'controller_server')

    g.box('navigate_to_pose', 7.4, 6.95, kind='action')
    g.box('compute_path_to_pose', 3.7, 6.95, kind='action')
    g.box('clear_costmap', 10.8, 6.95, kind='service')
    g.node('mission_controller', 7.4, 5.4)
    g.node('twin_core', 3.6, 5.4)
    g.node('localization_monitor', 10.4, 4.0)
    g.node('obstacle_detector', 1.9, 3.75)
    g.node('emulated_sensor', 5.9, 3.75)
    g.edge('mission_controller', 'navigate_to_pose', color=AMBER, lw=1.5)
    g.edge('navigate_to_pose', 'bt_navigator', color=AMBER, lw=1.5)
    g.edge('twin_core', 'compute_path_to_pose', color=AMBER, lw=1.5)
    g.edge('compute_path_to_pose', 'planner_server', color=AMBER, lw=1.5)
    g.edge('mission_controller', 'clear_costmap', color=AMBER, lw=1.5, ls='--')
    g.edge('localization_monitor', 'clear_costmap', color=AMBER, lw=1.5, ls='--')
    g.edge('/scan', 'obstacle_detector', rad=0.12)
    g.edge('emulated_sensor', 'twin_core')
    g.edge('twin_core', 'mission_controller')

    g.node('plumetrace_gateway', 6.2, 2.0)
    g.edge('mission_controller', 'plumetrace_gateway', rad=-0.1)
    g.edge('twin_core', 'plumetrace_gateway', rad=0.35)
    g.edge('obstacle_detector', 'plumetrace_gateway', rad=0.1)
    g.box('ws :8765', 2.6, 0.75, kind='web')
    g.box('relay.py :8090  /ws', 6.2, 0.75, kind='web')
    g.box('browser dashboards', 10.0, 0.75, kind='web')
    g.edge('plumetrace_gateway', 'ws :8765', color=TEAL, lw=1.5)
    g.edge('ws :8765', 'relay.py :8090  /ws', color=TEAL, lw=1.5)
    g.edge('relay.py :8090  /ws', 'browser dashboards', color=TEAL, lw=1.5)
    g.legend(1.0, -0.45)
    g.ax.set_ylim(-0.8, 12.6)
    return g.save('ros_architecture_graph.png')


def sync():
    W = 13.2
    g = Graph(W, 10.4, (9, 7.4))
    g.band(7.55, 10.2, 'ROBOT SIDE  ·  edge', W)
    g.band(4.95, 7.35, 'LINK  ·  Wi-Fi', W)
    g.band(0.1, 4.75, 'TWIN SIDE  ·  lab laptop', W)

    g.node('emulated_sensor', 1.75, 8.9)
    g.box('/plume/sample_raw', 4.85, 8.9)
    g.node('edge_buffer', 7.75, 8.9)
    g.box('/edge/sample_out', 10.6, 9.5)
    g.box('/edge/heartbeat · /edge/pose', 10.75, 8.15, w=4.1)
    g.edge('emulated_sensor', '/plume/sample_raw')
    g.edge('/plume/sample_raw', 'edge_buffer')
    g.edge('edge_buffer', '/edge/sample_out')
    g.edge('edge_buffer', '/edge/heartbeat · /edge/pose')

    g.node('link_gate', 10.6, 6.15)
    g.edge('/edge/sample_out', 'link_gate', rad=-0.35)
    g.edge('/edge/heartbeat · /edge/pose', 'link_gate')
    g.box('/edge/ack', 6.4, 6.15)
    g.edge('link_gate', '/edge/ack', color=AMBER, lw=1.5)
    g.edge('/edge/ack', 'edge_buffer', color=AMBER, lw=1.5)

    g.box('/plume/sample', 11.6, 4.0)
    g.box('/twin/heartbeat · /robot/pose', 6.9, 4.0, w=4.3)
    g.edge('link_gate', '/plume/sample')
    g.edge('link_gate', '/twin/heartbeat · /robot/pose')
    g.node('sample_ingest', 11.6, 2.7)
    g.node('sync_monitor', 6.9, 2.7)
    g.edge('/plume/sample', 'sample_ingest')
    g.edge('/twin/heartbeat · /robot/pose', 'sync_monitor')
    g.box('/plume/ack', 9.4, 3.4)
    g.edge('sample_ingest', '/plume/ack', color=AMBER, lw=1.5)
    g.edge('/plume/ack', 'link_gate', color=AMBER, lw=1.5, rad=-0.25)

    g.box('/twin/sync', 4.5, 2.7)
    g.edge('sync_monitor', '/twin/sync')
    g.node('localization_monitor', 2.1, 3.75)
    g.box('/localization/status', 1.95, 2.7, w=2.9)
    g.edge('localization_monitor', '/localization/status')
    g.node('mission_controller', 3.0, 0.9)
    g.node('plumetrace_gateway', 7.2, 0.9)
    g.edge('/twin/sync', 'mission_controller')
    g.edge('/localization/status', 'mission_controller')
    g.edge('/twin/sync', 'plumetrace_gateway')
    g.box('/twin/samples', 11.0, 0.9)
    g.edge('sample_ingest', '/twin/samples')
    g.edge('/twin/samples', 'plumetrace_gateway')
    g.box('WebSocket → relay', 7.2, -0.35, kind='web', w=3.0)
    g.edge('plumetrace_gateway', 'WebSocket → relay', color=TEAL, lw=1.5)
    g.ax.set_ylim(-0.8, 10.4)
    g.ax.text(W - 0.3, -0.35, 'amber = acknowledgement path', fontsize=8, color=NAVY, ha='right', va='center')
    return g.save('state_sync_graph.png')


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    print(architecture())
    print(sync())
