#!/usr/bin/env python3
"""Build the reach handoff files from Bavarian open data, without FME/ArcGIS.

Sources (all open, CC BY 4.0, no registration):
  water, park, paths : ALKIS Tatsaechliche Nutzung (Bayerische Vermessungsverwaltung), per district
  terrain            : DGM1, 1 m GeoTIFF tiles, EPSG:25832, heights DHHN2016
  buildings          : LoD2 CityGML 1.0 tiles (2 km), EPSG:25832
  gauge              : LfU gauge shapefile; values from the Gewaesserkundlicher Dienst (GKD)
  water quality      : GKD chemistry station

    python3 tools/reach_from_open_data.py [pegnitz_nuernberg] [out_dir]

Writes water_area.geojson, outfalls.geojson, stations.geojson, context.geojson, gis/ (clips), source/
(raw tiles incl. DOM20 and DOP20), timeseries/, SOURCES.md and FME_README.md to out_dir (default data/reach_candidates/<reach>/).
data/reach/ is not touched: copy the three handoff files there and run tools/swap_reach.sh.
Downloads are cached in ~/.cache/plumetrace.
"""
import csv
import html
import io
import json
import math
import os
import re
import shutil
import struct
import sys
import urllib.request
import zipfile

import numpy as np
import pymap3d
import shapely
from pyproj import Transformer
from shapely.geometry import LineString, MultiPolygon, Point, Polygon, mapping
from shapely.ops import unary_union

BVV = 'https://download1.bayernwolke.de/a/'
PEGEL_URL = 'https://www.lfu.bayern.de/gdi/dls/daten/pegel/pegel_epsg25832_shp.zip'
CACHE = os.path.expanduser('~/.cache/plumetrace')
UA = {'User-Agent': 'plumetrace/reach_from_open_data'}

# A reach is the water polygon cut by a rectangle along `axis` (upstream point, downstream point,
# ETRS89 / UTM 32N metres). The upstream point becomes the reach origin (arena 0, 1).
REACHES = {
    'pegnitz_nuernberg': dict(
        reach_id='PEGNITZ-LEDERERSTEG',
        name='Pegnitz at Nürnberg Lederersteg',
        water_name='Pegnitz',
        district='09564',                       # Stadt Nürnberg (ALKIS land use package)
        axis=((648950.0, 5480127.5), (648650.0, 5480187.5)),
        length_m=300.0,
        half_width_m=(30.0, 30.0),              # left, right of the axis
        depth_m=1.0,                            # assumed: no open bed survey
        gauge='24225000',                       # GKD Nürnberg Lederersteg (discharge, water level)
        wq=dict(id='17651', name='Nürnberg, Lederersteg',
                url='https://www.gkd.bayern.de/en/rivers/chemistry/regnitz/nuernberg-lederersteg-17651'),
        # Mission hypotheses: metres along the axis, on the robot (left) bank. Positions are synthetic
        # (the active outfall is invented so the truth is known).
        outfalls=[('A', 60.0), ('B', 140.0), ('C', 220.0)],
        gis_margin_m=150.0,
    ),
}


def cached(name, url):
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, name)
    if not os.path.exists(path) and url:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=900) as r, \
                open(path + '.part', 'wb') as f:
            while True:
                chunk = r.read(1 << 20)
                if not chunk:
                    break
                f.write(chunk)
        os.replace(path + '.part', path)
    return path


def read_dbf(data):
    n, hl, rl = struct.unpack('<IHH', data[4:12])
    fields, o = [], 32
    while data[o] != 0x0D:
        fields.append((data[o:o + 11].split(b'\0')[0].decode(), data[o + 16]))
        o += 32
    rows = []
    for i in range(n):
        r, p, d = data[hl + i * rl + 1:hl + (i + 1) * rl], 0, {}
        for name, ln in fields:
            d[name] = r[p:p + ln].decode('utf-8', 'replace').strip()
            p += ln
        rows.append(d)
    return rows


