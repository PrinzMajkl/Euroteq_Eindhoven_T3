#!/usr/bin/env python3
"""Build every derived reach artefact from the handoff files in data/reach/.

Inputs : data/reach/water_area.geojson, outfalls.geojson, stations.geojson (WGS84)
Outputs: config/reach_frame.yaml
         plumetrace_sim/maps/arena.{pgm,yaml}, keepout_mask.{pgm,yaml}, keepout_soft.{pgm,yaml}
         web/data/*.geojson (copies for the city view)
         docs/lab_arena_layout.svg (top-down drawing; tools/lab_tape_guide.py prints the numbers)
Deterministic: running it twice on the same inputs gives byte-identical files.

Frames. The arena (= Nav2 map) frame is the world frame of plumetrace_sim/worlds/lab_arena.world: origin
on the robot's start mark, +x the way the robot faces there. The river is laid out in a flow frame f
(arena metres): f = (0, 0) is the reach origin (upstream end of the axis), +x runs downstream, +y is
the left bank. It is placed in the arena with
    p_arena = R(FLOW_YAW) f + REACH_ORIGIN
Property theta_rad of the water polygon (default 0) is the angle from the flow direction to local east.
The water polygon must be monotone along the flow (each cross line cuts it once).
"""
import json
import math
import os
import xml.etree.ElementTree as ET

import numpy as np
import pymap3d
import shapely
import yaml
from shapely.geometry import LineString, Polygon

# Fixed defaults
SCALE = 100.0
THETA = 0.0          # arena -> river rotation, set in build()
T = (0.0, 0.0)       # arena -> river translation, set in build()
# Lab arena (worlds/lab_arena.world): inner wall faces, metres in the arena frame
ARENA_X = (-1.0, 2.6)
ARENA_Y = (-3.87, 1.0)
WALL_T, WALL_H = 0.05, 0.50
RES = 0.02
MAP_ORIGIN = (-1.2, -4.0)      # lower-left corner of every generated map
MAP_SIZE = (4.0, 5.2)          # covers x -1.2 .. 2.8, y -4.0 .. 1.2
START = (0.0, 0.0, 0.0)
# River placement (decided 2026-10-14): the 3 m of river run along the 4.85 m direction (arena +y) in the
# board-free column x 1.0 .. 2.0; the robot's bank (left bank) is the side towards the start mark.
FLOW_YAW = math.pi / 2         # flow direction in the arena frame: +y
REACH_ORIGIN = (1.85, -3.40)   # arena position of the reach origin (upstream end of the axis)
SAMPLE_X0, SAMPLE_DX, SAMPLE_N = 0.30, 0.12, 22   # along the flow, from the reach origin
STANDOFF = 0.13
# The lethal keepout mask is the water pulled back from its edge by this much. The robot stops 0.13 m from
# the edge and is 0.105 m in radius: with the mask right on the edge only 2 cm of localisation error put the
# robot "in collision" and Nav2 could not plan away from the bank (measured in simulation, 2026-10-14).
KEEPOUT_MARGIN = 0.06
CL_STEP = 1.0  # river metres between centreline samples
SOFT_PEAK, SOFT_DECAY, SOFT_RANGE = 90.0, 0.05, 0.25


def r9(v):
    return float(round(float(v), 9))


def load_fc(path):
    with open(path) as f:
        return json.load(f)


def geo_to_river(lon, lat, o):
    e, n, _ = pymap3d.geodetic2enu(lat, lon, o[2], o[0], o[1], o[2])
    return np.stack([np.asarray(e, dtype=float), np.asarray(n, dtype=float)], axis=-1)


def rot(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s], [s, c]])


def river_to_arena(p):
    return ((np.asarray(p, dtype=float) - np.array(T)) / SCALE) @ rot(THETA)


def flow_to_arena(f):
    """Flow frame (arena metres, origin at the reach origin, +x downstream) -> arena frame."""
    return np.asarray(f, dtype=float) @ rot(FLOW_YAW).T + np.array(REACH_ORIGIN)


def vertical_cut(poly, x):
    b = poly.bounds
    cut = poly.intersection(LineString([(x, b[1] - 1.0), (x, b[3] + 1.0)]))
    if cut.is_empty:
        return None
    _, y0, _, y1 = cut.bounds
    return y0, y1


