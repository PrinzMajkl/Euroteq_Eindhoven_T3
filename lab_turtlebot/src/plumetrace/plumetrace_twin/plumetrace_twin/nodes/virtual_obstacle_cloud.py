"""virtual_obstacle_cloud: VIRTUAL obstacles as point clouds on their footprint edge for Nav2.

0.05 m spacing, z = 0.10 m, frame map, 10 Hz (empty clouds too, so sources never time out).
Stamped with the latest map -> odom transform time (AMCL publishes it only with each scan).
REROUTE obstacles -> /virtual_obstacles/cloud (extra costmap observation source: Nav2 plans around).
STOP obstacles    -> /virtual_obstacles/stop_cloud (collision monitor stop polygon: the robot stops),
                     published in the odom frame stamped with the latest odom -> base_footprint time, so the
                     monitor can always transform it (AMCL future-dates map -> odom).
"""
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.time import Time
from tf2_ros import Buffer, TransformListener
from sensor_msgs.msg import PointCloud2, PointField
from std_msgs.msg import Header

from plumetrace_msgs.msg import Obstacle, ObstacleArray

SPACING, Z = 0.05, 0.10


def edge_points(poly, spacing=SPACING):
    pts = []
    n = len(poly)
    for i in range(n):
        a, b = np.asarray(poly[i]), np.asarray(poly[(i + 1) % n])
        L = float(np.linalg.norm(b - a))
        k = max(1, int(np.ceil(L / spacing)))
        for j in range(k):
            pts.append(a + (b - a) * j / k)
    return np.array(pts).reshape(-1, 2)


def make_cloud(header, xy):
    pts = np.zeros((len(xy), 3), dtype=np.float32)
    if len(xy):
        pts[:, :2] = xy
        pts[:, 2] = Z
    msg = PointCloud2()
    msg.header = header
    msg.height = 1
    msg.width = len(pts)
    msg.fields = [PointField(name=n, offset=4 * i, datatype=PointField.FLOAT32, count=1) for i, n in enumerate('xyz')]
    msg.is_bigendian = False
    msg.point_step = 12
    msg.row_step = 12 * len(pts)
    msg.is_dense = True
    msg.data = pts.tobytes()
    return msg


class VirtualObstacleCloud(Node):
    def __init__(self):
        super().__init__('virtual_obstacle_cloud')
        self.reroute = np.zeros((0, 2))
        self.stop = np.zeros((0, 2))
        self.pub = self.create_publisher(PointCloud2, '/virtual_obstacles/cloud', 10)
        self.pub_stop = self.create_publisher(PointCloud2, '/virtual_obstacles/stop_cloud', 10)
        self.create_subscription(ObstacleArray, '/twin/obstacles', self.on_obstacles, 10)
        self.tf = Buffer()
        self.tfl = TransformListener(self.tf, self)
        self.create_timer(0.1, self.tick)

    def on_obstacles(self, arr):
        rr, st = [], []
        for o in arr.obstacles:
            if o.origin != Obstacle.ORIGIN_VIRTUAL or len(o.footprint.points) < 3:
                continue
            e = edge_points([(p.x, p.y) for p in o.footprint.points])
            (st if o.mode == Obstacle.MODE_STOP else rr).append(e)
        self.reroute = np.vstack(rr) if rr else np.zeros((0, 2))
        self.stop = np.vstack(st) if st else np.zeros((0, 2))

    def tick(self):
        h = Header()
        # stamp with the latest map -> odom time, so the odom-frame local costmap can always transform it
        try:
            h.stamp = self.tf.lookup_transform('odom', 'map', Time()).header.stamp
        except Exception:
            h.stamp = self.get_clock().now().to_msg()
        h.frame_id = 'map'
        self.pub.publish(make_cloud(h, self.reroute))
        hs = Header()
        hs.frame_id = 'odom'
        stop = self.stop
        try:
            m2o = self.tf.lookup_transform('odom', 'map', Time())
            hs.stamp = self.tf.lookup_transform('odom', 'base_footprint', Time()).header.stamp
            if len(stop):
                t = m2o.transform
                q = t.rotation
                yaw = np.arctan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))
                c, s = np.cos(yaw), np.sin(yaw)
                stop = stop @ np.array([[c, s], [-s, c]]) + np.array([t.translation.x, t.translation.y])
        except Exception:
            return
        self.pub_stop.publish(make_cloud(hs, stop))


def main():
    rclpy.init()
    node = VirtualObstacleCloud()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass


if __name__ == '__main__':
    main()
