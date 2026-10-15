"""Scan-to-map fit used by tools/localize.py, checked on the real arena map with simulated scans."""
import os

import numpy as np
import pytest

from plumetrace_twin.scanfit import DistanceField, fit_score, judge, mirror_pose, scan_endpoints

REPO = os.environ['PLUMETRACE_REPO']
N_BEAMS = 220  # LDS-02: about 0.0285 rad per beam
INC = 2 * np.pi / N_BEAMS


def load_map():
    """arena.pgm as an OccupancyGrid-like array (row 0 = lowest y), with resolution and origin from arena.yaml."""
    with open(os.path.join(REPO, 'plumetrace_sim', 'maps', 'arena.pgm'), 'rb') as f:
        data = f.read()
    parts = data.split(b'\n', 3)
    w, h = map(int, parts[1].split())
    img = np.frombuffer(parts[3], dtype=np.uint8).reshape(h, w)
    occ = np.where(img < 0.35 * 255, 100, 0)  # trinary: dark = occupied (occupied_thresh 0.65, negate 0)
    return occ[::-1].copy(), 0.02, -1.2, -4.0


def raycast(grid, res, ox, oy, x, y, yaw, max_range=3.5, noise=0.0, rng=None):
    """Simulated 360 deg scan from (x, y, yaw) on the grid; ranges beyond max_range are inf."""
    ranges = np.full(N_BEAMS, np.inf)
    steps = np.arange(0.0, max_range, res / 2)
    for i in range(N_BEAMS):
        a = yaw + i * INC
        px, py = x + steps * np.cos(a), y + steps * np.sin(a)
        col = ((px - ox) / res).astype(int)
        row = ((py - oy) / res).astype(int)
        inside = (col >= 0) & (col < grid.shape[1]) & (row >= 0) & (row < grid.shape[0])
        hit = np.zeros(len(steps), bool)
        hit[inside] = grid[row[inside], col[inside]] >= 65
        if hit.any():
            ranges[i] = steps[np.argmax(hit)]
    if noise and rng is not None:
        ranges = ranges + rng.normal(0, noise, N_BEAMS)
    return ranges


@pytest.fixture(scope='module')
def arena():
    grid, res, ox, oy = load_map()
    return grid, res, ox, oy, DistanceField(grid.ravel(), grid.shape[1], grid.shape[0], res, ox, oy)


def score(arena, ranges, x, y, yaw):
    *_, field = arena
    return fit_score(field, scan_endpoints(ranges, 0.0, INC, x, y, yaw, 0.12, 3.5))


POSES = [(0.0, 0.0, 0.0), (1.2, -0.5, 1.57), (0.3, -2.8, -2.0), (2.0, -2.0, 3.0)]


@pytest.mark.parametrize('pose', POSES)
def test_true_pose_fits(arena, pose):
    grid, res, ox, oy, _ = arena
    rng = np.random.default_rng(1)
    ranges = raycast(grid, res, ox, oy, *pose, noise=0.015, rng=rng)
    assert score(arena, ranges, *pose) >= 0.85  # well above the 0.75 keep threshold


@pytest.mark.parametrize('pose', POSES)
def test_wrong_poses_do_not_fit(arena, pose):
    """Clearly wrong poses (30 cm across, 30 deg) fall below the 0.65 acceptance threshold."""
    grid, res, ox, oy, _ = arena
    ranges = raycast(grid, res, ox, oy, *pose)
    x, y, yaw = pose
    for w in [(x + 0.30, y, yaw), (x, y, yaw + 0.5)]:
        assert score(arena, ranges, *w) < 0.65, w


def test_centre_is_arena_centre(arena):
    *_, field = arena
    assert field.centre == pytest.approx((0.8, -1.435), abs=0.02)


@pytest.mark.parametrize('pose', POSES)
def test_mirror_told_apart(arena, pose):
    """The arena is nearly point-symmetric: the mirrored pose still fits well, but less than the true one,
    and judge() accepts the true pose and flags the mirrored one."""
    grid, res, ox, oy, field = arena
    ranges = raycast(grid, res, ox, oy, *pose, noise=0.015, rng=np.random.default_rng(4))
    m = mirror_pose(*pose, field.centre)
    f_true, f_mirror = score(arena, ranges, *pose), score(arena, ranges, *m)
    assert f_mirror > 0.6  # why a plain threshold is not enough
    assert judge(f_true, f_mirror, 0.65) == 'ok'
    assert judge(f_mirror, f_true, 0.65) == 'mirrored'  # AMCL locked on the mirror: detected


def test_mirror_twice_is_identity():
    p = mirror_pose(*mirror_pose(1.2, -0.5, 1.57, (0.8, -1.435)), (0.8, -1.435))
    assert p == pytest.approx((1.2, -0.5, 1.57))


def test_small_error_still_accepted(arena):
    """AMCL's answer is never exact: 3 cm and 3 deg off must still pass the acceptance threshold."""
    grid, res, ox, oy, _ = arena
    ranges = raycast(grid, res, ox, oy, 1.2, -0.5, 1.57, noise=0.015, rng=np.random.default_rng(2))
    assert score(arena, ranges, 1.23, -0.52, 1.57 + np.radians(3)) >= 0.65


def test_clutter_tolerated(arena):
    """People's legs or a bag near the robot: 25 % of beams blocked short must not reject the right pose."""
    grid, res, ox, oy, _ = arena
    rng = np.random.default_rng(3)
    ranges = raycast(grid, res, ox, oy, 0.0, 0.0, 0.0, noise=0.015, rng=rng)
    blocked = rng.choice(N_BEAMS, N_BEAMS // 4, replace=False)
    ranges[blocked] = rng.uniform(0.2, 0.6, len(blocked))
    assert score(arena, ranges, 0.0, 0.0, 0.0) >= 0.65


def test_empty_map_rejected():
    with pytest.raises(ValueError):
        DistanceField(np.zeros(100), 10, 10, 0.1, 0, 0)
