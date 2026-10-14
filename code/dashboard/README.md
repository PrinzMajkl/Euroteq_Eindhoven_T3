# PlumeTrace Authority Dashboard

A browser dashboard for water authorities. It shows what the robot finds in real time (**See**), lets an official send inspection requests (**Ask**), and produces a CSV and a plain-language incident report (**Get**).

It runs on `localhost` next to ROS 2. `gateway_node.py` (one folder up) is the bridge between ROS 2 and the browser.

```
TurtleBot3 ──ROS 2──▶ digital_twin_pollution_v4.py, safe_navigation_pollution_v3.py
                          │ /digital_twin_state, /robot_status, /pollution, ...
                          ▼
                    gateway_node.py ── ws://localhost:8765 ──▶ browser (http://localhost:8080)
                          ▲                                        │
                          └──────── requests (/dashboard_request) ◀┘
```

## Run it

**Preview with no robot (any laptop):**

```bash
pip install websockets
python3 gateway_node.py            # from the code/ folder
# open http://localhost:8080  ->  Replay  ->  press play
```

**Live with the robot (lab laptop, same ROS_DOMAIN_ID as the robot):**

```bash
# 1. robot bringup + Nav2 as usual
# 2. python3 safe_navigation_pollution_v3.py
# 3. python3 digital_twin_pollution_v4.py
python3 gateway_node.py
# open http://localhost:8080/?live   (or click "Live robot")
```

Every live run is recorded to `dashboard/runs/run_<time>.jsonl`. To replay it later (for example as a backup on demo day), choose **Replay → Load run**.

## Requests: what actually happens

| Request | Published on | Effect today |
|---|---|---|
| Stop robot | `/dashboard_request` and `/navigation_decision` = `STOP` | **Works now.** safe_navigation stops and cancels Nav2. |
| Inspect a spot / an outfall | `/dashboard_request` (JSON) | Logged for the twin. The twin does not act on it yet. |
| Same, with `python3 gateway_node.py --direct` | also `/twin_waypoint` | safe_navigation drives there with Nav2. This bypasses the twin, so use it for testing only. It works once per run, because safe_navigation stops after one goal. |

**To do for the twin owner:** subscribe to `/dashboard_request` in `digital_twin_pollution_v4.py` and turn requests into waypoints. Example message:

```json
{"id": "R-001", "type": "outfall", "outfall": "B", "x": 4.7, "y": 4.8, "frame_id": "odom",
 "check": "both", "priority": "urgent", "reason": "citizen complaint", "requested_by": "River authority dashboard"}
```

## Settings: `js/config.js`

- `ANCHOR`, `HEADING_DEG`: where the arena sits on the Pegnitz. It is currently set to Wöhrder Wiese, with the robot driving upstream (east). Shift+click the map to read coordinates.
- `SCALE_ALONG`, `SCALE_ACROSS`: metres of river per metre of arena, chosen so the wooden walls line up with the banks.
- `ARENA`: wall positions in odom metres. The robot's start point is (0, 0).
- `OUTFALLS`: put A, B and C where your markers stand in the lab, in odom metres.
- `CESIUM_ION_TOKEN`: leave it empty for a flat OpenStreetMap map. With a free token from ion.cesium.com you get 3D terrain and buildings. Upload Bavarian DGM1 terrain or LoD2 buildings to ion and set `TERRAIN_ASSET_ID` / `BUILDINGS_ASSET_ID`.

## Files

- `index.html`, `css/style.css`: layout and brand styling (from `presentation/brand_style_guide.md`)
- `js/app.js`: wiring
- `js/data.js`: live WebSocket and replay
- `js/store.js`: mission state and alerts
- `js/map.js`: Cesium map
- `js/panels.js`: status, tiles, charts, findings
- `js/requests.js`: request panel
- `js/report.js`: incident report and CSV
- `js/geo.js`: arena to Pegnitz coordinates
- `data/demo_run.jsonl`: synthetic demo mission (`tools/make_demo_run.py` regenerates it)

Needs an internet connection for CesiumJS, Chart.js and map tiles (loaded from CDNs). Readings are synthetic (`SYNTHETIC_POSITION_BASED`), and the "likely source" is the outfall nearest the highest reading.
