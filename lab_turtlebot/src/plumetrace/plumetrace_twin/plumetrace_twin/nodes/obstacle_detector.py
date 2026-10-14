"""obstacle_detector: LiDAR points not explained by the static map become REAL obstacles.

Per scan: points -> map frame; drop points within 0.10 m of mapped walls and points inside VIRTUAL
footprints (no echo loops); cluster with 0.05 m tolerance; keep clusters with >= 3 points; a track
is confirmed after 3 consecutive scans. Confirmed tracks are published on /obstacles/detections
(ObstacleArray, origin REAL) every scan; the registry expires them 5 s after last seen.
Footprint: the measured (visible) face, extended 0.10 m away from the sensor, as a rotated rectangle.
"""
import math

import numpy as np
import rclpy
import yaml
from geometry_msgs.msg import Point32, Polygon
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.time import Time
from scipy.ndimage import distance_transform_edt
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree
from sensor_msgs.msg import LaserScan
from shapely.geometry import MultiPoint, Point, Polygon as SPolygon
from tf2_ros import Buffer, TransformListener

from plumetrace_msgs.msg import Obstacle, ObstacleArray

from ..simtools import quat_to_yaw


def load_map(path):
    import os
    with open(path) as f:
        meta = yaml.safe_load(f)
    img_path = os.path.join(os.path.dirname(path), meta['image'])
    with open(img_path, 'rb') as f:
        data = f.read()
    # P5 header: magic, width, height, maxval; map_saver adds a '#' comment line
    tok, pos = [], 0
    while len(tok) < 4:
        end = data.index(b'\n', pos)
        line = data[pos:end].split(b'#')[0]
        tok += line.split()
        pos = end + 1
    w, h = int(tok[1]), int(tok[2])
    img = np.frombuffer(data[pos:pos + w * h], dtype=np.uint8).reshape(h, w)[::-1]  # row 0 = y min
    occ = (255 - img.astype(float)) / 255.0 > meta['occupied_thresh']
    return occ, float(meta['resolution']), meta['origin'][:2]