def read_shp(data, bbox=None):
    """Minimal ESRI shapefile reader -> list of (record index, shapely geometry or None)."""
    out, o, i = [], 100, 0
    while o < len(data):
        _, n_words = struct.unpack('>ii', data[o:o + 8])
        c = data[o + 8:o + 8 + n_words * 2]
        o += 8 + n_words * 2
        i += 1
        kind = struct.unpack('<i', c[:4])[0]
        if kind in (1, 11, 21):
            out.append((i - 1, Point(struct.unpack('<2d', c[4:20]))))
            continue
        if kind not in (5, 15):
            continue
        x0, y0, x1, y1 = struct.unpack('<4d', c[4:36])
        if bbox and (x1 < bbox[0] or x0 > bbox[2] or y1 < bbox[1] or y0 > bbox[3]):
            continue
        n_parts, n_pts = struct.unpack('<ii', c[36:44])
        parts = list(struct.unpack(f'<{n_parts}i', c[44:44 + 4 * n_parts])) + [n_pts]
        pts = np.frombuffer(c, dtype='<f8', count=2 * n_pts, offset=44 + 4 * n_parts).reshape(-1, 2)
        rings = [pts[parts[k]:parts[k + 1]] for k in range(n_parts)]
        area = [0.5 * np.sum(r[:-1, 0] * r[1:, 1] - r[1:, 0] * r[:-1, 1]) for r in rings]
        outer = [r for r, a in zip(rings, area) if a < 0] or rings  # outer rings are clockwise
        holes = [r for r, a in zip(rings, area) if a >= 0] if len(outer) < len(rings) else []
        polys = [Polygon(r, [h for h in holes if Polygon(r).contains(Point(h[0]))]) for r in outer]
        out.append((i - 1, polys[0] if len(polys) == 1 else MultiPolygon(polys)))
    return out


