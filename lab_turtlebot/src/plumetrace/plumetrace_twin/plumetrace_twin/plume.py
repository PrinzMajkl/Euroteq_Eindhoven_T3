"""Gaussian-puff plume on a 2D depth-averaged river (pure Python + NumPy).

Coordinates are curvilinear river coordinates: s along the centreline (downstream +),
n across (+ = left bank). Concentrations in mg/L (= g/m^3), times in river seconds.

    C(s, n, t) = C_bg + sum_i m_i e^{-k tau_i} / (4 pi h tau_i sqrt(Dx Dy))
                 * exp(-(s - s_s - u tau_i)^2 / (4 Dx tau_i) - (n - n_s)^2 / (4 Dy tau_i))

The left bank (n = +W/2) reflects by an image source at n = 2 n_bank - n_s; the far bank is
ignored. One puff is released every `release_dt` river seconds while the source is active.
"""
import math

import numpy as np

DEFAULTS = dict(
    Q=10.0,            # m^3/s
    width=20.0,        # m
    depth=1.0,         # m
    Dx=1.0,            # m^2/s
    Dy=0.05,           # m^2/s
    k=0.0,             # 1/s
    release_dt=2.0,    # river s between puffs
    c_bg=0.05,         # mg/L NH3-N background
    do_bg=9.0,         # mg/L DO background
    do_alpha=0.5,      # DO = do_bg - alpha (C - c_bg)
    t_on=-1200.0,      # river s relative to mission start
    t_off=math.inf,
    calib_ds=20.0,     # m downstream on the bank
    calib_c=3.0,       # mg/L total at calib_ds on the bank (5 x the 0.6 alert threshold)
)


class PlumeParams:
    def __init__(self, **kw):
        p = dict(DEFAULTS)
        p.update(kw)
        self.__dict__.update(p)
        self.u = self.Q / (self.width * self.depth)
        self.n_bank = self.width / 2.0


def steady_excess(ds, dn, n_src, p, mdot=1.0, reflect=True):
    """Analytical steady excess concentration for a continuous point source (rate mdot g/s).

    C = mdot / (2 pi h sqrt(Dx Dy)) exp(u ds / (2 Dx)) K0(u / (2 Dx) sqrt(ds^2 + (Dx/Dy) dn^2)),
    with k = 0. dn is measured from the source; the image source is added when reflect=True.
    """
    ds = np.asarray(ds, dtype=float)
    dn = np.asarray(dn, dtype=float)
    a = p.u / (2 * p.Dx)
    pref = mdot / (2 * math.pi * p.depth * math.sqrt(p.Dx * p.Dy))

    def one(dn_):
        r = np.sqrt(ds ** 2 + (p.Dx / p.Dy) * dn_ ** 2)
        r = np.maximum(r, 1e-9)
        return pref * np.exp(a * ds - a * r) * _k0e(a * r)

    c = one(dn)
    if reflect:
        n_rcv = n_src + dn
        n_img = 2 * p.n_bank - n_src
        c = c + one(n_rcv - n_img)
    return c


def _k0e(x):
    """Exponentially scaled K0: K0(x) e^x (scipy)."""
    from scipy.special import k0e
    return k0e(x)


def calibrate_mdot(p, n_src=None):
    """Mass rate (g/s) so the steady total concentration on the bank calib_ds downstream is calib_c."""
    n_src = p.n_bank if n_src is None else n_src
    unit = float(steady_excess(p.calib_ds, p.n_bank - n_src, n_src, p, 1.0))
    return (p.calib_c - p.c_bg) / unit