class ObstacleDetector(Node):
    def __init__(self):
        super().__init__('obstacle_detector')
        from ament_index_python.packages import get_package_share_directory
        import os
        default_map = os.path.join(get_package_share_directory('plumetrace_sim'), 'maps', 'arena.yaml')
        self.declare_parameter('map_yaml', default_map)
        self.declare_parameter('wall_margin', 0.10)
        self.declare_parameter('cluster_tol', 0.05)
        self.declare_parameter('min_points', 3)
        self.declare_parameter('confirm_scans', 3)
        self.declare_parameter('assoc_dist', 0.15)
        self.declare_parameter('depth', 0.10)
        self.declare_parameter('height_m', 0.30)
        occ, self.res, self.origin = load_map(self.get_parameter('map_yaml').value)
        self.wall_dist = distance_transform_edt(~occ) * self.res  # metres to the nearest occupied cell centre
        self.wall_dist = np.maximum(self.wall_dist - self.res / 2, 0.0)
        self.margin = float(self.get_parameter('wall_margin').value)
        self.tol = float(self.get_parameter('cluster_tol').value)
        self.min_pts = int(self.get_parameter('min_points').value)
        self.confirm = int(self.get_parameter('confirm_scans').value)
        self.assoc = float(self.get_parameter('assoc_dist').value)
        self.depth = float(self.get_parameter('depth').value)
        self.height = float(self.get_parameter('height_m').value)
        self.virtual = []
        self.tracks = {}  # id -> dict(c, hits, missed, confirmed)
        self.next_id = 1
        self.tf = Buffer()
        self.tfl = TransformListener(self.tf, self)  # lookups below never block
        self.pub = self.create_publisher(ObstacleArray, '/obstacles/detections', 10)
        self.create_subscription(LaserScan, '/scan', self.on_scan, qos_profile_sensor_data)
        self.create_subscription(ObstacleArray, '/twin/obstacles', self.on_registry, 10)

    def on_registry(self, arr):
        self.virtual = [SPolygon([(p.x, p.y) for p in o.footprint.points]).buffer(0.05)
                        for o in arr.obstacles if o.origin == Obstacle.ORIGIN_VIRTUAL and len(o.footprint.points) >= 3]

    def near_wall(self, pts):
        ij = np.floor((pts - np.asarray(self.origin)) / self.res).astype(int)
        h, w = self.wall_dist.shape
        inside = (ij[:, 0] >= 0) & (ij[:, 0] < w) & (ij[:, 1] >= 0) & (ij[:, 1] < h)
        d = np.zeros(len(pts))
        d[inside] = self.wall_dist[ij[inside, 1], ij[inside, 0]]
        return ~inside | (d <= self.margin)

    def on_scan(self, scan):
        # sensor pose at the scan time = latest map -> odom (slow AMCL correction, may lag the scan)
        # composed with odom -> sensor at the scan stamp (odometry, fine-grained)
        try:
            m2o = self.tf.lookup_transform('map', 'odom', Time()).transform
            try:
                o2s = self.tf.lookup_transform('odom', scan.header.frame_id, Time.from_msg(scan.header.stamp)).transform
            except Exception:
                o2s = self.tf.lookup_transform('odom', scan.header.frame_id, Time()).transform
        except Exception:
            return
        ya, yb = quat_to_yaw(m2o.rotation), quat_to_yaw(o2s.rotation)
        ca, sa = math.cos(ya), math.sin(ya)
        sx = m2o.translation.x + ca * o2s.translation.x - sa * o2s.translation.y
        sy = m2o.translation.y + sa * o2s.translation.x + ca * o2s.translation.y
        yaw = ya + yb
        r = np.asarray(scan.ranges, dtype=float)
        a = scan.angle_min + scan.angle_increment * np.arange(len(r))
        ok = np.isfinite(r) & (r > scan.range_min) & (r < scan.range_max)
        r, a = r[ok], a[ok]
        px = sx + r * np.cos(a + yaw)
        py = sy + r * np.sin(a + yaw)
        pts = np.stack([px, py], axis=1)
        if len(pts):
            pts = pts[~self.near_wall(pts)]
        if len(pts) and self.virtual:
            keep = np.array([not any(v.contains(Point(x, y)) for v in self.virtual) for x, y in pts])
            pts = pts[keep]
        clusters = []
        if len(pts) >= self.min_pts:
            tree = cKDTree(pts)
            pairs = tree.query_pairs(self.tol, output_type='ndarray')
            from scipy.sparse import coo_matrix
            n = len(pts)
            g = coo_matrix((np.ones(len(pairs)), (pairs[:, 0], pairs[:, 1])), shape=(n, n)) if len(pairs) else coo_matrix((n, n))
            k, lab = connected_components(g, directed=False)
            for c in range(k):
                cp = pts[lab == c]
                if len(cp) >= self.min_pts:
                    clusters.append(cp)
        self.update_tracks(clusters, (sx, sy), scan.header.stamp)

    def footprint(self, cp, sensor):
        d = cp - np.asarray(sensor)
        d /= np.maximum(np.linalg.norm(d, axis=1, keepdims=True), 1e-6)
        ext = np.vstack([cp, cp + self.depth * d])
        rect = MultiPoint([tuple(p) for p in ext]).minimum_rotated_rectangle
        if rect.geom_type != 'Polygon':
            rect = rect.buffer(0.01)
        return list(rect.exterior.coords)[:-1]

    def update_tracks(self, clusters, sensor, stamp):
        seen = set()
        for cp in clusters:
            c = cp.mean(axis=0)
            best, bd = None, self.assoc
            for tid, tr in self.tracks.items():
                if tid in seen:
                    continue
                dd = math.hypot(*(tr['c'] - c))
                if dd < bd:
                    best, bd = tid, dd
            if best is None:
                best = f'real-{self.next_id}'
                self.next_id += 1
                self.tracks[best] = dict(c=c, hits=0, missed=0, confirmed=False)
            tr = self.tracks[best]
            tr.update(c=c, hits=tr['hits'] + 1, missed=0, fp=self.footprint(cp, sensor), n=len(cp))
            if tr['hits'] >= self.confirm:
                tr['confirmed'] = True
            seen.add(best)
        for tid in list(self.tracks):
            if tid not in seen:
                tr = self.tracks[tid]
                tr['missed'] += 1
                if not tr['confirmed']:
                    tr['hits'] = 0  # needs consecutive scans
                if tr['missed'] > 60:
                    del self.tracks[tid]
        arr = ObstacleArray()
        arr.header.stamp = stamp
        arr.header.frame_id = 'map'
        for tid in seen:
            tr = self.tracks[tid]
            if not tr['confirmed']:
                continue
            o = Obstacle()
            o.id = tid
            o.origin = Obstacle.ORIGIN_REAL
            o.mode = Obstacle.MODE_REROUTE
            o.footprint = Polygon(points=[Point32(x=float(x), y=float(y), z=0.0) for x, y in tr['fp']])
            o.height_m = self.height
            o.confidence = float(min(1.0, tr['hits'] / 10.0))
            o.last_seen = stamp
            arr.obstacles.append(o)
        self.pub.publish(arr)


def main():
    rclpy.init()
    node = ObstacleDetector()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass


if __name__ == '__main__':
    main()