def dgm_mosaic(box):
    """1 m DGM over box (integer metres) from the 1 km tiles; row 0 is the north edge."""
    from PIL import Image
    e0, n0, e1, n1 = box
    out = np.full((n1 - n0, e1 - e0), np.nan, dtype=np.float32)
    for ke in range(e0 // 1000, (e1 - 1) // 1000 + 1):
        for kn in range(n0 // 1000, (n1 - 1) // 1000 + 1):
            t = np.array(Image.open(cached(f'dgm1_{ke}_{kn}.tif', f'{BVV}dgm/dgm1/{ke}_{kn}.tif')), dtype=np.float32)
            te, tn = ke * 1000, (kn + 1) * 1000   # tile west and north edges
            c0, c1, r0, r1 = max(e0, te), min(e1, te + 1000), max(n0, tn - 1000), min(n1, tn)
            out[n1 - r1:n1 - r0, c0 - e0:c1 - e0] = t[tn - r1:tn - r0, c0 - te:c1 - te]
    return out


def write_geotiff(path, a, e0, n1):
    from PIL import Image, TiffImagePlugin
    info = TiffImagePlugin.ImageFileDirectory_v2()
    info[33550], info.tagtype[33550] = (1.0, 1.0, 0.0), 12
    info[33922], info.tagtype[33922] = (0.0, 0.0, 0.0, float(e0), float(n1), 0.0), 12
    info[34735], info.tagtype[34735] = (1, 1, 0, 3, 1024, 0, 1, 1, 1025, 0, 1, 1, 3072, 0, 1, 25832), 3
    Image.fromarray(a.astype(np.float32)).save(path, tiffinfo=info)


def clip_citygml(src, dst, area):
    """Copy the cityObjectMembers whose first coordinate lies in `area` (a shapely polygon)."""
    with open(src, encoding='utf-8') as f:
        text = f.read()
    m = re.search(r'<(\w+:)?cityObjectMember', text)
    head, tag = text[:m.start()], (m.group(1) or '') + 'cityObjectMember'
    tail = text[text.rfind(f'</{tag}>') + len(tag) + 3:]
    keep = []
    for mem in re.finditer(rf'<{tag}[ >].*?</{tag}>', text, flags=re.S):
        p = re.search(r'<gml:posList[^>]*>\s*([-\d.]+)\s+([-\d.]+)', mem.group(0))
        if p and area.contains(Point(float(p.group(1)), float(p.group(2)))):
            keep.append(mem.group(0))
    with open(dst, 'w', encoding='utf-8') as f:
        f.write(head + '\n'.join(keep) + tail)
    return len(keep)


def gkd_table(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (plumetrace)'})
    with urllib.request.urlopen(req, timeout=120) as r:
        page = r.read().decode('utf-8', 'ignore')
    rows = [[html.unescape(re.sub(r'<[^>]+>', '', td)).strip() for td in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', tr, flags=re.S)]
            for tr in re.findall(r'<tr[^>]*>(.*?)</tr>', page, flags=re.S)]
    return [r for r in rows if r]


def gkd_series(spec, gauge_row, out):
    """Last week of 15-min discharge and water level, and the chemistry record, as CSV."""
    os.makedirs(out, exist_ok=True)
    base = gauge_row['link_link'].replace('/de/fluesse/wasserstand/', '/en/rivers/{}/').rsplit('/', 1)[0]
    jobs = {'discharge_15min.csv': base.format('discharge') + '/current-values/table',
            'waterlevel_15min.csv': base.format('waterlevel') + '/current-values/table',
            'chemistry.csv': spec['wq']['url'] + '/total-period/table'}
    done = {}
    for name, url in jobs.items():
        try:
            rows = gkd_table(url)
        except OSError as e:
            done[name] = f'not fetched ({e})'
            continue
        with open(os.path.join(out, name), 'w', newline='') as f:
            csv.writer(f).writerows(rows)
        done[name] = f'{len(rows) - 1} rows, {url}'
    return done


def build(key, out_dir):
    spec = REACHES[key]
    to_ll = Transformer.from_crs(25832, 4326, always_xy=True)
    up, dn = np.array(spec['axis'][0]), np.array(spec['axis'][1])
    u = (dn - up) / np.linalg.norm(dn - up)   # downstream unit vector
    v = np.array([-u[1], u[0]])               # to the left bank
    L, (hl, hr), m = spec['length_m'], spec['half_width_m'], spec['gis_margin_m']

    def along_cross(p):
        d = np.asarray(p, dtype=float) - up
        return d @ u, d @ v

    def utm(a, c):
        return up + a * u + c * v

    def ll(x, y):
        lon, lat = to_ll.transform(x, y)
        return [round(lon, 8), round(lat, 8)]

    area = Polygon([utm(-m, -hr - m), utm(L + m, -hr - m), utm(L + m, hl + m), utm(-m, hl + m)])
    box = (math.floor(area.bounds[0]), math.floor(area.bounds[1]), math.ceil(area.bounds[2]), math.ceil(area.bounds[3]))

    # --- ALKIS land use: river, park, paths ---
    z = zipfile.ZipFile(cached(f"tn_{spec['district']}.zip", f"{BVV}tn/lkr/tn_{spec['district']}.zip"))
    rows = read_dbf(z.read('Nutzung.dbf'))
    use = [(rows[i], g) for i, g in read_shp(z.read('Nutzung.shp'), box)]
    rect = Polygon([utm(0, -hr), utm(L, -hr), utm(L, hl), utm(0, hl)])
    river = unary_union([g for r, g in use if r['nutzart'] == 'Fließgewässer' and r['name'] == spec['water_name']])
    cut = river.intersection(rect)
    water = max(list(cut.geoms) if hasattr(cut, 'geoms') else [cut], key=lambda p: p.area)
    water = Polygon(water.exterior)
    ring = np.array(water.exterior.coords)
    a_ring, c_ring = along_cross(ring)
    width = water.area / L

    # --- terrain: water level = median DGM over the water polygon ---
    dgm = dgm_mosaic(box)
    E, N = np.meshgrid(box[0] + 0.5 + np.arange(dgm.shape[1]), box[3] - 0.5 - np.arange(dgm.shape[0]))
    level = float(np.nanmedian(dgm[shapely.contains_xy(water, E, N)]))

    # --- frame: ENU at the upstream axis point; theta turns arena +x onto the flow direction ---
    lon0, lat0 = to_ll.transform(*up)
    lon1, lat1 = to_ll.transform(*dn)
    e, n, _ = pymap3d.geodetic2enu(lat1, lon1, 0, lat0, lon0, 0)
    theta = math.atan2(n, e)

    crs = {'type': 'name', 'properties': {'name': 'urn:ogc:def:crs:OGC:1.3:CRS84'}}

    def fc(features):
        return {'type': 'FeatureCollection', 'crs': crs, 'features': features}

    def feat(props, geom):
        return {'type': 'Feature', 'properties': props, 'geometry': geom}

    def geo(g):
        gj = mapping(g)
        conv = (lambda r: [ll(x, y) for x, y in r])
        if gj['type'] == 'Point':
            return {'type': 'Point', 'coordinates': ll(*gj['coordinates'])}
        if gj['type'] == 'Polygon':
            return {'type': 'Polygon', 'coordinates': [conv(r) for r in gj['coordinates']]}
        return {'type': gj['type'], 'coordinates': [[conv(r) for r in p] for p in gj['coordinates']]}

    water_fc = fc([feat({
        'reach_id': spec['reach_id'], 'name': spec['name'],
        'origin_lat': round(lat0, 8), 'origin_lon': round(lon0, 8), 'origin_h': round(level, 2),
        'theta_rad': round(theta, 6), 'width_m': round(width, 2), 'depth_m': spec['depth_m'],
        'depth_source': 'assumed', 'water_level_m': round(level, 2),
        'water_level_source': 'DGM1 (DHHN2016), median over the water polygon',
        'flow_bearing_deg': round((90 - math.degrees(theta)) % 360, 1), 'length_m': L,
        'axis_utm32': [list(spec['axis'][0]), list(spec['axis'][1])],
        'source': 'ALKIS Tatsaechliche Nutzung, Fliessgewaesser (CC BY 4.0), cut at the reach ends'},
        geo(water))])

    # --- stations ---
    pz = zipfile.ZipFile(cached('pegel_epsg25832_shp.zip', PEGEL_URL))
    base = next(nm[:-4] for nm in pz.namelist() if nm.endswith('.shp'))
    pegel = [(r, g) for r, (_, g) in zip(read_dbf(pz.read(base + '.dbf')), read_shp(pz.read(base + '.shp')))]
    gr, gp = next((r, g) for r, g in pegel if r['stationsnu'] == spec['gauge'])
    stations_fc = fc([
        feat({'id': spec['wq']['id'], 'kind': 'wq', 'name': spec['wq']['name'], 'operator': 'LfU Bayern (GKD)',
              'url': spec['wq']['url'], 'determinands': 'Ammonium-N, dissolved oxygen and others (grab samples)',
              'position': 'at the gauge footbridge (station page gives no coordinates)',
              'along_m': round(float(along_cross((gp.x, gp.y))[0]), 1)}, geo(gp)),
        feat({'id': spec['gauge'], 'kind': 'gauge', 'name': gr['stationsna'], 'river': gr['gewaesser'],
              'operator': gr['betreiber'], 'bank': 'left' if gr['lage_am_ge'] == 'Links' else 'right',
              'river_km': gr['flusskilom'], 'catchment_km2': gr['einzugsgeb'], 'gauge_zero_m': float(gr['wert']),
              'url': gr['link_link'], 'along_m': round(float(along_cross((gp.x, gp.y))[0]), 1)}, geo(gp))])

    # --- outfall hypotheses on the left bank edge ---
    left = LineString(ring[c_ring > 0][np.argsort(a_ring[c_ring > 0])])
    feats = []
    for oid, a in spec['outfalls']:
        hit = left.intersection(LineString([utm(a, -hr), utm(a, hl)]))
        p = max(hit.geoms, key=lambda g: along_cross((g.x, g.y))[1]) if hasattr(hit, 'geoms') else hit
        feats.append(feat({'id': oid, 'edm_site_id': f'SYNTHETIC-{oid}', 'bank': 'left', 'along_m': a,
                           'position': 'synthetic'}, geo(p)))
    outfalls_fc = fc(feats)

    # --- context: real land use around the reach ---
    ctx = []
    for r, g in use:
        kind = ('water' if r['nutzart'] in ('Fließgewässer', 'Stehendes Gewässer') else
                'path' if r['nutzart'] == 'Weg' else 'road' if r['nutzart'] == 'Straßenverkehr' else
                'park' if r['bez'] in ('Park', 'Grünanlage') else None)
        g = g.intersection(area) if kind else None
        if g is None or g.is_empty or g.geom_type not in ('Polygon', 'MultiPolygon'):
            continue
        props = {'kind': kind, 'alkis_id': r['gml_id'], 'use': r['nutzart'], 'source': 'ALKIS Tatsaechliche Nutzung'}
        if r['name']:
            props['name'] = r['name']
        if kind in ('path', 'park'):
            props['bank'] = 'left' if along_cross((g.centroid.x, g.centroid.y))[1] > 0 else 'right'
        ctx.append(feat(props, geo(g)))
    context_fc = fc(ctx)

    # --- write ---
    os.makedirs(os.path.join(out_dir, 'gis'), exist_ok=True)
    for name, obj in (('water_area', water_fc), ('outfalls', outfalls_fc), ('stations', stations_fc),
                      ('context', context_fc)):
        with open(os.path.join(out_dir, name + '.geojson'), 'w') as f:
            json.dump(obj, f, indent=1, ensure_ascii=False)
            f.write('\n')
    write_geotiff(os.path.join(out_dir, 'gis', 'dgm1.tif'), dgm, box[0], box[3])
    tiles = sorted({(int(x) // 2000 * 2, int(y) // 2000 * 2) for x, y in area.exterior.coords})
    n_bldg, raw = 0, [cached(f"tn_{spec['district']}.zip", ''), cached('pegel_epsg25832_shp.zip', '')]
    for te, tn in tiles:
        src = cached(f'lod2_{te}_{tn}.gml', f'{BVV}lod2/citygml/{te}_{tn}.gml')
        raw.append(src)
        n_bldg += clip_citygml(src, os.path.join(out_dir, 'gis', f'buildings_lod2_{te}_{tn}.gml'), area)
    for ke in range(box[0] // 1000, (box[2] - 1) // 1000 + 1):
        for kn in range(box[1] // 1000, (box[3] - 1) // 1000 + 1):
            raw.append(cached(f'dgm1_{ke}_{kn}.tif', f'{BVV}dgm/dgm1/{ke}_{kn}.tif'))
            raw.append(cached(f'dom20_32{ke}_{kn}.tif', f'{BVV}dom20/DOM/32{ke}_{kn}_20_DOM.tif'))
            raw.append(cached(f'dop20_32{ke}_{kn}.tif', f'{BVV}dop20/data/32{ke}_{kn}.tif'))
    os.makedirs(os.path.join(out_dir, 'source'), exist_ok=True)
    for path in raw:   # hard links to the cache where possible: the raw tiles are large
        dst = os.path.join(out_dir, 'source', os.path.basename(path))
        if not os.path.exists(dst):
            try:
                os.link(path, dst)
            except OSError:
                shutil.copyfile(path, dst)
    series = gkd_series(spec, gr, os.path.join(out_dir, 'timeseries'))
    kinds = {}
    for c in ctx:
        kinds[c['properties']['kind']] = kinds.get(c['properties']['kind'], 0) + 1
    with open(os.path.join(out_dir, 'SOURCES.md'), 'w') as f:
        f.write(f"""# {spec['name']}: data sources

Generated by `tools/reach_from_open_data.py {key}`. Source CRS is ETRS89 / UTM 32N (EPSG:25832); GeoJSON is WGS84.
Reach axis (UTM32): {spec['axis'][0]} to {spec['axis'][1]}, {L:.0f} m, flowing {(90 - math.degrees(theta)) % 360:.0f}° from north. `gis/` covers {box}.

| File | Content | Source | Licence |
| --- | --- | --- | --- |
| `water_area.geojson` | Water surface cut at both reach ends | ALKIS Tatsächliche Nutzung, `Fließgewässer` {spec['water_name']}, district {spec['district']} | CC BY 4.0, Bayerische Vermessungsverwaltung |
| `context.geojson` | {', '.join(f'{v} {k}' for k, v in sorted(kinds.items()))} polygons | ALKIS Tatsächliche Nutzung | CC BY 4.0, Bayerische Vermessungsverwaltung |
| `gis/dgm1.tif` | Terrain, 1 m, m DHHN2016 | DGM1 tiles | CC BY 4.0, Bayerische Vermessungsverwaltung |
| `gis/buildings_lod2_*.gml` | {n_bldg} LoD2 buildings, CityGML 1.0, unchanged objects | LoD2 tiles {tiles} | CC BY 4.0, Bayerische Vermessungsverwaltung |
| `stations.geojson` | Gauge {spec['gauge']} ({gr['stationsna']}), chemistry station {spec['wq']['id']} | LfU gauge shapefile; Gewässerkundlicher Dienst Bayern | CC BY 4.0, Bayerisches Landesamt für Umwelt, www.gkd.bayern.de |
| `outfalls.geojson` | Mission hypotheses A, B, C on the left bank | Synthetic positions | n/a |

Real: water outline, terrain, water level ({level:.2f} m from DGM1), buildings, park, paths, roads, gauge position.
Assumed: depth ({spec['depth_m']} m); the chemistry station is placed at the gauge footbridge.
Synthetic: the three outfall positions (the active outfall is invented so the true answer is known).
""")
        f.write('\n## Raw tiles and time series\n\n`source/` holds the unmodified official files (git-ignored, large): '
                + ', '.join(f'`{os.path.basename(p)}`' for p in raw) + '.\n\n`timeseries/`: '
                + '; '.join(f'`{k}` ({v})' for k, v in series.items()) + '.\n')
    x0, y0 = spec['axis'][0]
    with open(os.path.join(out_dir, 'FME_README.md'), 'w') as f:
        f.write(f"""# FME brief: {spec['name']}

Inputs are in this folder; all source data is EPSG:25832 (ETRS89 / UTM 32N), heights DHHN2016.

| Input | Use in FME |
| --- | --- |
| `water_area.geojson` (WGS84) | The reach water surface, already cut at both ends. Reproject to EPSG:25832 |
| `source/dgm1_*.tif` (or the clip `gis/dgm1.tif`) | Terrain; bank heights for the bank meshes |
| `source/dom20_*.tif`, `source/dop20_*.tif` | 20 cm surface model and orthophoto: tree and bridge heights, textures |
| `source/lod2_*.gml` (or the clips `gis/buildings_lod2_*.gml`) | LoD2 buildings, CityGML 1.0, ready for 3DCityDB |
| `source/tn_{spec['district']}.zip` (or `context.geojson`) | ALKIS land use: river, park, paths, roads |
| `stations.geojson`, `outfalls.geojson` | Generic city objects: gauge {spec['gauge']}, chemistry station {spec['wq']['id']}, hypotheses A, B, C |

Reach parameters:

| Parameter | Value |
| --- | --- |
| Reach id | `{spec['reach_id']}` |
| Axis (upstream to downstream, UTM32) | {spec['axis'][0]} to {spec['axis'][1]} |
| Reach origin (upstream axis point) | E {x0}, N {y0}; lat {lat0:.8f}, lon {lon0:.8f} |
| Water level (WaterSurface height) | {level:.2f} m (median DGM1 over the water polygon) |
| Assumed depth (WaterGroundSurface = level - depth) | {spec['depth_m']} m |
| Mean width | {width:.1f} m |
| theta (arena +x to local east, counter-clockwise) | {theta:.6f} rad = {math.degrees(theta):.2f}° |

Outputs to put in `data/reach/`:

1. `reach_waterbody.gml`: CityGML (EPSG:25832) WaterBody with WaterSurface at the water level, WaterGroundSurface at
   level minus depth, WaterClosureSurface at both cut ends; gauge, chemistry station and outfalls as generic city
   objects. Use CityGML 1.0 or 2.0 so it loads into 3DCityDB next to the LoD2 buildings.
2. `tiles/tileset.json`: Cesium 3D Tiles of the WaterBody plus the LoD2 buildings.
3. `meshes/*.dae`: COLLADA in local metres from the reach origin, x east, y north, z up minus the water level
   (subtract E {x0}, N {y0}, {level:.2f}). The build scales them by 0.01 and rotates by theta.
""")
    return dict(area=water.area, width=width, level=level, theta=theta, kinds=kinds, box=box, buildings=n_bldg)


if __name__ == '__main__':
    key = sys.argv[1] if len(sys.argv) > 1 else 'pegnitz_nuernberg'
    repo = os.environ.get('PLUMETRACE_REPO') or os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(repo, 'data', 'reach_candidates', key)
    r = build(key, out)
    print(f"{key}: water {r['area']:.0f} m2, mean width {r['width']:.1f} m, level {r['level']:.2f} m, "
          f"theta {math.degrees(r['theta']):.1f} deg, {r['buildings']} LoD2 buildings, context {r['kinds']} -> {out}")
