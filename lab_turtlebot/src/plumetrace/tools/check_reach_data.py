#!/usr/bin/env python3
"""Validate the reach handoff files in data/reach/.

Errors (exit 1): wrong CRS, missing or invalid geometry, missing required properties, outfalls not at
the water edge. Warnings: optional FME products (CityGML, 3D Tiles, meshes) not delivered yet.
    python3 tools/check_reach_data.py [data/reach]
"""
import json
import os
import sys

from shapely.geometry import Point, shape
from shapely.validation import explain_validity

WGS84 = {'urn:ogc:def:crs:OGC:1.3:CRS84', 'urn:ogc:def:crs:EPSG::4326', 'EPSG:4326', 'epsg:4326', 'CRS84'}
EDGE_TOL_M = 5.0  # outfalls and stations must be within this distance of the water polygon


def load(path, errors):
    if not os.path.exists(path):
        errors.append(f'{os.path.basename(path)}: missing')
        return None
    try:
        with open(path) as f:
            fc = json.load(f)
    except ValueError as e:
        errors.append(f'{os.path.basename(path)}: not JSON ({e})')
        return None
    name = os.path.basename(path)
    if fc.get('type') != 'FeatureCollection' or not fc.get('features'):
        errors.append(f'{name}: not a non-empty FeatureCollection')
        return None
    crs = (fc.get('crs') or {}).get('properties', {}).get('name')
    if crs is not None and crs not in WGS84:
        errors.append(f'{name}: CRS {crs} is not WGS84 (RFC 7946 GeoJSON must be lon/lat WGS84)')
    for i, f in enumerate(fc['features']):
        for x, y in _coords(f.get('geometry', {})):
            if not (-180 <= x <= 180 and -90 <= y <= 90):
                errors.append(f'{name}: feature {i} coordinate ({x}, {y}) outside lon/lat range')
                break
    return fc


def _coords(g):
    t, c = g.get('type'), g.get('coordinates')
    if t == 'Point':
        return [c]
    if t == 'Polygon':
        return [p for ring in c for p in ring]
    if t == 'MultiPolygon':
        return [p for poly in c for ring in poly for p in ring]
    return []


def metres_from(poly_ll, pt_ll):
    import pymap3d
    c = poly_ll.centroid
    ring = [pymap3d.geodetic2enu(lat, lon, 0, c.y, c.x, 0)[:2] for lon, lat in poly_ll.exterior.coords]
    from shapely.geometry import Polygon
    e, n, _ = pymap3d.geodetic2enu(pt_ll.y, pt_ll.x, 0, c.y, c.x, 0)
    return Polygon(ring).exterior.distance(Point(e, n))


def check(d):
    errors, warnings, info = [], [], []
    water = load(os.path.join(d, 'water_area.geojson'), errors)
    outf = load(os.path.join(d, 'outfalls.geojson'), errors)
    stat = load(os.path.join(d, 'stations.geojson'), errors)
    poly = None
    if water:
        f = water['features'][0]
        if len(water['features']) != 1:
            warnings.append('water_area.geojson: more than one feature; using the first')
        if f.get('geometry', {}).get('type') != 'Polygon':
            errors.append('water_area.geojson: geometry must be a Polygon')
        else:
            poly = shape(f['geometry'])
            ring = f['geometry']['coordinates'][0]
            if ring[0] != ring[-1]:
                errors.append('water_area.geojson: ring not closed')
            if not poly.is_valid:
                errors.append(f'water_area.geojson: invalid polygon ({explain_validity(poly)})')
            if len(ring) < 4:
                errors.append('water_area.geojson: fewer than 4 ring points')
        if not f.get('properties', {}).get('reach_id'):
            errors.append('water_area.geojson: property reach_id missing')
        else:
            info.append(f"reach_id {f['properties']['reach_id']}")
    if outf:
        ids = [f.get('properties', {}).get('id') for f in outf['features']]
        if sorted(ids) != ['A', 'B', 'C']:
            errors.append(f'outfalls.geojson: need exactly ids A, B, C (got {ids})')
        for f in outf['features']:
            p = f.get('properties', {})
            if f.get('geometry', {}).get('type') != 'Point':
                errors.append(f"outfalls.geojson: {p.get('id')} is not a Point")
                continue
            if not p.get('edm_site_id'):
                errors.append(f"outfalls.geojson: {p.get('id')} missing edm_site_id")
            if p.get('bank') not in ('left', 'right'):
                errors.append(f"outfalls.geojson: {p.get('id')} bank must be left or right")
            if poly is not None and poly.is_valid:
                dm = metres_from(poly, shape(f['geometry']))
                if dm > EDGE_TOL_M:
                    errors.append(f"outfalls.geojson: {p.get('id')} is {dm:.1f} m from the water edge (> {EDGE_TOL_M} m)")
    if stat:
        kinds = []
        for f in stat['features']:
            p = f.get('properties', {})
            if f.get('geometry', {}).get('type') != 'Point':
                errors.append(f"stations.geojson: {p.get('id')} is not a Point")
            if not p.get('id'):
                errors.append('stations.geojson: a station has no id')
            if p.get('kind') not in ('wq', 'gauge'):
                errors.append(f"stations.geojson: {p.get('id')} kind must be wq or gauge")
            kinds.append(p.get('kind'))
        for k in ('wq', 'gauge'):
            if k not in kinds:
                errors.append(f'stations.geojson: no station of kind {k}')
    for opt, what in (('reach_waterbody.gml', 'CityGML WaterBody'), ('tiles/tileset.json', '3D Tiles'), ('meshes', 'COLLADA meshes')):
        if not os.path.exists(os.path.join(d, opt)):
            warnings.append(f'{opt}: not delivered yet ({what}, from FME later)')
    return errors, warnings, info


def main():
    d = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'reach')
    errors, warnings, info = check(d)
    for m in info:
        print('INFO ', m)
    for m in warnings:
        print('WARN ', m)
    for m in errors:
        print('ERROR', m)
    print('PASS' if not errors else f'FAIL ({len(errors)} errors)')
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