def write_pgm(path, img):
    h, w = img.shape
    with open(path, 'wb') as f:
        f.write(b'P5\n%d %d\n255\n' % (w, h))
        f.write(np.ascontiguousarray(img, dtype=np.uint8).tobytes())


def write_map_yaml(path, image):
    with open(path, 'w') as f:
        f.write(f'image: {image}\nmode: trinary\nresolution: {RES}\n'
                f'origin: [{MAP_ORIGIN[0]}, {MAP_ORIGIN[1]}, 0.0]\n'
                'negate: 0\noccupied_thresh: 0.65\nfree_thresh: 0.196\n')


def pixel_centres():
    nx, ny = int(round(MAP_SIZE[0] / RES)), int(round(MAP_SIZE[1] / RES))
    xs = MAP_ORIGIN[0] + (np.arange(nx) + 0.5) * RES
    ys = MAP_ORIGIN[1] + (np.arange(ny) + 0.5) * RES
    X, Y = np.meshgrid(xs, ys[::-1])  # image row 0 is the top (max y)
    return X, Y


def world_boards(repo):
    """Every board of worlds/lab_arena.world as (name, cx, cy, yaw, sx, sy): outer walls and inner boards."""
    world = ET.parse(os.path.join(repo, 'plumetrace_sim', 'worlds', 'lab_arena.world')).getroot().find('world')
    out = []
    for m in world.findall('model'):
        size = m.find('link/collision/geometry/box/size')
        if size is None:
            continue
        x, y, _, _, _, yaw = (float(v) for v in m.findtext('pose').split())
        sx, sy, _ = (float(v) for v in size.text.split())
        out.append((m.get('name'), r9(x), r9(y), r9(yaw), sx, sy))
    return out


def board_polygon(b):
    _, cx, cy, yaw, sx, sy = b
    corners = np.array([[-sx / 2, -sy / 2], [sx / 2, -sy / 2], [sx / 2, sy / 2], [-sx / 2, sy / 2]])
    return Polygon(corners @ rot(yaw).T + np.array([cx, cy]))


def is_inner(b):
    """True for a board that stands inside the arena (not part of the outer wall)."""
    _, cx, cy, _, _, _ = b
    m = 0.15
    return ARENA_X[0] + m < cx < ARENA_X[1] - m and ARENA_Y[0] + m < cy < ARENA_Y[1] - m


