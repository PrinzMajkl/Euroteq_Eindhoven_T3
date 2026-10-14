"""Plume engine."""
import math

import numpy as np
import pytest

from plumetrace_twin.plume import PlumeParams, PuffPlume, calibrate_mdot, steady_excess


@pytest.mark.parametrize('tau', [20.0, 100.0, 500.0])
@pytest.mark.parametrize('reflect', [False, True])
def test_single_puff_conserves_mass(tau, reflect):
    p = PlumeParams()
    m = 100.0
    n_src = p.n_bank if reflect else 0.0
    pl = PuffPlume(50.0, n_src, mdot=0.0, params=p, reach_length=1e9, reflect=reflect)
    pl.add_puff(0.0, m)
    sx, sy = math.sqrt(2 * p.Dx * tau), math.sqrt(2 * p.Dy * tau)
    sc = 50.0 + p.u * tau
    s = np.linspace(sc - 8 * sx, sc + 8 * sx, 801)
    n_hi = p.n_bank if reflect else n_src + 8 * sy
    n = np.linspace(n_src - 8 * sy, n_hi, 801)
    S, N = np.meshgrid(s, n)
    c = pl.excess(S, N, t=tau)
    mass = np.trapz(np.trapz(c * p.depth, s, axis=1), n)
    err = abs(mass - m) / m
    print(f'tau={tau} reflect={reflect}: mass {mass:.4f} g, error {err * 100:.4f} %')
    assert err < 0.01


@pytest.mark.parametrize('t_now', [0.0, 0.7, 1.3])
def test_steady_source_matches_analytical(t_now):
    p = PlumeParams()
    mdot = calibrate_mdot(p)
    pl = PuffPlume(60.0, p.n_bank, mdot=mdot, params=p, reach_length=1e9)
    pl.advance_to(t_now)
    for d in (20.0, 50.0, 100.0):
        num = float(pl.excess(60.0 + d, p.n_bank)[0])
        ana = float(steady_excess(d, 0.0, p.n_bank, p, mdot))
        err = abs(num - ana) / ana
        print(f't={t_now} d={d:5.1f} m: puffs {num:.4f}, analytical {ana:.4f} mg/L, error {err * 100:.2e} %')
        assert err < 0.05


def test_calibration_and_do():
    p = PlumeParams()
    mdot = calibrate_mdot(p)
    pl = PuffPlume(60.0, p.n_bank, mdot=mdot, params=p, reach_length=1e9)
    pl.advance_to(0.0)
    c20 = float(pl.concentration(80.0, p.n_bank)[0])
    print(f'mdot {mdot:.4f} g/s, bank C at 20 m: {c20:.3f} mg/L')
    assert abs(c20 - 3.0) < 0.15
    assert abs(float(pl.dissolved_oxygen(c20)) - (9.0 - 0.5 * (c20 - 0.05))) < 1e-9
    # upstream of the source the plume is at background
    assert float(pl.concentration(40.0, p.n_bank)[0]) < 0.051


def test_reach_plume_uses_frame():
    import os
    from plumetrace_twin.reach import ReachFrame
    from plumetrace_twin.plume import ReachPlume
    fr = ReachFrame.load(os.path.join(os.environ['PLUMETRACE_REPO'], 'config', 'reach_frame.yaml'))
    rp = ReachPlume(fr, 'B')
    rp.advance_to(0.0)
    sp = fr.sampling_points()
    c = rp.at_arena_xy(np.array([q['edge'] for q in sp]))
    xs = np.array([q['along'] for q in sp])     # arena metres down the flow
    assert np.all(c[xs < 1.35] < 0.06)          # upstream of B (1.4 m down the flow)
    assert c[np.argmin(np.abs(xs - 1.62))] > 1.0  # ~22 m downstream of B
