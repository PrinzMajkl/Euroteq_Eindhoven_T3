"""Scenario files: config/scenarios/<name>.yaml."""
import os

import yaml

from .reach import repo_dir


def scenario_path(name):
    if os.path.isfile(name):
        return name
    return os.path.join(repo_dir(), 'config', 'scenarios', f'{name}.yaml')


def load_scenario(name, seed=None):
    with open(scenario_path(name)) as f:
        sc = yaml.safe_load(f)
    if seed is not None:
        sc['noise_seed'] = int(seed)
    sc.setdefault('time_factor', 10.0)
    sc.setdefault('strength_factor', 1.0)
    sc.setdefault('source_on_s', -1200.0)
    return sc


def plume_params(sc):
    """Plume parameters a scenario fixes: flow Q and, when the file has a `background` block, the
    NH3-N and DO background (written from the GKD stations by tools/update_scenarios.py)."""
    p = dict(Q=float(sc['flow']['q_m3s']))
    bg = sc.get('background') or {}
    if 'nh3_n_mg_l' in bg:
        p['c_bg'] = float(bg['nh3_n_mg_l'])
    if 'do_mg_l' in bg:
        p['do_bg'] = float(bg['do_mg_l'])
    return p


def make_plume(frame, sc):
    from .plume import ReachPlume
    return ReachPlume(frame, sc['active_outfall'], strength_factor=float(sc['strength_factor']),
                      t_on=float(sc['source_on_s']), **plume_params(sc))


def make_estimator(frame, sc, noise_rel=0.05, noise_abs=0.01):
    """noise_rel, noise_abs: the emulated sensor's noise settings (sensor_model.SENSOR_DEFAULTS)."""
    from .estimator import SourceEstimator
    return SourceEstimator(frame, noise_rel=noise_rel, noise_abs=noise_abs, **plume_params(sc))
