"""Emulated NH3-N probe: first-order lag, multiplicative + additive Gaussian noise, dwell averaging.

Fixed defaults: 1 Hz readings; noise 5 % multiplicative + 0.01 mg/L additive; lag 2 s; dwell 3 s;
reported value = mean of the 3 dwell readings. Probe point = robot position + 0.13 m along its heading.
"""
import math

import numpy as np

QC_MOVED = 1        # robot moved more than 0.01 m during the dwell
QC_POSE_STALE = 2   # localisation older than 0.5 s at the end of the dwell
QC_OFF_BANK = 4     # probe point more than 0.05 m (arena) from the water edge
QC_REPLAY = 8       # reserved: sample was re-sent by the edge buffer

PROBE_OFFSET = 0.13


def probe_point(x, y, yaw, offset=PROBE_OFFSET):
    return np.array([x + offset * math.cos(yaw), y + offset * math.sin(yaw)])


class SensorModel:
    def __init__(self, rng, tau=2.0, noise_rel=0.05, noise_abs=0.01, initial=None):
        self.rng = rng
        self.tau = tau
        self.noise_rel = noise_rel
        self.noise_abs = noise_abs
        self.state = initial

    def step(self, dt, c_true):
        """Advance the lag by dt (simulation seconds) towards the true concentration."""
        if self.state is None:
            self.state = float(c_true)
            return self.state
        a = 1.0 - math.exp(-dt / self.tau)
        self.state += a * (float(c_true) - self.state)
        return self.state

    def read(self):
        v = self.state * (1.0 + self.noise_rel * self.rng.standard_normal()) + self.noise_abs * self.rng.standard_normal()
        return max(0.0, float(v))
