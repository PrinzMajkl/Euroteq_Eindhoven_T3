"""Reach and the coordinate chain."""
import os

import numpy as np
import pytest
from shapely.geometry import Point, Polygon

from plumetrace_twin.reach import ReachFrame

REPO = os.environ['PLUMETRACE_REPO']


@pytest.fixture(scope='module')
def frame():
    return ReachFrame.load(os.path.join(REPO, 'config', 'reach_frame.yaml'))


def read_pgm(path):
    with open(path, 'rb') as f:
        data = f.read()
    parts = data.split(b'\n', 3)
    w, h = map(int, parts[1].split())
    return np.frombuffer(parts[3], dtype=np.uint8).reshape(h, w)


def test_transform_round_trip(frame):
    rng = np.random.default_rng(0)
    arena = rng.uniform([-1.0, -3.87], [2.6, 1.0], size=(2000, 2))
    river = frame.arena_to_river(arena)
    lat, lon, h = frame.river_to_geodetic(river)
    river2 = frame.geodetic_to_river(lat, lon, h)
    arena2 = frame.river_to_arena(river2)
    err_river = np.max(np.hypot(*(river2 - river).T))
    err_arena = np.max(np.hypot(*(arena2 - arena).T))
    print(f'max round-trip error: river {err_river:.3e} m, arena {err_arena:.3e} m')
    assert err_river < 1e-6
    assert err_arena < 1e-6


def test_transform_defaults(frame):
    # arena `reach_origin` is the reach origin; the flow runs along `flow_yaw` (arena +y in the lab),
    # 1 arena metre = `scale` river metres
    o = np.array(frame.arena['reach_origin'])
    fy = frame.arena['flow_yaw']
    down = np.array([np.cos(fy), np.sin(fy)])
    assert np.allclose(o, [1.85, -3.40]) and np.allclose(down, [0.0, 1.0], atol=1e-9)
    assert np.allclose(frame.arena_to_river(o), [0.0, 0.0], atol=1e-6)
    lat, lon, _ = frame.river_to_geodetic(np.array([0.0, 0.0]))
    assert abs(lat - frame.lat0) < 1e-12 and abs(lon - frame.lon0) < 1e-12
    d = frame.arena_to_river(o + 3.0 * down) - frame.arena_to_river(o)
    assert abs(np.hypot(*d) - 3.0 * frame.scale) < 1e-6
    s, n = frame.to_sn([frame.arena_to_river(o + 0.5 * down), frame.arena_to_river(o + 2.5 * down)])
    assert s[1] > s[0]
    # the left bank (n > 0) is the side of the start mark
    _, n = frame.to_sn([frame.arena_to_river(o + 1.5 * down + [-0.5, 0.0])])
    assert n[0] > 0
    assert frame.arena['start_pose'] == [0.0, 0.0, 0.0]


def test_mask_area(frame):
    mask = read_pgm(os.path.join(REPO, 'plumetrace_sim', 'maps', 'keepout_mask.pgm'))
    assert mask.shape == (260, 200)   # 5.2 x 4.0 m at 0.02 m, origin (-1.2, -4.0)
    res = 0.02
    mask_area = np.count_nonzero(mask == 0) * res * res
    # the lethal mask is the water pulled back from its edge by keepout_margin (room for the robot at the bank)
    poly = Polygon(frame.river_to_arena(np.array(frame.cfg['water_ring_river']))).buffer(-frame.arena['keepout_margin'])
    rel = abs(mask_area - poly.area) / poly.area
    print(f'mask water area {mask_area:.4f} m2, polygon {poly.area:.4f} m2, diff {rel * 100:.3f} %')
    assert rel < 0.08  # 2 cm cells on a strip about 0.1 m wide in the arena