def build(repo):
    rd = os.path.join(repo, 'data', 'reach')
    water_fc = load_fc(os.path.join(rd, 'water_area.geojson'))
    wf = water_fc['features'][0]
    props = wf['properties']
    ring_ll = np.array(wf['geometry']['coordinates'][0], dtype=float)
    if 'origin_lat' in props:
        origin = (float(props['origin_lat']), float(props['origin_lon']), float(props.get('origin_h', 0.0)))
    else:
        c = Polygon(ring_ll).centroid
        origin = (c.y, c.x, 0.0)
    ring = geo_to_river(ring_ll[:, 0], ring_ll[:, 1], origin)
    ring = np.round(ring, 6)
    # A real reach flows in any direction: theta_rad turns the flow direction onto local east. The geometry
    # below is worked out in the flow-aligned frame q = R(-theta_rad) p_river = SCALE * f (river metres).
    #   p_river = R(theta_rad) q,  q = SCALE * R(-FLOW_YAW) (p_arena - REACH_ORIGIN)
    #   =>  p_river = SCALE * R(theta_rad - FLOW_YAW) p_arena + t
    global THETA, T
    theta_river = float(props.get('theta_rad', 0.0))
    rot_river = rot(theta_river)
    THETA = r9(theta_river - FLOW_YAW)
    T = tuple(r9(v) for v in -SCALE * (rot(THETA) @ np.array(REACH_ORIGIN)))

    def to_river(q):
        return [[r9(v) for v in row] for row in np.asarray(q, dtype=float) @ rot_river.T]

    def aligned_to_arena(q):
        return flow_to_arena(np.asarray(q, dtype=float) / SCALE)

    poly = Polygon(ring @ rot_river)
    xmin, _, xmax, _ = poly.bounds
    eps = 1e-6
    xs = np.arange(math.ceil(xmin), math.floor(xmax) + 1e-9, CL_STEP)
    xs = np.clip(xs, xmin + eps, xmax - eps)
    cuts = [vertical_cut(poly, x) for x in xs]
    centre = [[r9(x), r9((a + b) / 2)] for x, (a, b) in zip(xs, cuts)]
    left = [[r9(x), r9(b)] for x, (a, b) in zip(xs, cuts)]
    cl = np.array(centre)
    cl_len = float(np.sum(np.hypot(*np.diff(cl, axis=0).T)))
    width = float(props.get('width_m', poly.area / cl_len))
    depth = float(props.get('depth_m', 1.0))

    def pts(name):
        fc = load_fc(os.path.join(rd, name))
        out = []
        for f in fc['features']:
            lon, lat = f['geometry']['coordinates'][:2]
            p = geo_to_river(lon, lat, origin)
            d = dict(f['properties'])
            d['lonlat'] = [float(lon), float(lat)]
            d['river_xy'] = [r9(p[0]), r9(p[1])]
            d['arena_xy'] = [r9(v) for v in river_to_arena(p)]
            out.append(d)
        return out

    outfalls = pts('outfalls.geojson')
    stations = pts('stations.geojson')

    # sampling points on the left bank edge (arena frame)
    lb = np.array(left)
    samples = []
    for k in range(SAMPLE_N):
        ax = SAMPLE_X0 + SAMPLE_DX * k   # arena metres along the flow from the reach origin
        rx = ax * SCALE
        ry = float(np.interp(rx, lb[:, 0], lb[:, 1]))
        h = 0.5
        ry0 = float(np.interp(rx - h, lb[:, 0], lb[:, 1]))
        ry1 = float(np.interp(rx + h, lb[:, 0], lb[:, 1]))
        edge = aligned_to_arena([rx, ry])
        tang = np.array([1.0, (ry1 - ry0) / (2 * h)])
        tang /= np.linalg.norm(tang)
        nrm = np.array([-tang[1], tang[0]])  # left of flow = away from the water for the left bank
        nrm = rot(FLOW_YAW) @ nrm            # the same direction in the arena frame
        wp = edge + STANDOFF * nrm
        yaw = math.atan2(-nrm[1], -nrm[0])
        samples.append({'index': k, 'along': r9(ax), 'edge': [r9(v) for v in edge],
                        'waypoint': [r9(v) for v in wp], 'yaw': r9(yaw)})

    frame = {
        'reach_id': props['reach_id'],
        'name': props.get('name', props['reach_id']),
        'origin': {'lat': origin[0], 'lon': origin[1], 'h': origin[2]},
        'transform': {'scale': SCALE, 'theta_rad': THETA, 't': list(T),
                      'note': 'river = scale * R(theta) * arena + t; river = local ENU at origin'},
        'width_m': r9(width), 'depth_m': r9(depth),
        'arena': {'frame': 'world frame of plumetrace_sim/worlds/lab_arena.world (origin = start mark)',
                  'x_range': list(ARENA_X), 'y_range': list(ARENA_Y),
                  'size': [r9(ARENA_X[1] - ARENA_X[0]), r9(ARENA_Y[1] - ARENA_Y[0])],
                  'wall_thickness': WALL_T, 'wall_height': WALL_H,
                  'resolution': RES, 'map_origin': list(MAP_ORIGIN), 'map_size': list(MAP_SIZE),
                  'keepout_margin': KEEPOUT_MARGIN,
                  'start_pose': list(START),
                  'flow_yaw': r9(FLOW_YAW), 'reach_origin': list(REACH_ORIGIN),
                  'inner_boards': [{'name': b[0], 'xy': [b[1], b[2]], 'yaw': b[3], 'size': [b[4], b[5]]}
                                   for b in world_boards(repo) if is_inner(b)]},
        'outfalls': outfalls,
        'stations': stations,
        'sampling_points': samples,
        'centreline': to_river(centre),
        'left_bank': to_river(left),
        'water_ring_river': [[r9(x), r9(y)] for x, y in ring],
    }
    return frame, poly


