#!/usr/bin/env python3
"""PlumeTrace dashboard gateway: ROS 2 <-> browser.

One command serves the dashboard and bridges it to ROS 2:

  * HTTP  :8080  serves code/dashboard/ (open http://localhost:8080)
  * WS    :8765  streams ROS topics to the browser as JSON and receives
                 requests from the browser

ROS -> browser (every message is wrapped as {"t", "topic", "data"}):
  /digital_twin_state, /robot_status, /pollution, /twin_waypoint,
  /navigation_decision, /twin_mission_event

Browser -> ROS:
  every request          -> /dashboard_request (JSON, for the twin to act on)
  "stop" request         -> also /navigation_decision "STOP" (works today:
                            safe_navigation latches a stop and cancels Nav2)
  "inspect" / "outfall"  -> with --direct, also /twin_waypoint, which
                            safe_navigation sends to Nav2 (bypasses the twin;
                            only for testing until the twin handles requests)

Every message is also logged to code/dashboard/runs/run_<time>.jsonl, so a
live run can be replayed later from the dashboard (Replay -> load file).

Without ROS installed (e.g. on a laptop) it still serves the dashboard, so
Replay mode works anywhere.

Usage:
  python3 gateway_node.py            # live, requests logged for the twin
  python3 gateway_node.py --direct   # inspect/outfall also go to Nav2
Requires: pip install websockets
"""

import argparse
import asyncio
import functools
import http.server
import json
import pathlib
import threading
import time

import websockets

try:
    import rclpy
    from rclpy.node import Node
    from std_msgs.msg import String
    HAVE_ROS = True
except ImportError:
    HAVE_ROS = False

HERE = pathlib.Path(__file__).resolve().parent
WEB_ROOT = HERE / 'dashboard'
RUNS = WEB_ROOT / 'runs'

TOPICS = [
    '/digital_twin_state',
    '/robot_status',
    '/pollution',
    '/twin_waypoint',
    '/navigation_decision',
    '/twin_mission_event',
]

clients = set()
loop = None
t_start = time.time()
log_file = None
log_lock = threading.Lock()


def envelope(topic, raw):
    try:
        data = json.loads(raw)
    except ValueError:
        data = raw
    return {'t': round(time.time() - t_start, 3), 'topic': topic, 'data': data}


def log(msg):
    if log_file is None:
        return
    with log_lock:
        log_file.write(json.dumps(msg) + '\n')
        log_file.flush()


def broadcast(msg):
    """Thread-safe: called from the ROS thread."""
    log(msg)
    text = json.dumps(msg)
    for ws in list(clients):
        asyncio.run_coroutine_threadsafe(safe_send(ws, text), loop)


async def safe_send(ws, text):
    try:
        await ws.send(text)
    except websockets.ConnectionClosed:
        clients.discard(ws)


if HAVE_ROS:
    class Gateway(Node):
        def __init__(self, direct):
            super().__init__('dashboard_gateway')
            self.direct = direct
            for topic in TOPICS:
                self.create_subscription(
                    String, topic,
                    functools.partial(self.on_topic, topic), 10)
            self.request_pub = self.create_publisher(String, '/dashboard_request', 10)
            self.decision_pub = self.create_publisher(String, '/navigation_decision', 10)
            self.waypoint_pub = self.create_publisher(String, '/twin_waypoint', 10)
            self.get_logger().info(
                f'Gateway ready (direct={direct}). Dashboard: http://localhost:8080')

        def on_topic(self, topic, msg):
            broadcast(envelope(topic, msg.data))

        def publish(self, pub, text):
            m = String()
            m.data = text
            pub.publish(m)

        def handle_request(self, req):
            """Returns the list of ROS topics the request was published on."""
            sent = ['/dashboard_request']
            self.publish(self.request_pub, json.dumps(req))
            kind = req.get('type')
            if kind == 'stop':
                self.publish(self.decision_pub, 'STOP')
                sent.append('/navigation_decision')
            elif self.direct and kind in ('inspect', 'outfall'):
                target = {
                    'x': float(req['x']), 'y': float(req['y']),
                    'frame_id': 'odom', 'tolerance_m': 0.25,
                    'basis': 'DASHBOARD_REQUEST',
                }
                self.publish(self.waypoint_pub, json.dumps(target))
                sent.append('/twin_waypoint')
            self.get_logger().info(f'Dashboard request {req.get("id")}: {kind} -> {sent}')
            return sent

node = None


async def handler(ws):
    clients.add(ws)
    await ws.send(json.dumps({
        't': round(time.time() - t_start, 3), 'topic': '/gateway/hello',
        'data': {'ros': HAVE_ROS and node is not None,
                 'direct': bool(node and node.direct)}}))
    try:
        async for raw in ws:
            try:
                req = json.loads(raw)
            except ValueError:
                continue
            if req.get('kind') != 'request':
                continue
            req = req.get('request', {})
            log({'t': round(time.time() - t_start, 3), 'topic': '/dashboard_request',
                 'data': req})
            if node is None:
                ack = {'id': req.get('id'), 'delivered': False, 'topics': [],
                       'reason': 'ROS 2 is not running on this computer'}
            else:
                try:
                    topics = node.handle_request(req)
                    ack = {'id': req.get('id'), 'delivered': True, 'topics': topics}
                except (KeyError, TypeError, ValueError) as exc:
                    ack = {'id': req.get('id'), 'delivered': False, 'topics': [],
                           'reason': f'Invalid request: {exc}'}
            await ws.send(json.dumps({'t': round(time.time() - t_start, 3),
                                      'topic': '/gateway/ack', 'data': ack}))
    finally:
        clients.discard(ws)


def serve_http(port):
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def end_headers(self):
            self.send_header('Cache-Control', 'no-store')
            super().end_headers()

    handler_cls = functools.partial(Quiet, directory=str(WEB_ROOT))
    httpd = http.server.ThreadingHTTPServer(('0.0.0.0', port), handler_cls)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()


async def main(args):
    global loop, node, log_file
    loop = asyncio.get_running_loop()
    serve_http(args.http_port)

    if HAVE_ROS and not args.no_ros:
        RUNS.mkdir(exist_ok=True)
        log_file = open(RUNS / time.strftime('run_%Y%m%d_%H%M%S.jsonl'), 'w')
        rclpy.init()
        node = Gateway(args.direct)
        threading.Thread(target=rclpy.spin, args=(node,), daemon=True).start()
    else:
        print('ROS 2 not available: serving the dashboard for Replay mode only.')

    print(f'Dashboard: http://localhost:{args.http_port}   '
          f'WebSocket: ws://localhost:{args.ws_port}')
    async with websockets.serve(handler, '0.0.0.0', args.ws_port):
        await asyncio.Future()


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--direct', action='store_true',
                   help='also send inspect/outfall requests straight to Nav2')
    p.add_argument('--no-ros', action='store_true', help='serve dashboard only')
    p.add_argument('--http-port', type=int, default=8080)
    p.add_argument('--ws-port', type=int, default=8765)
    try:
        asyncio.run(main(p.parse_args()))
    except KeyboardInterrupt:
        pass
    finally:
        if log_file:
            log_file.close()
        if node is not None:
            node.destroy_node()
            rclpy.shutdown()
