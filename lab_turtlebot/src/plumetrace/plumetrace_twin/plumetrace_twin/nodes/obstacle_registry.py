"""obstacle_registry: the single list of obstacles for every view and for Nav2.

Inputs:  /twin/registry_cmd (std_msgs/String JSON {op: add|remove, id, kind, mode, footprint (arena), height_m})
             -> VIRTUAL obstacles and no-go zones; removed only by an operator.
         /obstacles/detections (ObstacleArray, origin REAL) from obstacle_detector
             -> REAL obstacles; expire 5 s after last seen. Never re-published as VIRTUAL.
Output:  /twin/obstacles (ObstacleArray, frame map) on change and at 1 Hz;
         /twin/obstacle_markers (MarkerArray) with the same content for RViz / Foxglove.
"""
import json

import rclpy
from geometry_msgs.msg import Point, Point32, Polygon
from rclpy.node import Node
from std_msgs.msg import ColorRGBA, String
from visualization_msgs.msg import Marker, MarkerArray

from plumetrace_msgs.msg import Obstacle, ObstacleArray


class ObstacleRegistry(Node):
    def __init__(self):
        super().__init__('obstacle_registry')
        self.declare_parameter('expire_s', 5.0)
        self.expire_s = float(self.get_parameter('expire_s').value)
        self.virtual = {}
        self.real = {}  # id -> (Obstacle, last_seen_s)
        self.pub = self.create_publisher(ObstacleArray, '/twin/obstacles', 10)
        self.markers = self.create_publisher(MarkerArray, '/twin/obstacle_markers', 10)  # RViz / Foxglove
        self.create_subscription(String, '/twin/registry_cmd', self.on_cmd, 20)
        self.create_subscription(ObstacleArray, '/obstacles/detections', self.on_detections, 10)
        self.create_timer(1.0, self.publish)
        self.create_timer(0.2, self.expire)

    def now_s(self):
        return self.get_clock().now().nanoseconds * 1e-9

    def on_cmd(self, msg):
        try:
            op = json.loads(msg.data)
        except ValueError:
            return
        if op.get('op') == 'remove':
            hit = self.virtual.pop(op.get('id'), None)
            self.get_logger().info(f"remove {op.get('id')}: {'ok' if hit else 'unknown id'}")
        elif op.get('op') == 'add':
            o = Obstacle()
            o.id = str(op['id'])
            o.origin = Obstacle.ORIGIN_VIRTUAL
            o.mode = Obstacle.MODE_STOP if op.get('mode') == 'STOP' else Obstacle.MODE_REROUTE
            o.footprint = Polygon(points=[Point32(x=float(x), y=float(y), z=0.0) for x, y in op['footprint']])
            o.height_m = float(op.get('height_m', 0.3))
            o.confidence = 1.0
            o.last_seen = self.get_clock().now().to_msg()
            self.virtual[o.id] = o
            self.get_logger().info(f"add {op.get('kind')} {o.id} mode {op.get('mode')}")
        self.publish()

    def on_detections(self, arr):
        now = self.now_s()
        changed = False
        for o in arr.obstacles:
            if o.origin != Obstacle.ORIGIN_REAL:
                continue
            changed |= o.id not in self.real
            self.real[o.id] = (o, now)
        if changed:
            self.publish()

    def expire(self):
        now = self.now_s()
        gone = [k for k, (_, t) in self.real.items() if now - t > self.expire_s]
        for k in gone:
            del self.real[k]
        if gone:
            self.publish()

    def publish(self):
        arr = ObstacleArray()
        arr.header.stamp = self.get_clock().now().to_msg()
        arr.header.frame_id = 'map'
        arr.obstacles = [o for o, _ in self.real.values()] + list(self.virtual.values())
        self.pub.publish(arr)
        self.publish_markers(arr)

    def publish_markers(self, arr):
        """Footprint outlines for RViz / Foxglove: REAL grey, VIRTUAL REROUTE orange, STOP red, no-go dotted red."""
        ma = MarkerArray()
        clear = Marker()
        clear.action = Marker.DELETEALL
        ma.markers.append(clear)
        for i, o in enumerate(arr.obstacles):
            m = Marker()
            m.header = arr.header
            m.ns = 'obstacles'
            m.id = i
            m.type = Marker.LINE_STRIP
            m.scale.x = 0.015
            pts = [Point(x=p.x, y=p.y, z=0.02) for p in o.footprint.points]
            m.points = pts + pts[:1]
            if o.origin == Obstacle.ORIGIN_REAL:
                m.color = ColorRGBA(r=0.4, g=0.4, b=0.4, a=1.0)
            elif o.id.startswith('nogo'):
                m.color = ColorRGBA(r=0.9, g=0.2, b=0.2, a=0.7)
            elif o.mode == Obstacle.MODE_STOP:
                m.color = ColorRGBA(r=0.9, g=0.1, b=0.1, a=1.0)
            else:
                m.color = ColorRGBA(r=1.0, g=0.6, b=0.0, a=1.0)
            ma.markers.append(m)
            t = Marker()
            t.header = arr.header
            t.ns = 'obstacle_labels'
            t.id = i
            t.type = Marker.TEXT_VIEW_FACING
            t.scale.z = 0.05
            t.pose.position.x = sum(p.x for p in pts) / max(len(pts), 1)
            t.pose.position.y = sum(p.y for p in pts) / max(len(pts), 1)
            t.pose.position.z = 0.15
            t.color = m.color
            t.text = f"{o.id} ({'REAL' if o.origin == Obstacle.ORIGIN_REAL else ('STOP' if o.mode == Obstacle.MODE_STOP else 'REROUTE')})"
            ma.markers.append(t)
        self.markers.publish(ma)


def main():
    rclpy.init()
    node = ObstacleRegistry()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass


if __name__ == '__main__':
    main()
