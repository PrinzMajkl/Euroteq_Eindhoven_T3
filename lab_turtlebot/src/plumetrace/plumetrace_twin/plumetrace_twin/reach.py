"""Reach geometry and the one coordinate chain used by every component.

The arena frame is the Nav2 map frame: the world frame of worlds/lab_arena.world, origin on the start mark.

arena (m, map frame) -> river (m, x east / y north at the reach origin, i.e. local ENU)
-> WGS84 via pymap3d.enu2geodetic.

    p_river = s * R(theta) * p_arena + t

The river is also described in curvilinear coordinates (s_along, n_across) along the
centreline polyline stored in config/reach_frame.yaml; n > 0 is the left (north) bank side.
"""
import os

import numpy as np
import yaml


def repo_dir():
    env = os.environ.get('PLUMETRACE_REPO')
    if env:
        return env
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))


def default_frame_path():
    return os.path.join(repo_dir(), 'config', 'reach_frame.yaml')


class ReachFrame:
    def __init__(self, cfg):
        self.cfg = cfg
        o = cfg['origin']
        self.lat0, self.lon0, self.h0 = float(o['lat']), float(o['lon']), float(o['h'])
        tr = cfg['transform']
        self.scale = float(tr['scale'])
        self.theta = float(tr['theta_rad'])
        self.t = np.array(tr['t'], dtype=float)
        c, s = np.cos(self.theta), np.sin(self.theta)
        self.R = np.array([[c, -s], [s, c]])
        self.reach_id = cfg['reach_id']
        self.name = cfg.get('name', self.reach_id)
        self.width = float(cfg['width_m'])
        self.depth = float(cfg['depth_m'])
        cl = np.array(cfg['centreline'], dtype=float)
        self.cl = cl
        seg = np.diff(cl, axis=0)
        self.seg_len = np.hypot(seg[:, 0], seg[:, 1])
        self.cl_s = np.concatenate([[0.0], np.cumsum(self.seg_len)])
        self.seg_dir = seg / self.seg_len[:, None]
        self.left_bank = np.array(cfg['left_bank'], dtype=float)
        self.outfalls = cfg['outfalls']
        self.stations = cfg['stations']
        self.arena = cfg['arena']
        self.sampling = cfg['sampling_points']

    @classmethod
    def load(cls, path=None):
        with open(path or default_frame_path()) as f:
            return cls(yaml.safe_load(f))

    # ---- arena <-> river -------------------------------------------------
    def arena_to_river(self, p):
        p = np.asarray(p, dtype=float)
        return self.scale * (p @ self.R.T) + self.t

    def river_to_arena(self, p):
        p = np.asarray(p, dtype=float)
        return ((p - self.t) / self.scale) @ self.R

    def arena_yaw_to_river(self, yaw):
        return yaw + self.theta

    # ---- river (ENU) <-> WGS84 -------------------------------------------
    def river_to_geodetic(self, p, up=0.0):
        import pymap3d
        p = np.asarray(p, dtype=float)
        lat, lon, h = pymap3d.enu2geodetic(p[..., 0], p[..., 1], up, self.lat0, self.lon0, self.h0)
        return np.asarray(lat), np.asarray(lon), np.asarray(h)

    def geodetic_to_river(self, lat, lon, h=None):
        import pymap3d
        if h is None:
            h = self.h0
        e, n, u = pymap3d.geodetic2enu(lat, lon, h, self.lat0, self.lon0, self.h0)
        return np.stack([np.asarray(e), np.asarray(n)], axis=-1)

    def arena_to_geodetic(self, p):
        return self.river_to_geodetic(self.arena_to_river(p))

    # ---- curvilinear (s along centreline, n across, + = left bank) -------
    def to_sn(self, p):
        """Project river-frame points onto the centreline polyline."""
        p = np.atleast_2d(np.asarray(p, dtype=float))
        a = self.cl[:-1]
        d = p[:, None, :] - a[None, :, :]
        tproj = np.einsum('nkj,kj->nk', d, self.seg_dir)
        tproj = np.clip(tproj, 0.0, self.seg_len[None, :])
        foot = a[None, :, :] + tproj[..., None] * self.seg_dir[None, :, :]
        dist2 = np.sum((p[:, None, :] - foot) ** 2, axis=2)
        k = np.argmin(dist2, axis=1)
        idx = np.arange(len(p))
        s = self.cl_s[k] + tproj[idx, k]
        dvec = p - foot[idx, k]
        dirk = self.seg_dir[k]
        cross = dirk[:, 0] * dvec[:, 1] - dirk[:, 1] * dvec[:, 0]
        n = np.sign(cross) * np.sqrt(dist2[idx, k])
        return s, n

    def from_sn(self, s, n):
        s = np.atleast_1d(np.asarray(s, dtype=float))
        n = np.atleast_1d(np.asarray(n, dtype=float))
        k = np.clip(np.searchsorted(self.cl_s, s, side='right') - 1, 0, len(self.seg_len) - 1)
        base = self.cl[k] + (s - self.cl_s[k])[:, None] * self.seg_dir[k]
        normal = np.stack([-self.seg_dir[k, 1], self.seg_dir[k, 0]], axis=1)
        return base + n[:, None] * normal

    @property
    def length(self):
        return float(self.cl_s[-1])

    # ---- convenience -----------------------------------------------------
    def outfall_sn(self, oid):
        o = next(o for o in self.outfalls if o['id'] == oid)
        s, n = self.to_sn([o['river_xy']])
        return float(s[0]), float(n[0])

    def water_polygon_arena(self):
        from shapely.geometry import Polygon
        return Polygon(self.river_to_arena(np.array(self.cfg['water_ring_river'])))

    def bank_waypoint(self, along, standoff=0.13):
        """Left-bank edge point `along` arena metres down the flow from the reach origin, the waypoint
        `standoff` m inland of it and the yaw that faces the water (all in the arena frame)."""
        fy = float(self.arena.get('flow_yaw', 0.0))
        c, s = np.cos(self.theta + fy), np.sin(self.theta + fy)
        lb = self.left_bank @ np.array([[c, -s], [s, c]])  # flow-aligned frame, river metres
        rx = self.scale * along
        h = 0.5
        ry = np.interp(rx, lb[:, 0], lb[:, 1])
        slope = (np.interp(rx + h, lb[:, 0], lb[:, 1]) - np.interp(rx - h, lb[:, 0], lb[:, 1])) / (2 * h)
        c, s = np.cos(fy), np.sin(fy)
        Rf = np.array([[c, -s], [s, c]])
        edge = Rf @ (np.array([rx, ry]) / self.scale) + np.array(self.arena.get('reach_origin', [0.0, 1.0]))
        tang = np.array([1.0, slope]) / np.hypot(1.0, slope)
        nrm = Rf @ np.array([-tang[1], tang[0]])
        return edge, edge + standoff * nrm, float(np.arctan2(-nrm[1], -nrm[0]))

    def sampling_points(self):
        """List of dicts: along (arena metres down the flow), edge (arena), waypoint (arena), yaw (rad)."""
        return [dict(along=float(p['along']), edge=np.array(p['edge']), waypoint=np.array(p['waypoint']),
                     yaw=float(p['yaw'])) for p in self.sampling]