def write_outputs(repo, frame, poly_river):
    with open(os.path.join(repo, 'config', 'reach_frame.yaml'), 'w') as f:
        f.write('# GENERATED by tools/reach_build.py from data/reach/*.geojson. Do not edit.\n')
        yaml.safe_dump(frame, f, sort_keys=False, default_flow_style=None, width=120)

    sim = os.path.join(repo, 'plumetrace_sim')
    maps = os.path.join(sim, 'maps')
    os.makedirs(maps, exist_ok=True)
    ring_a = river_to_arena(np.array(frame['water_ring_river']))
    poly_a = Polygon(ring_a)
    X, Y = pixel_centres()
    # occupancy map from the world file: every board occupied (0 = black), free 254.
    # A cell is occupied when the board touches it, so the 5 cm boards are never thinner than 2 cells.
    occ = np.full(X.shape, 254, dtype=np.uint8)
    pts = shapely.points(X.ravel(), Y.ravel())
    for b in world_boards(repo):
        m = (shapely.distance(board_polygon(b), pts) <= RES / 2).reshape(X.shape)
        occ[m] = 0
    write_pgm(os.path.join(maps, 'arena.pgm'), occ)
    write_map_yaml(os.path.join(maps, 'arena.yaml'), 'arena.pgm')
    # keepout mask: water more than KEEPOUT_MARGIN from the edge = black (-> 100), else white (-> 0)
    water = shapely.contains_xy(poly_a, X, Y)
    mask = np.where(shapely.contains_xy(poly_a.buffer(-KEEPOUT_MARGIN), X, Y), 0, 255).astype(np.uint8)
    write_pgm(os.path.join(maps, 'keepout_mask.pgm'), mask)
    write_map_yaml(os.path.join(maps, 'keepout_mask.yaml'), 'keepout_mask.pgm')
    # soft margin: occupancy 99 on water, 90 exp(-d / 0.05) inland up to 0.25 m.
    # Never lethal, so it shapes global paths without trapping a robot parked at the bank.
    d = shapely.distance(poly_a.boundary, shapely.points(X.ravel(), Y.ravel())).reshape(X.shape)
    occ_soft = np.where(water, 99.0, np.where(d < SOFT_RANGE, SOFT_PEAK * np.exp(-d / SOFT_DECAY), 0.0))
    soft = np.round(255.0 - occ_soft / 99.0 * 255.0).astype(np.uint8)
    write_pgm(os.path.join(maps, 'keepout_soft.pgm'), soft)
    with open(os.path.join(maps, 'keepout_soft.yaml'), 'w') as f:
        f.write(f'image: keepout_soft.pgm\nmode: scale\nresolution: {RES}\n'
                f'origin: [{MAP_ORIGIN[0]}, {MAP_ORIGIN[1]}, 0.0]\n'
                'negate: 0\noccupied_thresh: 1.0\nfree_thresh: 0.0\n')

    return poly_a, mask


