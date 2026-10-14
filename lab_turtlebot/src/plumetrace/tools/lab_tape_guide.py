#!/usr/bin/env python3
"""Where to tape the river on the lab floor.

    python3 tools/lab_tape_guide.py [step_m]        (drawing: docs/lab_arena_layout.svg)

Everything is measured from the two walls next to the robot's start mark, the way you stand there
looking along the robot's heading:
    "from back wall"  = distance from the wall behind the robot      (arena x + 1.00 m)
    "from left wall"  = distance from the wall on the robot's left   (1.00 m - arena y)
Arena frame (= Nav2 map frame): origin on the start mark, +x the way the robot faces, +y to its left.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'plumetrace_twin'))
from shapely.geometry import LineString  # noqa: E402

from plumetrace_twin.reach import ReachFrame  # noqa: E402


def main():
    step = float(sys.argv[1]) if len(sys.argv) > 1 else 0.25
    fr = ReachFrame.load()
    a = fr.arena
    (x0, x1), (y0, y1) = a['x_range'], a['y_range']
    sx, sy, _ = a['start_pose']
    water = fr.water_polygon_arena()

    def back(x):
        return x - x0

    def left(y):
        return y1 - y

    print(f'{fr.name}: arena {x1 - x0:.2f} x {y1 - y0:.2f} m (inner wall faces), 1 m on the floor = '
          f'{fr.scale:.0f} m of river')
    print(f'robot start mark: {back(sx):.2f} m from the back wall, {left(sy):.2f} m from the left wall, '
          'facing away from the back wall (arena 0, 0, yaw 0)')
    wx0, wy0, wx1, wy1 = water.bounds
    print(f'river: {wy1 - wy0:.2f} m long, parallel to the back wall, water between {back(wx0):.2f} and '
          f'{back(wx1):.2f} m from the back wall; it starts {left(wy1):.2f} m and ends {left(wy0):.2f} m '
          'from the left wall. The water flows towards the left wall.')
    print('\nriver edges (tape both lines; the near bank is the one towards the start mark):')
    print(' from left wall | near bank from back wall | far bank from back wall |  arena y | near x | far x')
    n = int(round((wy1 - wy0) / step))
    for k in range(n + 1):
        y = min(wy1 - 1e-6, max(wy0 + 1e-6, wy1 - k * (wy1 - wy0) / n))
        cut = water.intersection(LineString([(x0 - 1, y), (x1 + 1, y)]))
        xs = [c[0] for g in getattr(cut, 'geoms', [cut]) for c in g.coords]
        print(f'{left(y):15.2f} | {back(min(xs)):24.2f} | {back(max(xs)):23.2f} | {y:8.2f} | {min(xs):6.2f} | '
              f'{max(xs):5.2f}')
    print('\noutfall markers (on the near bank):')
    for o in fr.cfg['outfalls']:
        x, y = o['arena_xy']
        print(f"  {o['id']}: {back(x):.2f} m from the back wall, {left(y):.2f} m from the left wall "
              f'(arena {x:.2f}, {y:.2f})')
    sp = fr.sampling_points()
    wxs = [p['waypoint'][0] for p in sp]
    print(f'\nrobot stops: {len(sp)} points on the near bank, {back(min(wxs)):.2f} to {back(max(wxs)):.2f} m from '
          f"the back wall, {left(sp[-1]['waypoint'][1]):.2f} to {left(sp[0]['waypoint'][1]):.2f} m from the left wall.")
    print(f'Keep the strip from {back(min(wxs)) - 0.35:.2f} m from the back wall up to the near bank clear '
          'over the whole length of the river.')
    print('\ninner boards as in the simulated arena (centre; place marker objects where the lab has them):')
    for b in a['inner_boards']:
        x, y = b['xy']
        print(f"  {b['name']:12s} {back(x):.2f} m from the back wall, {left(y):.2f} m from the left wall")


if __name__ == '__main__':
    main()
