# PlumeTrace city view

Static CesiumJS page. It talks only to the PlumeTrace gateway over WebSocket; it never touches ROS 2 DDS.

## Run

```bash
source ~/Documents/turtlebot3_ws/plumetrace_starter/plumetrace/config/env.sh
cd $PLUMETRACE_REPO/web && python3 -m http.server 8080
```

Then open http://localhost:8080 while a mission launch (with the gateway) is running. The gateway listens on `ws://localhost:8765`.

## Pinned versions

| Library | Version | Source |
| --- | --- | --- |
| CesiumJS | **1.146** (latest 1.x on npm at build time, 2026-10-07: `cesium@1.146.0`) | `https://cesium.com/downloads/cesiumjs/releases/1.146/Build/Cesium/` |

Imagery: OpenStreetMap tiles (`tile.openstreetmap.org`); base-layer picker and geocoder are disabled. Without a Cesium ion token: ellipsoid terrain and no ion requests. With a token in the git-ignored `config.local.js` (`window.PLUMETRACE_CONFIG_LOCAL = { ionToken: '...' }`): Cesium World Terrain + OSM Buildings.

## Files

- `index.html`: Top bar (reach, mode, sync, time factor), alert banner, Mission and Commands panel, map (river, plume, outfall pins A/B/C, robot, samples, real/virtual obstacles, no-go zones), "Which outfall?" bars, alerts, CSV export, timeline scrubber, CZML replay loader.
- `config.js` (in git): gateway URL, `tileset_url` (Cesium 3D Tiles; loaded when not empty), and synthetic overflow events for the timeline. Keep `ionToken` empty here.
- `config.local.js` (git-ignored, optional): personal secrets such as the ion token; merged over `config.js`.
- `schema.json`: JSON Schema of every gateway message, plus `definitions/command` for client commands.
- `data/*.geojson`: copies of `data/reach/` written by `tools/reach_build.py`.

## Commands (all others are rejected)

`abort`, `return_home`, `add_nogo` (`polygon` of `[lat, lon]`), `remove_nogo` (`id`), `add_obstacle` (`polygon` or `center` + `size_m`, `mode` REROUTE|STOP), `remove_obstacle` (`id`).