def test_occupancy_walls(frame):
    """arena.pgm is the lab arena of worlds/lab_arena.world: outer walls, inner boards, free start and bank."""
    occ = read_pgm(os.path.join(REPO, 'plumetrace_sim', 'maps', 'arena.pgm'))
    assert occ.shape == (260, 200)
    ox, oy = frame.arena['map_origin']

    def cell(x, y):
        return occ[occ.shape[0] - 1 - int((y - oy) // 0.02), int((x - ox) // 0.02)]

    # a point on each outer wall (board centres) and on three inner boards
    for x, y in [(-1.02, -1.11), (2.63, -1.14), (0.50, 1.00), (0.52, -3.86), (0.77, 0.67), (0.97, -1.37), (2.31, -0.80)]:
        assert cell(x, y) == 0, (x, y)
    assert set(np.unique(occ)) == {0, 254}
    # free: the start mark, every robot stop and the straight strip along the bank
    assert np.all(occ[125:136, 55:66] == 254)   # 0.2 m square around (0, 0)
    for p in frame.sampling_points():
        x, y = p['waypoint']
        r = int((y - oy) // 0.02)
        c = int((x - ox) // 0.02)
        assert np.all(occ[occ.shape[0] - 1 - r - 8: occ.shape[0] - r + 8, c - 8: c + 9] == 254)
    # every inner board is clear of the water and of the robot stops by more than the robot radius
    from shapely.geometry import MultiPoint
    water = Polygon(frame.river_to_arena(np.array(frame.cfg['water_ring_river'])))
    stops = MultiPoint([tuple(p['waypoint']) for p in frame.sampling_points()])
    assert len(frame.arena['inner_boards']) == 8
    for b in frame.arena['inner_boards']:
        c, s = np.cos(b['yaw']), np.sin(b['yaw'])
        hx, hy = b['size'][0] / 2, b['size'][1] / 2
        corners = np.array([[-hx, -hy], [hx, -hy], [hx, hy], [-hx, hy]]) @ np.array([[c, s], [-s, c]]) + b['xy']
        board = Polygon(corners)
        assert board.distance(water) > 0.02, b['name']
        assert board.distance(stops) > 0.30, b['name']


def test_sampling_points(frame):
    sp = frame.sampling_points()
    assert len(sp) == 22
    assert np.allclose([p['along'] for p in sp], 0.30 + 0.12 * np.arange(22))
    # the flow runs along arena +y from the reach origin: `along` is the edge's y offset
    assert np.allclose([p['edge'][1] - frame.arena['reach_origin'][1] for p in sp], [p['along'] for p in sp])
    for p in sp:
        e, w, yaw = frame.bank_waypoint(p['along'])
        assert np.allclose(e, p['edge'], atol=1e-6) and np.allclose(w, p['waypoint'], atol=1e-6)
        assert abs(yaw - p['yaw']) < 1e-6
    poly = Polygon(frame.river_to_arena(np.array(frame.cfg['water_ring_river'])))
    for p in sp:
        assert abs(np.linalg.norm(p['waypoint'] - p['edge']) - 0.13) < 1e-6
        assert poly.exterior.distance(Point(p['edge'])) < 1e-4
        assert not poly.contains(Point(p['waypoint']))
        probe = p['waypoint'] + 0.13 * np.array([np.cos(p['yaw']), np.sin(p['yaw'])])
        assert np.allclose(probe, p['edge'], atol=1e-6)


def test_outfalls_on_left_bank(frame):
    assert [o['id'] for o in frame.outfalls] == ['A', 'B', 'C']
    poly = Polygon(frame.river_to_arena(np.array(frame.cfg['water_ring_river'])))
    last = -1.0
    for o in frame.outfalls:
        assert o['bank'] == 'left'
        s, n = frame.outfall_sn(o['id'])
        assert s > last and 0.25 * frame.width < n < 0.85 * frame.width  # downstream order, on the left edge
        assert poly.exterior.distance(Point(o['arena_xy'])) < 0.05
        last = s


def test_sn_round_trip(frame):
    rng = np.random.default_rng(1)
    s = rng.uniform(5, frame.length - 5, 500)
    n = rng.uniform(-5, 5, 500)
    p = frame.from_sn(s, n)
    s2, n2 = frame.to_sn(p)
    # polyline centreline (1 m segments): normals jump at vertices, <= ~0.07 m in s at n = 10 m
    # a surveyed centreline has sharper vertices than the stand-in: allow 1 cm across
    assert np.max(np.abs(s2 - s)) < 0.1 and np.max(np.abs(n2 - n)) < 1e-2
