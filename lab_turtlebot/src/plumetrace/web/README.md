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

- `index.html`: Top bar (reach, mode, sync, time factor), alert / incident bar, Mission, Robot, Mission events and Commands panel, map (river, plume, outfall pins A/B/C, robot, samples, real/virtual obstacles, no-go zones), Pollution and River panels, "Which outfall?" bars, alerts, CSV export, timeline scrubber, CZML replay loader, incident window.
- `pegnitz_response.js` (in git): `window.PEGNITZ_RESPONSE` with gauge and river facts, thresholds, the 5-tier escalation ladder, recommended actions, public-warning issuers and the Meldebogen report fields. Optional: without it the page uses built-in thresholds (0.3 / 0.6 / 2.0 mg/L NH₃-N, DO 6 / 4 mg/L) and shows "not loaded" in place of the ladder and actions.
- `config.js` (in git): gateway URL, `tileset_url` (Cesium 3D Tiles; loaded when not empty), and synthetic overflow events for the timeline. Keep `ionToken` empty here.
- `config.local.js` (git-ignored, optional): personal secrets such as the ion token; merged over `config.js`.
- `schema.json`: JSON Schema of every gateway message, plus `definitions/command` for client commands.
- `data/*.geojson`: copies of `data/reach/` written by `tools/reach_build.py`.

## Dashboard features

| Area | What it shows / does |
| --- | --- |
| Robot | 56 px billboard (never below ~40 px, never hidden by terrain or buildings), "TurtleBot3" label, pulsing 5–11 m ground ring. Left panel: **Find robot** (fly to it), **Follow robot** (camera tracks it). |
| Plume | Legend radio: **Estimated plume** (`plume_points`, default), **True plume (simulation)** (`plume_true`), **Off**. Points below background + 0.02 mg/L are skipped (background from `hello.scenario.background_nh3_n_mg_l`, else 0.05). Point size and colour scale with concentration; the colour ramp has ticks at 0.05, 0.3, 0.6 (alert), 2 and 3 mg/L. **3D columns**: the up to 300 highest cells as vertical bars, height proportional to concentration. Points and bars are pooled primitives, reused on every update. |
| Pollution (right, top) | Last NH₃-N and DO with status chips (Normal / Elevated / ALERT / SEVERE; DO OK / low / CRITICAL) from `PEGNITZ_RESPONSE.thresholds`, sparkline of the last 60 samples with the alert line, background, max seen and where. Samples on the map: 12 px, colour-coded, red outline above Normal, status in the info box. |
| River · gauge | Gauge 24225000 Lederersteg (MQ, MNQ, NQ, MHQ, warning levels, link), scenario flow `hello.scenario.q_m3s`, mean velocity v = Q / (width × depth) with width and depth from `data/water_area.geojson` (22.61 m, 1.0 m), ETA to the Regnitz confluence = 6.47 km / v (falls back to MQ without a scenario), bathing note, sources. |
| Mission events | Last 10 `event` messages (`goal_sent`, `goal_result`, `sample`, `hold`, `resume`, `done`, `abort`). On `done` the outfall in `data.map_label` is marked "SOURCE CONFIRMED" with a pulse on the map and added to the incident. |
| Incident | Opens on the first `alert`, or when a sample reaches `thresholds.nh3_n_alert`. Window "POLLUTANT DETECTED — Pegnitz, Nürnberg": summary (id, time, location, max NH₃-N, min DO, likely outfall, ETA), recommended actions as a checklist (each tick is logged with a timestamp), the 5-tier escalation ladder ("Escalate to next level" only records the tier as notified, with time; nothing is sent; unverified numbers are flagged "verify number"), "Request public warning" (German + English draft addressed to `public_warning.issuers`, warning circle on the map with a 100–2000 m slider, affected places within the radius, copy button, disclaimer). Severity becomes SEVERE at `nh3_n_severe` or below `do_critical`. Minimise to the red incident bar and reopen from there or from the Pollution panel. Incident log of alerts, escalations, actions, warning drafts and mission events; export as JSON, or as a Meldebogen report (CSV or text) built from `report_fields`. |

### Layout (minimal view) and back-to-back runs (2026-10-14)

- Always visible: map, header (reach, mission state, link, one sync dot with per-stream tooltip), Mission card (run number, scenario and elapsed time, samples, battery, live progress line such as "driving to stop (x, y)", "sampling (dwell)", "returning home", "home ✓", "done: outfall B 98 %", Find / Follow robot), Pollution card (NH₃-N and DO with chips, small sparkline, max and where, background) and the "Which outfall?" bars. Everything else is in collapsible sections (closed by default, open state kept in `localStorage`): Mission events, Commands, Sync per stream (incl. mode and time factor), Runs, Alerts, River · gauge, Samples · export · replay. The legend is one small collapsible card on the map. The incident window has tabs: Actions, Escalation (current and next tier expanded), Public warning, Report & log; minimised it is a slim red bar.
- Runs (several missions on one page, e.g. `tools/run_abc.py` started again): a new run starts when `mission.scenario` changes from the previous non-empty value, or when a sample arrives with `seq` ≤ the last seq of the current run after that run ended (mission DONE / ABORTED / IDLE, or a fresh `hello` = gateway restart). The finished run is archived (scenario, times, samples, max NH₃-N and place, min DO, `done` result with localised yes/no, return-home status, incident id / severity / notified tiers, incident record, log, events, samples); samples, map points, sparkline, timeline, max, source marker, track, plume layers, posterior and the incident are cleared, and the next alert opens a fresh incident. Samples are de-duplicated per run (same seq and t = relay replay, dropped). Runs table: Run # | Scenario | Samples | Max | Result | Status (running / localised ✓ / best guess / aborted); **Export all runs (JSON)**.
- `battery {t, voltage, percentage}`: Mission · Battery shows `V (%)`, warning colour below 11.3 V, red below 11.0 V with one `battery_low` event (re-armed above 11.5 V after a swap).
- Incident report (demo pre-fill): reporter "PlumeTrace TurtleBot3 (autonomous survey, demo)", water body "Pegnitz, Nürnberg (Lederersteg reach, 1:100 lab model)", observation from NH₃-N / background / DO, suspected source (posterior, then `done`), quantity from `posterior.map_strength`. Fields stay editable; an edited field is no longer auto-updated.

All text that arrives from the network is escaped before it is inserted as HTML.

## Gateway messages used

`hello` (incl. optional `scenario {id, q_m3s, background_nh3_n_mg_l, background_do_mg_l, time_factor}`), `battery`, `pose`, `sample`, `posterior`, `plume_points`, `plume_true` (same grid as `plume_points`, simulated ground truth), `alert`, `event {t, kind, data}`, `obstacles`, `sync`, `mission`, `ack`. Unknown types are ignored; a handler error is logged to the console and does not stop the stream.

## Commands (all others are rejected)

`abort`, `return_home`, `add_nogo` (`polygon` of `[lat, lon]`), `remove_nogo` (`id`), `add_obstacle` (`polygon` or `center` + `size_m`, `mode` REROUTE|STOP), `remove_obstacle` (`id`).
