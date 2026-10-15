"""Source estimator: grid Bayesian filter over (outfall, strength) and the next-sample planner.

Hypotheses: outfalls A, B, C x 20 log-spaced strength factors from 0.2 to 5 (uniform prior).
Prediction for a sample at probe point p: C = c_bg + q * E_h(p), with E_h the steady excess of
outfall h at strength 1 (analytical steady solution, k = 0, bank reflection).
Likelihood: Gaussian, sigma = 0.05 * pred + 0.02 mg/L + 10 % model error (0.10 * pred), marginalised
over the probe position uncertainty: a 3 x 3 Gauss-Hermite mixture in (s, n) with
sigma_pos = 1.5 m river (0.015 m arena, the AMCL error measured in A4).
Localised when the top outfall probability >= 0.95.

Planner: score = expected entropy reduction of the outfall marginal (20 noise draws)
/ (straight-line distance + 0.3 m); points sampled within 0.10 m are skipped; the top 3 are
re-checked with Nav2 path lengths when a path function is given; cap 24 samples.
Sweep (the alternative to the adaptive planner): fixed bank stops just upstream and just downstream of every
outfall, visited in order along the bank from the end nearest the robot; no early stop at 95 %.
"""
import math

import numpy as np

from .plume import DRY_MARGIN_M, PlumeParams, calibrate_mdot, steady_excess

LABELS = ('A', 'B', 'C')
N_STRENGTH = 20
STRENGTHS = np.logspace(math.log10(0.2), math.log10(5.0), N_STRENGTH)
LOCALISED_P = 0.95
CAP = 24
SKIP_RADIUS = 0.10
DIST_OFFSET = 0.3
N_DRAWS = 20
POS_SIGMA_RIVER = 1.5
SWEEP_OFFSET = 0.2  # arena metres: sweep stops this far upstream and downstream of every outfall
_GH_X, _GH_W = np.polynomial.hermite_e.hermegauss(3)
_GH_W = _GH_W / _GH_W.sum()


def sigma_of(pred):
    return 0.05 * pred + 0.02 + 0.10 * pred


