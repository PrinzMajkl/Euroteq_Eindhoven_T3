"""How well a laser scan fits the map at a given pose (numpy and scipy only, no ROS).

Used by tools/localize.py to accept or reject AMCL's answer after global localisation: AMCL reports the
covariance of its best particle cluster only, so a confident but wrong cluster (for example a mirrored
pose in a near-symmetric room) would look fine on covariance alone. At a clearly wrong pose most beam
endpoints land in free space, away from any wall or board. The lab arena is a near-symmetric rectangle, though:
the pose turned 180 deg about the arena centre (the "mirrored" pose) still fits about 0.8 against 1.0 at the
true pose, because most beams hit the outer walls. So the fit at the pose is always compared with the fit at
its mirrored twin; only the inner boards tell them apart.
"""
import math

import numpy as np
from scipy.ndimage import distance_transform_edt

OCCUPIED = 65  # nav_msgs/OccupancyGrid value from which a cell counts as an obstacle (map_server default 0.65)


class DistanceField:
    """Distance (m) from every map cell to the nearest occupied cell."""

    def __init__(self, data, width, height, resolution, origin_x, origin_y):
        grid = np.asarray(data, dtype=np.int16).reshape(height, width)  # row 0 = lowest y, as in OccupancyGrid
        occupied = grid >= OCCUPIED
        if not occupied.any():
            raise ValueError('map has no occupied cells')
        self.dist = distance_transform_edt(~occupied) * resolution
        self.res = float(resolution)
        self.ox = float(origin_x)
        self.oy = float(origin_y)
        self.h, self.w = grid.shape
        # centre of the outer walls: middle of the occupied cells' extent; 1st/99th percentiles so that a few stray
        # cells in a SLAM map (things seen through gaps between the boards) do not move it
        rows, cols = np.nonzero(occupied)
        c0, c1 = np.percentile(cols, [1, 99])
        r0, r1 = np.percentile(rows, [1, 99])
        self.centre = (self.ox + (c0 + c1 + 1) * 0.5 * self.res, self.oy + (r0 + r1 + 1) * 0.5 * self.res)

    def lookup(self, xy):
        """Distance at map points (N x 2); points outside the map get +inf."""
        col = np.floor((xy[:, 0] - self.ox) / self.res).astype(int)
        row = np.floor((xy[:, 1] - self.oy) / self.res).astype(int)
        inside = (col >= 0) & (col < self.w) & (row >= 0) & (row < self.h)
        out = np.full(len(xy), np.inf)
        out[inside] = self.dist[row[inside], col[inside]]
        return out


def scan_endpoints(ranges, angle_min, angle_increment, sensor_x, sensor_y, sensor_yaw, range_min, range_max):
    """Beam endpoints in the map frame for a sensor at (x, y, yaw); invalid beams are dropped."""
    r = np.asarray(ranges, dtype=float)
    a = angle_min + angle_increment * np.arange(len(r))
    ok = np.isfinite(r) & (r > max(range_min, 0.05)) & (r < range_max)
    r, a = r[ok], a[ok] + sensor_yaw
    return np.column_stack([sensor_x + r * np.cos(a), sensor_y + r * np.sin(a)])


def fit_score(field, endpoints, tol=0.08):
    """Fraction of endpoints within `tol` metres of a mapped obstacle (0 when there are too few beams)."""
    if len(endpoints) < 20:
        return 0.0
    return float(np.mean(field.lookup(endpoints) <= tol))


def mirror_pose(x, y, yaw, centre):
    """The pose turned 180 deg about `centre`: the one a rectangular room cannot tell apart from (x, y, yaw)."""
    cx, cy = centre
    return 2 * cx - x, 2 * cy - y, math.atan2(math.sin(yaw + math.pi), math.cos(yaw + math.pi))


def judge(fit, fit_mirror, min_fit, margin=0.08):
    """'ok' (pose fits, clearly better than its mirror), 'mirrored' (the mirror fits clearly better) or 'unsure'."""
    if fit >= min_fit and fit >= fit_mirror + margin:
        return 'ok'
    if fit_mirror >= min_fit and fit_mirror >= fit + margin:
        return 'mirrored'
    return 'unsure'
