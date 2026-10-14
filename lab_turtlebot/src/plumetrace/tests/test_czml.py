"""tools/export_czml.py turns a run dir (run_logger CSVs) into valid CZML with a robot path and samples."""
import csv
import json
import os
import subprocess
import sys

REPO = os.environ['PLUMETRACE_REPO']


def write_csv(path, header, rows):
    with open(path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def make_run(d):
    write_csv(d / 'pose.csv', ['t', 'x', 'y', 'yaw', 'lat', 'lon'],
              [[100 + 0.2 * i, 0.3 + 0.01 * i, 1.6, 0.0, 51.5 + 1e-6 * i, -0.1 + 1e-6 * i] for i in range(50)])
    write_csv(d / 'samples.csv', ['seq', 't', 'arena_x', 'arena_y', 'arena_theta', 'river_x', 'river_y', 'lat', 'lon',
                                  'nh3_n_mg_l', 'do_mg_l', 'qc_flags', 'is_replay'],
              [[1, 103.0, 0.4, 1.6, 0.0, 10.0, 2.0, 51.50001, -0.09999, 0.08, 8.1, 0, 0],
               [2, 108.0, 0.5, 1.6, 0.0, 20.0, 2.0, 51.50002, -0.09998, 2.5, 6.0, 0, 0]])
    write_csv(d / 'posterior.csv', ['t', 'p_A', 'p_B', 'p_C', 'map_label', 'map_strength'],
              [[103.1, 0.5, 0.3, 0.2, 'A', 0.5], [108.1, 0.97, 0.02, 0.01, 'A', 0.97]])
    done = json.dumps(dict(type='done', final='DONE', samples=2, map_label='A'))
    write_csv(d / 'events.csv', ['t', 'type', 'state', 'data'], [[108.5, 'done', '', done]])


def test_export_czml(tmp_path):
    make_run(tmp_path)
    out = tmp_path / 'mission.czml'
    p = subprocess.run([sys.executable, os.path.join(REPO, 'tools', 'export_czml.py'), str(tmp_path), '-o', str(out)],
                       capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    doc = json.loads(out.read_text())
    assert isinstance(doc, list) and doc[0]['id'] == 'document' and doc[0]['version'] == '1.0'
    assert 'clock' in doc[0] and 'Result: DONE, outfall A, 2 samples' == doc[0]['description']
    ids = {e['id']: e for e in doc[1:]}
    robot = ids['robot']
    carto = robot['position']['cartographicDegrees']
    assert len(carto) % 4 == 0 and len(carto) // 4 == 25  # every second pose, (t, lon, lat, h)
    assert carto[0] == 0.0 and carto[1] == -0.1 and carto[2] == 51.5
    assert 'path' in robot and '0.97' in robot['description']
    assert {'sample-1', 'sample-2'} <= set(ids)
    s1, s2 = ids['sample-1'], ids['sample-2']
    assert s1['position']['cartographicDegrees'][:2] == [-0.09999, 51.50001]
    assert s1['point']['color']['rgba'] != s2['point']['color']['rgba']  # coloured by NH3-N


def test_export_czml_empty_run_fails(tmp_path):
    p = subprocess.run([sys.executable, os.path.join(REPO, 'tools', 'export_czml.py'), str(tmp_path)],
                       capture_output=True, text=True)
    assert p.returncode != 0 and 'no pose.csv' in (p.stderr + p.stdout)