class PuffPlume:
    """Puff source at (s_src, n_src) with continuous release rate mdot (g/s)."""

    def __init__(self, s_src, n_src, mdot=None, params=None, reach_length=300.0, reflect=True, **kw):
        self.p = params or PlumeParams(**kw)
        self.s_src = float(s_src)
        self.n_src = float(n_src)
        self.reflect = reflect
        self.mdot = calibrate_mdot(self.p, self.n_src) if mdot is None else float(mdot)
        self.reach_length = reach_length
        self.release_t = np.empty(0)
        self.mass = np.empty(0)
        self._next_release = self.p.t_on
        self.t = None

    def add_puff(self, t_release, mass):
        self.release_t = np.append(self.release_t, t_release)
        self.mass = np.append(self.mass, mass)

    def advance_to(self, t):
        """Release every puff due up to river time t and drop puffs that left the reach."""
        p = self.p
        if self._next_release <= t:
            stop = min(t, p.t_off)
            n = int(math.floor((stop - self._next_release) / p.release_dt)) + 1 if stop >= self._next_release else 0
            if n > 0:
                times = self._next_release + p.release_dt * np.arange(n)
                self.release_t = np.concatenate([self.release_t, times])
                self.mass = np.concatenate([self.mass, np.full(n, self.mdot * p.release_dt)])
                self._next_release = times[-1] + p.release_dt
        self.t = t
        tau = t - self.release_t
        centre = self.s_src + p.u * tau
        sig = np.sqrt(2 * p.Dx * np.maximum(tau, 0))
        keep = centre - 8 * sig < self.reach_length + 50.0
        self.release_t = self.release_t[keep]
        self.mass = self.mass[keep]

    def excess(self, s, n, t=None):
        """Excess concentration (mg/L) at points (s, n); n is clamped to the reflecting bank."""
        p = self.p
        t = self.t if t is None else t
        s = np.atleast_1d(np.asarray(s, dtype=float))
        n = np.atleast_1d(np.asarray(n, dtype=float))
        if self.reflect:
            n = np.minimum(n, p.n_bank)
        tau = t - self.release_t
        ok = tau > 1e-9
        tau, m = tau[ok], self.mass[ok]
        if tau.size == 0:
            return np.zeros(np.broadcast(s, n).shape)
        amp = m * np.exp(-p.k * tau) / (4 * math.pi * p.depth * tau * math.sqrt(p.Dx * p.Dy))
        ds = s[..., None] - self.s_src - p.u * tau
        ex = np.exp(-ds ** 2 / (4 * p.Dx * tau))
        dn = n[..., None] - self.n_src
        ey = np.exp(-dn ** 2 / (4 * p.Dy * tau))
        if self.reflect:
            n_img = 2 * p.n_bank - self.n_src
            ey = ey + np.exp(-(n[..., None] - n_img) ** 2 / (4 * p.Dy * tau))
        return np.sum(amp * ex * ey, axis=-1)

    def concentration(self, s, n, t=None):
        return self.p.c_bg + self.excess(s, n, t)

    def dissolved_oxygen(self, c):
        return self.p.do_bg - self.p.do_alpha * (np.asarray(c) - self.p.c_bg)


DRY_MARGIN_M = 5.0  # river m: a probe up to this far inland still dips into the bank water


class ReachPlume:
    """Plume for one active outfall of a ReachFrame, evaluated at river-frame (x, y) points.

    Points just inland of the left bank (within DRY_MARGIN_M) read the bank value; points further
    inland are dry and read the background.
    """

    def __init__(self, frame, outfall_id, strength_factor=1.0, **kw):
        self.frame = frame
        self.outfall = outfall_id
        s_src, n_src = frame.outfall_sn(outfall_id)
        params = PlumeParams(width=frame.width, depth=frame.depth, **kw)
        base = calibrate_mdot(params, n_src)
        self.puffs = PuffPlume(s_src, n_src, base * strength_factor, params, reach_length=frame.length)

    @property
    def params(self):
        return self.puffs.p

    def advance_to(self, t_river):
        self.puffs.advance_to(t_river)

    def at_river_xy(self, xy):
        s, n = self.frame.to_sn(xy)
        c = self.puffs.concentration(s, n)
        dry = n > self.params.n_bank + DRY_MARGIN_M
        return np.where(dry, self.params.c_bg, c)

    def at_arena_xy(self, xy):
        return self.at_river_xy(self.frame.arena_to_river(xy))