class SourceEstimator:
    def __init__(self, frame, labels=LABELS, strengths=STRENGTHS, q_m3s=10.0, Q=None, **params):
        self.frame = frame
        self.labels = list(labels)
        self.q = np.asarray(strengths, dtype=float)
        # Q and further plume parameters (c_bg, do_bg) come from the scenario (scenario.plume_params)
        self.p = PlumeParams(width=frame.width, depth=frame.depth, Q=q_m3s if Q is None else Q, **params)
        self.src = [frame.outfall_sn(lab) for lab in self.labels]
        self.mdot = [calibrate_mdot(self.p, n) for _, n in self.src]
        self.log_post = np.zeros((len(self.labels), len(self.q)))
        self.n = 0
        self.history = []

    # --- model -------------------------------------------------------------
    def unit_excess(self, river_xy):
        """E_h(p) for every hypothesis h and river point(s) p -> shape (H, N)."""
        s, n = self.frame.to_sn(np.atleast_2d(river_xy))
        dry = n > self.p.n_bank + DRY_MARGIN_M
        n = np.minimum(n, self.p.n_bank)
        out = np.empty((len(self.labels), len(s)))
        for i, ((ss, ns), m) in enumerate(zip(self.src, self.mdot)):
            out[i] = np.where(dry, 0.0, steady_excess(s - ss, n - ns, ns, self.p, m))
        return out

    def predict(self, river_xy):
        """Predicted concentration, shape (H, Q, N)."""
        e = self.unit_excess(river_xy)
        return self.p.c_bg + self.q[None, :, None] * e[:, None, :]

    @staticmethod
    def loglik(y, pred):
        sig = sigma_of(pred)
        return -0.5 * ((y - pred) / sig) ** 2 - np.log(sig)

    def predict_mix(self, river_xy):
        """Predictions at the 9 Gauss-Hermite probe positions around each point -> (H, Q, N, 9), weights (9,)."""
        s, n = self.frame.to_sn(np.atleast_2d(river_xy))
        ds, dn = np.meshgrid(_GH_X * POS_SIGMA_RIVER, _GH_X * POS_SIGMA_RIVER, indexing='ij')
        w = np.outer(_GH_W, _GH_W).ravel()
        ss = (s[:, None] + ds.ravel()[None, :]).ravel()
        nn = (n[:, None] + dn.ravel()[None, :]).ravel()
        pts = self.frame.from_sn(ss, nn)
        pred = self.predict(pts)  # (H, Q, N*9)
        H, Q = pred.shape[:2]
        return pred.reshape(H, Q, len(s), 9), w

    @classmethod
    def loglik_mix(cls, y, pred_mix, w):
        """log sum_k w_k N(y; pred_k, sigma(pred_k)) over the last axis."""
        ll = cls.loglik(y, pred_mix) + np.log(w)
        m = ll.max(axis=-1, keepdims=True)
        return (m + np.log(np.exp(ll - m).sum(axis=-1, keepdims=True)))[..., 0]

    # --- filter -------------------------------------------------------------
    def update(self, river_xy, value):
        pm, w = self.predict_mix(river_xy)
        self.log_post += self.loglik_mix(value, pm[:, :, 0, :], w)
        self.log_post -= self.log_post.max()
        self.n += 1
        self.history.append((np.asarray(river_xy, dtype=float).ravel()[:2], float(value)))
        return self.marginal()

    def posterior(self):
        w = np.exp(self.log_post - self.log_post.max())
        return w / w.sum()

    def marginal(self):
        return self.posterior().sum(axis=1)

    def map_estimate(self):
        post = self.posterior()
        i, j = np.unravel_index(np.argmax(post), post.shape)
        m = post.sum(axis=1)
        k = int(np.argmax(m))
        jk = int(np.argmax(post[k]))
        return self.labels[k], float(m[k]), float(self.q[jk])

    def localised(self):
        return float(self.marginal().max()) >= LOCALISED_P

    @staticmethod
    def entropy(p):
        p = p[p > 1e-15]
        return float(-(p * np.log(p)).sum())

    # --- planner ------------------------------------------------------------
    def expected_entropy_reduction(self, river_pts, rng):
        """For each candidate river point: H(now) - E[H(after one sample)], 20 noise draws."""
        post = self.posterior()
        h0 = self.entropy(post.sum(axis=1))
        flat = post.ravel()
        pm, w = self.predict_mix(river_pts)  # (H, Q, N, 9)
        H, Q, N = pm.shape[:3]
        cells = rng.choice(H * Q, size=N_DRAWS, p=flat)
        z = rng.standard_normal(N_DRAWS)
        comp = rng.choice(len(w), size=N_DRAWS, p=w)
        gains = np.empty(N)
        lp = self.log_post
        for k in range(N):
            pk = pm[:, :, k, :]
            truth = pk.reshape(H * Q, -1)[cells, comp]
            ys = truth + sigma_of(truth) * z
            hs = 0.0
            for y in ys:
                l2 = lp + self.loglik_mix(y, pk, w)
                pw = np.exp(l2 - l2.max())
                m = pw.sum(axis=1)
                hs += self.entropy(m / m.sum())
            gains[k] = h0 - hs / N_DRAWS
        return gains

    def plan(self, robot_xy, candidates, sampled_xy, rng, path_len=None, top=3):
        """candidates: list of dicts with 'waypoint' (arena), 'edge' (arena). Returns (index, info) or None."""
        robot_xy = np.asarray(robot_xy, dtype=float)
        ok = []
        for i, c in enumerate(candidates):
            if any(np.hypot(*(c['waypoint'] - np.asarray(s))) < SKIP_RADIUS for s in sampled_xy):
                continue
            ok.append(i)
        if not ok:
            return None
        river = self.frame.arena_to_river(np.array([candidates[i]['edge'] for i in ok]))
        gain = self.expected_entropy_reduction(river, rng)
        dist = np.array([np.hypot(*(candidates[i]['waypoint'] - robot_xy)) for i in ok])
        score = gain / (dist + DIST_OFFSET)
        order = np.argsort(-score)
        chosen, info = None, {}
        if path_len is not None:
            best = -np.inf
            for r in order[:top]:
                c = candidates[ok[r]]
                L = path_len(c)
                if L is None:
                    continue
                sc = gain[r] / (L + DIST_OFFSET)
                if sc > best:
                    best, chosen = sc, r
                    info = dict(path_len=L)
            if chosen is None:
                chosen = order[0]
        else:
            chosen = order[0]
        info.update(gain=float(gain[chosen]), dist=float(dist[chosen]), score=float(score[chosen]))
        return ok[chosen], info


def sweep_order(frame, candidates, robot_xy):
    """Sweep: for every outfall the bank stop nearest SWEEP_OFFSET upstream and the one nearest SWEEP_OFFSET
    downstream of it, ordered along the bank starting from the end nearest robot_xy. Returns candidate indices."""
    along = np.array([c['along'] for c in candidates])
    edges = np.array([c['edge'] for c in candidates])
    picked = set()
    for o in frame.outfalls:
        xy = frame.river_to_arena(np.asarray(o['river_xy'], dtype=float))
        a0 = along[int(np.argmin(np.hypot(*(edges - xy).T)))]
        for a in (a0 - SWEEP_OFFSET, a0 + SWEEP_OFFSET):
            picked.add(int(np.argmin(np.abs(along - a))))
    order = sorted(picked, key=lambda i: along[i])
    robot_xy = np.asarray(robot_xy, dtype=float)
    if np.hypot(*(candidates[order[-1]]['waypoint'] - robot_xy)) < np.hypot(*(candidates[order[0]]['waypoint'] - robot_xy)):
        order.reverse()
    return order
