"""Reach handoff tooling: the check script passes on the live reach; fetchers run in fixture mode."""
import os
import subprocess

from plumetrace_twin import fetchers

REPO = os.environ['PLUMETRACE_REPO']
def test_check_passes_on_live_reach():
    r = subprocess.run(['python3', os.path.join(REPO, 'tools', 'check_reach_data.py')], capture_output=True, text=True)
    print(r.stdout)
    assert r.returncode == 0 and 'PASS' in r.stdout


def test_check_catches_errors(tmp_path):
    import json
    import shutil
    for f in ('water_area.geojson', 'outfalls.geojson', 'stations.geojson'):
        shutil.copy(os.path.join(REPO, 'data', 'reach', f), tmp_path / f)
    o = json.load(open(tmp_path / 'outfalls.geojson'))
    o['features'][1]['properties'].pop('edm_site_id')
    o['features'][2]['properties']['bank'] = 'middle'
    json.dump(o, open(tmp_path / 'outfalls.geojson', 'w'))
    r = subprocess.run(['python3', os.path.join(REPO, 'tools', 'check_reach_data.py'), str(tmp_path)], capture_output=True, text=True)
    assert r.returncode == 1 and 'edm_site_id' in r.stdout and 'bank must be' in r.stdout


def test_fetchers_fixture_mode():
    fs = fetchers.all_fetchers({})  # no stations configured
    assert all(f.mode == 'fixture' for f in fs.values())
    flow = fs['flow'].fetch()
    assert len(flow) == 288 and 9.5 < sum(r['q_m3s'] for r in flow) / len(flow) < 11
    base = fs['water_quality'].baseline()
    assert 0.02 < base['NH3-N']['median'] < 0.1 and 8 < base['DO']['median'] < 10
    edm = fs['edm'].fetch()
    assert {e['site_id'] for e in edm} == {'PLACEHOLDER-EDM-A', 'PLACEHOLDER-EDM-B', 'PLACEHOLDER-EDM-C'}


def test_fetchers_configured_live():
    fs = fetchers.all_fetchers()
    assert fs['flow'].mode == 'live' and fs['water_quality'].mode == 'live' and fs['edm'].mode == 'fixture'


def test_gkd_parsers_offline():
    d = os.path.join(REPO, 'tests', 'data')
    flow = fetchers.GKDFlow({}).parse(open(os.path.join(d, 'gkd_discharge_table.html')).read())
    assert len(flow) == 12 and flow[0] == dict(time='2026-10-10T18:15:00+01:00', q_m3s=5.69)
    wq = fetchers.GKDWaterQuality({}).parse(open(os.path.join(d, 'gkd_chemistry_table.html')).read())
    assert dict(time='2024-12-04T00:00:00+01:00', determinand='NH3-N', value=0.02, unit='mg/L', below_loq=True) in wq
    assert dict(time='2024-12-04T00:00:00+01:00', determinand='DO', value=12.6, unit='mg/L', below_loq=False) in wq
    assert not any(r['determinand'] == 'NH3-N' and r['time'].startswith('2019-04-29') for r in wq)  # '--' is skipped
    assert fetchers.parse_value('6,15') == (6.15, False)
