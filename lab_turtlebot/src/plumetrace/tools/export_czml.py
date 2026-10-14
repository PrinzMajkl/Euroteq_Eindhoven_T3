#!/usr/bin/env python3
"""Convert a PlumeTrace run log (~/plumetrace_runs/<run>/) to CZML for replay in the Cesium city view.

Reads pose.csv (robot track), samples.csv (points coloured by NH3-N, shown from their sample time),
posterior.csv (outfall probabilities in the robot description) and events.csv. Simulation seconds are
mapped onto an epoch (default 2026-10-07T00:00:00Z) so Cesium's clock can play the mission.
    python3 tools/export_czml.py <run_dir> [-o out.czml] [--epoch ISO8601]
"""
import argparse
import csv
import datetime as dt
import json
import math
import os


def read(path):
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return list(csv.DictReader(f))


def iso(epoch, s):
    return (epoch + dt.timedelta(seconds=s)).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'


def colour(c):
    t = max(0.0, min(1.0, math.log10(max(c, 0.05) / 0.05) / math.log10(60)))
    stops = [(44, 123, 182), (171, 217, 233), (255, 255, 191), (253, 174, 97), (215, 25, 28)]
    x = t * (len(stops) - 1)
    i = min(len(stops) - 2, int(x))
    f = x - i
    return [int(stops[i][k] + (stops[i + 1][k] - stops[i][k]) * f) for k in range(3)] + [255]


def build(run_dir, epoch):
    pose = read(os.path.join(run_dir, 'pose.csv'))
    samples = read(os.path.join(run_dir, 'samples.csv'))
    post = read(os.path.join(run_dir, 'posterior.csv'))
    events = read(os.path.join(run_dir, 'events.csv'))
    times = [float(r['t']) for r in pose] + [float(r['t']) for r in samples]
    if not times:
        raise SystemExit(f'no pose.csv / samples.csv data in {run_dir}')
    t0, t1 = min(times), max(times)
    rel = lambda t: float(t) - t0  # noqa: E731
    doc = [{'id': 'document', 'name': f'PlumeTrace replay {os.path.basename(run_dir.rstrip("/"))}', 'version': '1.0',
            'clock': {'interval': f'{iso(epoch, 0)}/{iso(epoch, t1 - t0)}', 'currentTime': iso(epoch, 0),
                      'multiplier': 4, 'range': 'CLAMPED', 'step': 'SYSTEM_CLOCK_MULTIPLIER'}}]
    if pose:
        carto = []
        for r in pose[::2]:
            carto += [round(rel(r['t']), 2), float(r['lon']), float(r['lat']), 2.0]
        desc = '<br>'.join(f"t={rel(p['t']):.0f} s: A {float(p['p_A']):.2f}, B {float(p['p_B']):.2f}, "
                           f"C {float(p['p_C']):.2f}" for p in post[-10:])
        doc.append({'id': 'robot', 'name': 'TurtleBot3 (replay)',
                    'availability': f'{iso(epoch, 0)}/{iso(epoch, t1 - t0)}',
                    'description': f'Posterior (last updates):<br>{desc}',
                    'position': {'epoch': iso(epoch, 0), 'cartographicDegrees': carto},
                    'point': {'pixelSize': 12, 'color': {'rgba': [20, 20, 20, 255]},
                              'outlineColor': {'rgba': [255, 255, 255, 255]}, 'outlineWidth': 2},
                    'path': {'width': 2, 'leadTime': 0, 'trailTime': 1e6,
                             'material': {'solidColor': {'color': {'rgba': [255, 255, 255, 180]}}}}})
    for r in samples:
        c = float(r['nh3_n_mg_l'])
        doc.append({'id': f"sample-{r['seq']}", 'name': f"Sample {r['seq']}",
                    'availability': f"{iso(epoch, rel(r['t']))}/{iso(epoch, t1 - t0 + 60)}",
                    'description': f"NH3-N {c:.3f} mg/L<br>DO {float(r['do_mg_l']):.2f} mg/L<br>qc {r['qc_flags']}",
                    'position': {'cartographicDegrees': [float(r['lon']), float(r['lat']), 1.0]},
                    'point': {'pixelSize': 10, 'color': {'rgba': colour(c)}, 'outlineColor': {'rgba': [0, 0, 0, 255]},
                              'outlineWidth': 1}})
    done = [e for e in events if e['type'] == 'done']
    if done:
        d = json.loads(done[-1]['data'])
        doc[0]['description'] = f"Result: {d.get('final')}, outfall {d.get('map_label')}, {d.get('samples')} samples"
    return doc


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('run_dir')
    ap.add_argument('-o', '--out')
    ap.add_argument('--epoch', default='2026-10-07T00:00:00Z')
    a = ap.parse_args()
    epoch = dt.datetime.strptime(a.epoch, '%Y-%m-%dT%H:%M:%SZ')
    doc = build(a.run_dir, epoch)
    out = a.out or os.path.join(a.run_dir, 'mission.czml')
    with open(out, 'w') as f:
        json.dump(doc, f, indent=1)
    print(f'wrote {out}: {len(doc) - 1} entities')


if __name__ == '__main__':
    main()
