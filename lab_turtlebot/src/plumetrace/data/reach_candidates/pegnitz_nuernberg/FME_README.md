# FME brief: Pegnitz at Nürnberg Lederersteg

Inputs are in this folder; all source data is EPSG:25832 (ETRS89 / UTM 32N), heights DHHN2016.

| Input | Use in FME |
| --- | --- |
| `water_area.geojson` (WGS84) | The reach water surface, already cut at both ends. Reproject to EPSG:25832 |
| `source/dgm1_*.tif` (or the clip `gis/dgm1.tif`) | Terrain; bank heights for the bank meshes |
| `source/dom20_*.tif`, `source/dop20_*.tif` | 20 cm surface model and orthophoto: tree and bridge heights, textures |
| `source/lod2_*.gml` (or the clips `gis/buildings_lod2_*.gml`) | LoD2 buildings, CityGML 1.0, ready for 3DCityDB |
| `source/tn_09564.zip` (or `context.geojson`) | ALKIS land use: river, park, paths, roads |
| `stations.geojson`, `outfalls.geojson` | Generic city objects: gauge 24225000, chemistry station 17651, hypotheses A, B, C |

Reach parameters:

| Parameter | Value |
| --- | --- |
| Reach id | `PEGNITZ-LEDERERSTEG` |
| Axis (upstream to downstream, UTM32) | (648950.0, 5480127.5) to (648650.0, 5480187.5) |
| Reach origin (upstream axis point) | E 648950.0, N 5480127.5; lat 49.45553066, lon 11.05531111 |
| Water level (WaterSurface height) | 290.65 m (median DGM1 over the water polygon) |
| Assumed depth (WaterGroundSurface = level - depth) | 1.0 m |
| Mean width | 22.6 m |
| theta (arena +x to local east, counter-clockwise) | 2.916933 rad = 167.13° |

Outputs to put in `data/reach/`:

1. `reach_waterbody.gml`: CityGML (EPSG:25832) WaterBody with WaterSurface at the water level, WaterGroundSurface at
   level minus depth, WaterClosureSurface at both cut ends; gauge, chemistry station and outfalls as generic city
   objects. Use CityGML 1.0 or 2.0 so it loads into 3DCityDB next to the LoD2 buildings.
2. `tiles/tileset.json`: Cesium 3D Tiles of the WaterBody plus the LoD2 buildings.
3. `meshes/*.dae`: COLLADA in local metres from the reach origin, x east, y north, z up minus the water level
   (subtract E 648950.0, N 5480127.5, 290.65). The build scales them by 0.01 and rotates by theta.
