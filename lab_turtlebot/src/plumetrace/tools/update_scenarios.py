#!/usr/bin/env python3
"""Write real flow and background values from the GKD stations into config/scenarios/{A,B,C}.yaml.

A scenario file still defines a run completely, so runs stay reproducible
and need no network: this tool is run by hand when the values should be refreshed.
  flow       : median 15-min discharge of the last `--days` days at the gauge
  background : median NH4-N and dissolved oxygen of the last `--years` years at the chemistry station
    python3 tools/update_scenarios.py [--days 7] [--years 3]
"""
import argparse
import os
import statistics

from plumetrace_twin import fetchers
from plumetrace_twin.reach import ReachFrame, repo_dir

TEMPLATE = """# PlumeTrace scenario: active outfall {o} (operator's secret dice roll; here fixed per file).
# Flow and background are real values, written by tools/update_scenarios.py; the outfall and its strength are synthetic.
scenario: {o}
reach_id: {reach}
flow:
  source: gkd            # {flow_station}, 15-min discharge, www.gkd.bayern.de (CC BY 4.0)
  window: {t0} / {t1}
  q_m3s: {q}            # median of {nq} values (min {qmin}, max {qmax})
background:
  source: gkd            # {wq_station}, grab samples {b0} to {b1}
  nh3_n_mg_l: {nh}       # median NH4-N of {nnh} samples (90th percentile {nh90})
  do_mg_l: {do}          # median dissolved oxygen of {ndo} samples
edm_event_id: SYNTHETIC-EVENT   # no open overflow feed in Bavaria
active_outfall: {o}
strength_factor: 1.0     # x the calibrated default (3.0 mg/L on the bank 20 m downstream)
source_on_s: -1200.0     # river seconds relative to mission start
noise_seed: 1            # overridden by the seed launch argument (seeds 1-5)
time_factor: 10.0        # plume clock = 10 x simulation time
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--days', type=int, default=7)
    ap.add_argument('--years', type=int, default=3)
    a = ap.parse_args()
    fs = fetchers.all_fetchers()
    if not (fs['flow'].live and fs['water_quality'].live):
        raise SystemExit('config/data_sources.yaml has no GKD stations: nothing to write')
    flow = fs['flow'].fetch(days=a.days)
    wq = fs['water_quality'].fetch(years=a.years)
    base = fs['water_quality'].baseline(years=a.years)
    q = [r['q_m3s'] for r in flow]
    times = sorted(r['time'] for r in wq)
    vals = dict(reach=ReachFrame.load().reach_id, flow_station=fs['flow'].cfg['station_path'],
                wq_station=fs['water_quality'].cfg['station_path'], t0=flow[-1]['time'], t1=flow[0]['time'],
                q=round(statistics.median(q), 2), nq=len(q), qmin=min(q), qmax=max(q),
                b0=times[0][:10], b1=times[-1][:10], nh=round(base['NH3-N']['median'], 3), nnh=base['NH3-N']['n'],
                nh90=round(base['NH3-N']['p90'], 3), do=round(base['DO']['median'], 2), ndo=base['DO']['n'])
    for o in 'ABC':
        with open(os.path.join(repo_dir(), 'config', 'scenarios', f'{o}.yaml'), 'w') as f:
            f.write(TEMPLATE.format(o=o, **vals))
    print('scenarios A, B, C:', {k: vals[k] for k in ('q', 'nq', 't0', 't1', 'nh', 'nnh', 'do', 'ndo')})


if __name__ == '__main__':
    main()