def write_drawing(repo, frame):
    """Top-down drawing of the arena for taping: docs/lab_arena_layout.svg (arena x to the right, y up)."""
    a = frame['arena']
    k = 200.0                                  # pixels per metre
    x0, y1 = MAP_ORIGIN[0] - 0.25, MAP_ORIGIN[1] + MAP_SIZE[1] + 0.15
    w, h = (MAP_SIZE[0] + 0.5) * k, (MAP_SIZE[1] + 0.55) * k

    def P(x, y):
        return f'{(x - x0) * k:.1f},{(y1 - y) * k:.1f}'

    def poly(pts, **kw):
        attrs = ' '.join(f'{n.replace("_", "-")}="{v}"' for n, v in kw.items())
        return f'<polygon points="{" ".join(P(x, y) for x, y in pts)}" {attrs}/>'

    def line(pa, pb, **kw):
        (xa, ya), (xb, yb) = (P(*pa).split(','), P(*pb).split(','))
        attrs = ' '.join(f'{n.replace("_", "-")}="{v}"' for n, v in kw.items())
        return f'<line x1="{xa}" y1="{ya}" x2="{xb}" y2="{yb}" {attrs}/>'

    def text(x, y, s, size=13, anchor='middle', fill='#222', dx=0, dy=0):
        px, py = P(x, y).split(',')
        return (f'<text x="{float(px) + dx:.1f}" y="{float(py) + dy:.1f}" font-size="{size}" text-anchor="{anchor}" '
                f'fill="{fill}">{s}</text>')

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.0f}" height="{h:.0f}" viewBox="0 0 {w:.0f} {h:.0f}" '
         'font-family="DejaVu Sans, Arial, sans-serif">',
         f'<rect width="{w:.0f}" height="{h:.0f}" fill="#ffffff"/>']
    # grid every 0.5 m with arena coordinates
    for gx in np.arange(-1.0, 2.6 + 1e-9, 0.5):
        o.append(line((gx, MAP_ORIGIN[1]), (gx, 1.2), stroke='#dddddd', stroke_width=1))
        o.append(text(gx, MAP_ORIGIN[1], f'x {gx:+.1f}', 11, fill='#666', dy=14))
    for gy in np.arange(-3.5, 1.0 + 1e-9, 0.5):
        o.append(line((MAP_ORIGIN[0], gy), (2.8, gy), stroke='#dddddd', stroke_width=1))
        o.append(text(MAP_ORIGIN[0], gy, f'y {gy:+.1f}', 11, anchor='end', fill='#666', dx=-4, dy=4))
    # water, boards
    ring_a = river_to_arena(np.array(frame['water_ring_river']))
    o.append(poly(ring_a, fill='#9ecbff', stroke='#1f6feb', stroke_width=2))
    for b in world_boards(repo):
        o.append(poly(list(board_polygon(b).exterior.coords)[:4], fill='#8b5a2b' if is_inner(b) else '#444444',
                      stroke='none'))
    # sampling points: edge (probe) and waypoint (robot centre)
    for sp in frame['sampling_points']:
        (ex, ey), (wx, wy) = sp['edge'], sp['waypoint']
        px, py = P(wx, wy).split(',')
        o.append(f'<circle cx="{px}" cy="{py}" r="{0.105 * k:.1f}" fill="none" stroke="#bbbbbb" stroke-width="0.7"/>')
        o.append(f'<circle cx="{px}" cy="{py}" r="3.5" fill="#2da44e"/>')
        if sp['index'] % 3 == 0:
            o.append(text(wx, wy, str(sp['index']), 10, anchor='end', fill='#2da44e', dx=-26, dy=4))
    # flow arrow
    c = river_to_arena(np.array(frame['centreline']))
    (ax, ay), (bx, by) = c[130], c[170]
    o.append('<defs><marker id="arr" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">'
             '<path d="M0,0 L8,4 L0,8 z" fill="#0b3d91"/></marker></defs>')
    o.append(line((ax, ay), (bx, by), stroke='#0b3d91', stroke_width=3, marker_end='url(#arr)'))
    o.append(text(REACH_ORIGIN[0] + 0.02, REACH_ORIGIN[1] - 0.12, 'upstream end', 11, fill='#1f6feb'))
    o.append(text(REACH_ORIGIN[0] + 0.02, REACH_ORIGIN[1] + 3.0 + 0.08, 'downstream end (flow)', 11, fill='#1f6feb'))
    # outfalls
    for of in frame['outfalls']:
        x, y = of['arena_xy']
        px, py = P(x, y).split(',')
        o.append(f'<circle cx="{px}" cy="{py}" r="7" fill="#d1242f"/>')
        o.append(text(x, y, f"outfall {of['id']} ({x:.2f}, {y:.2f})", 12, anchor='start', fill='#d1242f', dx=52, dy=4))
    # start mark
    sx, sy, _ = a['start_pose']
    px, py = P(sx, sy).split(',')
    o.append(f'<circle cx="{px}" cy="{py}" r="{0.105 * k:.1f}" fill="#ffd33d" stroke="#222" stroke-width="1.5"/>')
    o.append(line((sx, sy), (sx + 0.25, sy), stroke='#222', stroke_width=3))
    o.append(text(sx, sy, 'start mark (0, 0), robot faces +x', 12, anchor='start', dx=-20, dy=40))
    o.append(text(0.8, 1.2, f"{frame['name']}: {frame['transform']['scale']:.0f} m of river per arena metre. "
                  'Brown: inner boards. Green: robot stops (22). Red: outfalls.', 12, dy=-8))
    o.append('</svg>')
    docs = os.path.join(repo, 'docs')
    os.makedirs(docs, exist_ok=True)
    with open(os.path.join(docs, 'lab_arena_layout.svg'), 'w') as f:
        f.write('\n'.join(o) + '\n')


def copy_web(repo):
    """The city view is served from web/: give it the handoff GeoJSON files."""
    import shutil
    dst = os.path.join(repo, 'web', 'data')
    os.makedirs(dst, exist_ok=True)
    for name in ('water_area.geojson', 'outfalls.geojson', 'stations.geojson'):
        shutil.copyfile(os.path.join(repo, 'data', 'reach', name), os.path.join(dst, name))


def main(repo):
    frame, poly = build(repo)
    write_outputs(repo, frame, poly)
    write_drawing(repo, frame)
    copy_web(repo)
    print('built reach artefacts for', frame['reach_id'])


if __name__ == '__main__':
    main(os.environ.get('PLUMETRACE_REPO') or os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
