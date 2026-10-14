"""Gateway protocol messages validate against web/schema.json; command allow-list."""
import json
import os
from types import SimpleNamespace as NS

import jsonschema
import pytest

from plumetrace_gateway import protocol as P
from plumetrace_twin.reach import ReachFrame

REPO = os.environ['PLUMETRACE_REPO']


@pytest.fixture(scope='module')
def ctx():
    return ReachFrame.load(), jsonschema.Draft7Validator(json.load(open(os.path.join(REPO, 'web', 'schema.json'))))


def fake_sample(c):
    return NS(seq=3, header=NS(stamp=NS(sec=12, nanosec=5)), river_xy=NS(x=70.0, y=24.7), arena_pose=NS(x=0.7, y=1.36),
              nh3_n_mg_l=c, do_mg_l=9.0 - 0.5 * (c - 0.05), qc_flags=0, is_replay=False)


def test_sample_alert_posterior_validate(ctx):
    fr, v = ctx
    s = P.sample_msg(fr, fake_sample(2.4))
    post = P.posterior_msg(NS(labels=['A', 'B', 'C'], probabilities=[0.97, 0.02, 0.01], map_label='A', map_strength=1.1))
    a = P.alert_msg(s, post)
    for m in (s, post, a, P.pose_msg(fr, 1.0, 0.3, 1.6, 0.0)):
        assert not list(v.iter_errors(m)), m
    assert 'likely outfall A (97 %)' in a['message'] and a['message'].startswith('NH₃-N above 0.6 mg/L')


def test_command_allow_list():
    assert P.validate_command(dict(type='command', command='abort'))[0]
    assert P.validate_command(dict(type='command', command='add_nogo', polygon=[[0, 0], [0, 1e-4], [1e-4, 0]]))[0]
    for bad in (dict(type='command', command='shutdown'), dict(type='command', command='add_nogo'),
                dict(type='command', command='add_obstacle', center=[0, 0], mode='EXPLODE'),
                dict(type='command', command='remove_obstacle'), dict(command='abort'), 'abort', None):
        assert not P.validate_command(bad)[0], bad


def test_command_to_registry_round_trip(ctx):
    fr, _ = ctx
    lat, lon, _ = fr.arena_to_geodetic(__import__('numpy').array([1.0, 1.6]))
    op = P.command_to_registry(fr, dict(type='command', command='add_obstacle', center=[float(lat), float(lon)],
                                        size_m=25, mode='STOP'), 7)
    xs = [p[0] for p in op['footprint']]
    ys = [p[1] for p in op['footprint']]
    assert op['mode'] == 'STOP' and op['id'] == 'obstacle-7'
    assert abs((min(xs) + max(xs)) / 2 - 1.0) < 1e-4 and abs(max(xs) - min(xs) - 0.25) < 1e-4


def test_plume_true_event_hello_validate(ctx):
    fr, v = ctx
    grid = [[51.43, 5.48], [51.431, 5.481]]
    pt = P.plume_points_msg('plume_true', 3.14159, grid, [0.04, 1.23456])
    assert pt['type'] == 'plume_true' and pt['points'][1][2] == 1.2346
    ev = P.event_msg(json.dumps(dict(type='sample', t=5.0, state='RUNNING', seq=2)), 5.5)
    assert ev['kind'] == 'sample' and ev['data'] == dict(state='RUNNING', seq=2)
    sc = dict(scenario='A', flow=dict(q_m3s=4.48), background=dict(nh3_n_mg_l=0.04, do_mg_l=9.1), time_factor=10.0,
              active_outfall='B')
    hello = dict(type='hello', reach='r', reach_id='i', time_factor=10.0, origin=dict(lat=0, lon=0, h=0),
                 commands=list(P.COMMANDS), scenario=P.hello_scenario(sc))
    assert 'active_outfall' not in hello['scenario'] and 'strength' not in json.dumps(hello)
    for m in (pt, P.plume_points_msg('plume_points', 1.0, grid, [0.1, 0.2]), ev, hello):
        assert not list(v.iter_errors(m)), m


def test_event_msg_rejects_garbage():
    for bad in ('not json', '[1, 2]', '{"t": 1}', '{"type": 5}', '', None):
        assert P.event_msg(bad, 1.0) is None, bad
