"""plumetrace_gateway: WebSocket server (ws://localhost:8765) between the twin and the city view.

Streams pose (10 Hz), plume_points (2 Hz, ~1000 water points from the twin's posterior),
sample, posterior, alert (on change), obstacles (on change + 1 Hz), sync (2 Hz), mission (1 Hz).
Accepts only the allow-listed commands (protocol.COMMANDS); abort / return_home go to
/twin/command, no-go zones and virtual obstacles to the obstacle registry (/twin/registry_cmd).
The browser never touches DDS. Later the server dials out to a cloud relay instead.
"""
import asyncio
import json
import threading
import time

import numpy as np
import rclpy
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.time import Time
from std_msgs.msg import String
from tf2_ros import Buffer, TransformListener

from plumetrace_msgs.msg import MissionState, ObstacleArray, PlumeSample, Posterior, SyncStatus
from plumetrace_twin.estimator import SourceEstimator
from plumetrace_twin.reach import ReachFrame
from plumetrace_twin.scenario import load_scenario
from plumetrace_twin.simtools import quat_to_yaw

from . import protocol as P


class Gateway(Node):
    def __init__(self):
        super().__init__('plumetrace_gateway')
        self.declare_parameter('host', 'localhost')
        self.declare_parameter('port', 8765)
        self.declare_parameter('scenario', 'A')
        self.frame = ReachFrame.load()
        sc = load_scenario(self.get_parameter('scenario').value)
        self.time_factor = float(sc['time_factor'])
        self.est = SourceEstimator(self.frame, q_m3s=float(sc['flow']['q_m3s']))
        self._plume_grid()
        self.ws_clients = set()
        self.loop = None
        self.post = None
        self.post_msg = None
        self.obstacles = None
        self.mission = None
        self.n_cmd = 0
        self.tf = Buffer()
        self.tfl = TransformListener(self.tf, self)
        self.cmd_pub = self.create_publisher(String, '/twin/command', 10)
        self.reg_pub = self.create_publisher(String, '/twin/registry_cmd', 10)
        self.create_subscription(PlumeSample, '/twin/samples', self.on_sample, 50)
        self.create_subscription(Posterior, '/twin/posterior', self.on_post, 10)
        self.create_subscription(ObstacleArray, '/twin/obstacles', self.on_obstacles, 10)
        self.create_subscription(SyncStatus, '/twin/sync', lambda m: self.send(P.sync_msg(m)), 10)
        self.create_subscription(MissionState, '/mission/state', self.on_mission, 10)
        self.create_timer(0.1, self.send_pose)
        self.create_timer(0.5, self.send_plume)
        self.create_timer(1.0, self.send_periodic)
        self.thread = threading.Thread(target=self._serve, daemon=True)
        self.thread.start()

    # --- plume field --------------------------------------------------------
    def _plume_grid(self):
        fr = self.frame
        ss = np.linspace(2.0, fr.length - 2.0, 32)
        nn = np.linspace(-fr.width / 2 + 0.3, fr.width / 2 - 0.05, 31)
        S, N = np.meshgrid(ss, nn)
        river = fr.from_sn(S.ravel(), N.ravel())
        lat, lon, _ = fr.river_to_geodetic(river)
        self.grid_ll = np.stack([lat, lon], axis=1)
        self.grid_unit = self.est.unit_excess(river)  # (3, 992)

    def plume_values(self):
        if self.post is None:
            p = np.full(3, 1 / 3)
            q = 1.0
        else:
            p = np.array(self.post.probabilities, dtype=float)
            q = float(self.post.map_strength)
        return self.est.p.c_bg + q * (p[:, None] * self.grid_unit).sum(axis=0)

    # --- ROS inputs -------------------------------------------------------------
    def on_sample(self, s):
        m = P.sample_msg(self.frame, s)
        self.send(m)
        if m['nh3_n_mg_l'] > P.ALERT_MG_L:
            self.send(P.alert_msg(m, self.post_msg))

    def on_post(self, p):
        self.post = p
        self.post_msg = P.posterior_msg(p)
        self.send(self.post_msg)

    def on_obstacles(self, arr):
        changed = self.obstacles is None or [o.id for o in arr.obstacles] != [o.id for o in self.obstacles.obstacles]
        self.obstacles = arr
        if changed:
            self.send(P.obstacles_msg(self.frame, arr, self.now_s()))

    def on_mission(self, ms):
        self.mission = ms
        self.send(P.mission_msg(ms, self.time_factor, self.frame.name))

    def now_s(self):
        return self.get_clock().now().nanoseconds * 1e-9

    # --- periodic ---------------------------------------------------------------
    def send_pose(self):
        try:
            tr = self.tf.lookup_transform('map', 'base_footprint', Time())
        except Exception:
            return
        t = tr.transform
        self.send(P.pose_msg(self.frame, self.now_s(), t.translation.x, t.translation.y, quat_to_yaw(t.rotation)))

    def send_plume(self):
        if not self.ws_clients:
            return
        v = self.plume_values()
        pts = [[P.r6(a), P.r6(b), round(float(c), 4)] for (a, b), c in zip(self.grid_ll, v)]
        self.send(dict(type='plume_points', t=round(self.now_s(), 3), units='mg/L NH3-N', points=pts))

    def send_periodic(self):
        if self.obstacles is not None:
            self.send(P.obstacles_msg(self.frame, self.obstacles, self.now_s()))
        if self.mission is None:
            self.send(dict(type='mission', mode='SIM', state='IDLE', samples_taken=0, scenario='',
                           time_factor=self.time_factor, reach=self.frame.name))

    # --- websocket --------------------------------------------------------------
    def send(self, msg):
        if self.loop is None or not self.ws_clients:
            return
        data = json.dumps(msg)
        self.loop.call_soon_threadsafe(self._broadcast, data)

    def _broadcast(self, data):
        for ws in list(self.ws_clients):
            asyncio.ensure_future(self._safe_send(ws, data))

    async def _safe_send(self, ws, data):
        try:
            await ws.send(data)
        except Exception:
            self.ws_clients.discard(ws)

    def hello(self):
        fr = self.frame
        return dict(type='hello', reach=fr.name, reach_id=fr.reach_id, time_factor=self.time_factor,
                    origin=dict(lat=fr.lat0, lon=fr.lon0, h=fr.h0), scale=fr.scale,
                    commands=list(P.COMMANDS), alert_mg_l=P.ALERT_MG_L)

    async def handler(self, ws):
        self.ws_clients.add(ws)
        await ws.send(json.dumps(self.hello()))
        if self.post_msg:
            await ws.send(json.dumps(self.post_msg))
        try:
            async for raw in ws:
                try:
                    msg = json.loads(raw)
                except ValueError:
                    msg = None
                ok, reason = P.validate_command(msg)
                cmd = msg.get('command') if isinstance(msg, dict) else None
                if ok:
                    self.n_cmd += 1
                    if cmd in ('abort', 'return_home'):
                        self.cmd_pub.publish(String(data=json.dumps(dict(type=cmd, source='web'))))
                    else:
                        op = P.command_to_registry(self.frame, msg, self.n_cmd)
                        op['source'] = 'web'
                        self.reg_pub.publish(String(data=json.dumps(op)))
                        reason = op.get('id', '')
                    self.get_logger().info(f'command {cmd} accepted {reason}')
                else:
                    self.get_logger().warn(f'command rejected: {reason}')
                await ws.send(json.dumps(dict(type='ack', command=cmd if isinstance(cmd, str) else None,
                                              ok=ok, detail=reason, t=round(time.time(), 3))))
        except Exception:
            pass
        finally:
            self.ws_clients.discard(ws)

    def _serve(self):
        try:
            from websockets.asyncio.server import serve
        except ImportError:  # websockets < 13 (Ubuntu 24.04 ships 10.4)
            from websockets import serve

        async def main():
            self.loop = asyncio.get_running_loop()
            async with serve(self.handler, self.get_parameter('host').value, self.get_parameter('port').value,
                             max_size=2 ** 22):
                await asyncio.Future()
        asyncio.run(main())


def main():
    rclpy.init()
    node = Gateway()
    ex = MultiThreadedExecutor(num_threads=2)
    ex.add_node(node)
    try:
        ex.spin()
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass


if __name__ == '__main__':
    main()
