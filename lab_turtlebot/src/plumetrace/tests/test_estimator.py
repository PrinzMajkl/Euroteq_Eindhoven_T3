"""Estimator and planner on the offline simulator (3 scenarios x 5 seeds)."""
import json
import os

import numpy as np
import pytest

from plumetrace_twin.estimator import SourceEstimator, STRENGTHS
from plumetrace_twin.offline_sim import run_mission
from plumetrace_twin.reach import ReachFrame
from plumetrace_twin.scenario import load_scenario


@pytest.fixture(scope='module')
def frame():
    return ReachFrame.load()


def test_grid_and_prior(frame):
    est = SourceEstimator(frame)
    assert len(STRENGTHS) == 20 and abs(STRENGTHS[0] - 0.2) < 1e-12 and abs(STRENGTHS[-1] - 5.0) < 1e-9
    assert np.allclose(est.marginal(), 1 / 3)


def test_prediction_matches_calibration(frame):
    est = SourceEstimator(frame)
    s, n = frame.outfall_sn('A')
    p = frame.from_sn([s + 20.0], [n])
    pred = est.predict(p)[:, :, 0]
    j1 = int(np.argmin(np.abs(est.q - 1.0)))
    assert abs(pred[0, j1] / est.q[j1] - (3.0 - 0.05) / 1.0 - 0.05 / est.q[j1]) < 0.15


def test_offline_15_runs(frame):
    results = []
    for sc in 'ABC':
        for seed in range(1, 6):
            r = run_mission(frame, load_scenario(sc, seed), seed)
            results.append(r)
            print(f"{sc} seed {seed}: localised={r['localised']} label={r['label']} samples={r['samples']} "
                  f"time={r['time_s']} s max_update={r['max_update_s'] * 1000:.1f} ms")
    good = sum(r['correct'] and r['samples'] <= 15 for r in results)
    worst = max(r['max_update_s'] for r in results)
    print(f'correct and <= 15 samples: {good}/15; worst update {worst * 1000:.1f} ms')
    out = os.path.join(os.environ['PLUMETRACE_REPO'], 'docs', 'a6_offline_results.json')
    with open(out, 'w') as f:
        json.dump([{k: v for k, v in r.items() if k != 'rows'} for r in results], f, indent=1)
    assert good >= 13
    assert worst <= 1.0
