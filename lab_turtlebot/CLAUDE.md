# lab_turtlebot: instructions for the agent

## Scope

- Work only in this folder (`lab_turtlebot`). It is the whole project. Do not read, copy from or refer to
  any other folder on this machine.
- Target: ROS 2 Jazzy on Ubuntu 24.04, the new Gazebo (`gz sim`, through `ros_gz_sim`), a real
  TurtleBot3 Burger. Nothing else is supported.
- Goal: (1) the simulation of the lab arena plus the Cesium dashboard runs from this repo; (2) the same
  repo, cloned on the lablaptop, drives the real TurtleBot3 and feeds the same dashboard.

## Rules

- No sudo anywhere. No apt changes. The lablaptop has no sudo for us.
- Local git only. The user pushes. Never push, never add a remote.
- `src/plumetrace/web/config.local.js` holds the user's Cesium ion token. It is in place on the development
  laptop and git-ignored. Never open, print, edit or commit it, and never paste a URL that contains the token.
- Do not edit the four ROBOTIS folders in `src/` (`DynamixelSDK`, `turtlebot3`, `turtlebot3_msgs`,
  `turtlebot3_simulations`). They are git-ignored reference copies of what the lablaptop already has
  built in `~/turtlebot3_ws`. Read them to check launch arguments, topics and parameters.
- `build/`, `install/`, `log/` in this folder were copied from the lablaptop and are git-ignored. Do not
  rely on them.
- Message definitions in `plumetrace_msgs` are frozen.
- Call the lab machine "lablaptop". It is a physical laptop, not a virtual machine.
- Say plainly what was run and what was not. Nothing here has run on Jazzy yet (see Status).
- The development laptop (where this folder lives now) has no Jazzy and no `gz sim`. Build and run in a
  Jazzy Docker container here (see Decisions), and on the lablaptop natively.

## Decisions the user has already made (2026-10-14): do not ask again

The user wants this work to run to the end without their input. These are settled:

| Topic | Decision |
| --- | --- |
| Autonomy | Work without asking. `.claude/settings.json` pre-approves shell, edits and Docker; sudo, host apt, `git push` and adding remotes stay blocked. Commit locally after each step. |
| Jazzy environment | Docker on the development laptop. You may pull an official ROS 2 Jazzy desktop image and build a local image with Nav2, `slam_toolbox`, the TurtleBot3 packages and `gz sim`. Put the Dockerfile and run script in `docker/`. Mount the repo; build inside the container, never into the host's `build/` or `install/`. |
| Graphics | NVIDIA works in containers since 2026-10-14 (toolkit installed by the user, device description in `/etc/cdi/nvidia.yaml`). Use **`--device nvidia.com/gpu=all`**: with it, `nvidia-smi` inside a container showed the GTX 1060 (driver 580.178.04, 6 GB). Do **not** use `--gpus all`: on this Docker (29.8) it fails with "AMD CDI spec not found". Docker was not restarted and the NVIDIA runtime is not registered, so `--runtime=nvidia` is not available. Checked 2026-10-14: with `NVIDIA_DRIVER_CAPABILITIES=all` gz sim renders on the GTX 1060 (OpenGL 4.6 NVIDIA) inside the Jazzy image; `docker/run.sh up` does this. The `/dev/dri` and software fallbacks (`PLUMETRACE_GFX=intel|software`) were not needed. |
| Windows | The user wants Gazebo and RViz windows open during runs (host session is Wayland with XWayland on `DISPLAY=:0`). If no display is reachable, run headless, keep logs and screenshots, and say so. |
| River placement | You decide. Keep the 300 m reach at 1:100 (3 m of river). Place it along the 4.85 m direction where a bank strip is clear of the inner boards; move the robot start if needed. Produce a top-down drawing and an updated tape guide for the user. |
| Inner boards | Stay as in the world file (they exist in the real lab). |
| Done | Scenarios A, B and C each run once in the simulated lab arena and end with a `done` event that names the correct outfall, with the dashboard receiving live data during a run. Write commands, results and dates to `src/plumetrace/docs/`. |
| When stuck | After a fair number of attempts on one problem: write the problem and what was tried to `src/plumetrace/docs/blocked.md`, take the simplest workaround, continue with the next task. Never weaken the Done check silently. |
| Dashboard | Local first, then through `tools/relay.py` (below). Do not sign up to any service or start a public tunnel; that step is the user's. |

## Confirmed facts: lablaptop (measured 2026-10-13)

| Item | Value |
| --- | --- |
| OS, ROS | Ubuntu 24.04.5, ROS 2 Jazzy, Python 3.12.3, 20 CPU threads, 15 GB RAM |
| `~/.bashrc` | sources `/opt/ros/jazzy/setup.bash`, then `~/turtlebot3_ws/install/setup.bash`, sets `ROS_DOMAIN_ID=32` |
| Nav2 | 1.3.13 (bringup, AMCL, map server, controller, planner, behaviors, BT navigator, smoother, collision monitor, regulated pure pursuit, NavFn) |
| SLAM | `slam_toolbox` 2.8.5, `cartographer_ros` 2.0.9003 |
| TurtleBot3 | `turtlebot3_*` 2.3.6, `turtlebot3_gazebo` 2.3.7, `turtlebot3_msgs` 2.4.0, built in `~/turtlebot3_ws` |
| tf2 | 0.36.22 (one release before the deadlock fix in 0.36.23; `tools/lab_tf2_overlay.sh` builds 0.36.23 locally) |
| Python libraries | present: numpy 1.26.4, scipy 1.11.4, yaml 6.0.1. Missing: shapely, pymap3d, websockets (`tools/lab_setup.sh --pip` installs them for the user) |
| Tools | pip 24.0, git 2.43, colcon; internet reaches github.com and pypi.org; no passwordless sudo |
| User, network | user `test`, address 192.168.8.115 on the robot's network |

## Confirmed facts: robot

- TurtleBot3 Burger, ROS 2 Jazzy, `ROS_DOMAIN_ID=32`, `LDS_MODEL=LDS-02`, `turtlebot3_node` 2.3.6.
- Started over ssh with `ros2 launch turtlebot3_bringup robot.launch.py`. Only this runs on the robot.
- Its bringup sets `enable_stamped_cmd_vel: true`, so `/cmd_vel` is `geometry_msgs/TwistStamped`.
  The simulated robot's bridge uses `TwistStamped` too. Nav2 defaults to plain `Twist`; our parameters
  switch it with `enable_stamped_cmd_vel` (launch argument `stamped`, default true).
- Teleop from the lablaptop works (user confirmed).
- Not yet measured: the live topic list, scan rate and range, frame names, and the clock offset between
  robot and lablaptop. `tools/lab_check.sh` records them; an earlier attempt returned nothing because it
  did not wait for discovery.

## Confirmed facts: arena

- The simulated lab arena is `src/plumetrace/plumetrace_sim/worlds/lab_arena.world`. It is the course's
  `new_world.world`, unchanged. The user confirmed from a top-down drawing that it is the lab setup.
- Outer walls: boards 0.55 m long, 0.05 m thick, 0.5 m high. Inner faces at about x = -1.0 and 2.6,
  y = -3.87 and 1.0, so about 3.6 x 4.85 m inside.
- The world origin is inside the arena. The robot spawns at (0, 0) facing +x, 1.0 m from the -x wall and
  1.0 m from the +y wall.
- Eight boards stand inside: near (-0.72, -1.73) and (-0.73, -1.92); (2.31, -0.80); (0.77, 0.67);
  (-0.75, 0.78); (2.34, -3.62); (0.97, -1.37) and (0.69, -1.04).
- All boards are non-static models (`<static>false</static>`): the simulated robot can push them.
- In the real lab the user tapes the river on the floor and places one or two objects as orientation
  marks. Whether the real boards match the world to the centimetre is not measured.

## What is in `src/plumetrace`

| Path | Content | State (2026-10-14) |
| --- | --- | --- |
| `plumetrace_msgs` | 6 messages | builds on Jazzy |
| `plumetrace_twin` | plume, sensor model, estimator, planner, nodes (`emulated_sensor`, `edge_buffer`, `link_gate`, `sample_ingest`, `sync_monitor`, `twin_core`, `mission_controller`, `obstacle_registry`, `obstacle_detector`, `virtual_obstacle_cloud`, `run_logger`, `localization_monitor`), `offline_sim.py` | 31 unit tests pass on Python 3.12 (Jazzy container) |
| `plumetrace_gateway` | WebSocket server, default `ws://localhost:8765`, parameters `host`, `port`, `scenario`; allow-listed commands only | ran on Jazzy (websockets 17.2) behind the relay |
| `plumetrace_sim/launch/lab_world.launch.py` | Gazebo with the lab arena and a Burger; `static_boards:=true` (default) loads a copy with fixed boards | ran in simulation |
| `plumetrace_sim/launch/sim_mission.launch.py` | `lab_world` + `lab_mission` with `use_sim_time:=true` and the generated map | A, B, C passed in simulation |
| `plumetrace_sim/launch/lab_map.launch.py` | `slam_toolbox` mapping; `use_sim_time` switch | ran in simulation (map frame = arena frame); not on the robot |
| `plumetrace_sim/launch/lab_nav.launch.py` | map server, AMCL, keepout filter, Nav2, optional collision monitor; switches `use_sim_time`, `stamped`, `xy_goal_tolerance`, `yaw_goal_tolerance` | ran in simulation; not on the robot |
| `plumetrace_sim/launch/lab_mission.launch.py` | `lab_nav` + twin nodes + gateway + CSV logs and rosbag | ran in simulation (through `sim_mission`); not on the robot |
| `plumetrace_sim/params/nav2_burger.yaml` | Nav2 parameters, one file for robot and simulation | loads in Nav2 1.3.13; tuned in simulation only |
| `plumetrace_sim/params/slam_lab.yaml` | `slam_toolbox` parameters; `map_start_pose` 0, 0, 0 (start mark) | ran in simulation |
| `plumetrace_sim/maps/` | `arena` (walls and inner boards from the world file), `keepout_mask` (water minus 0.06 m), `keepout_soft`; origin (-1.2, -4.0), 4.0 x 5.2 m | generated by `tools/reach_build.py` |
| `config/reach_frame.yaml` | arena-to-river transform, outfalls, stations, water polygon, inner boards; generated by `tools/reach_build.py` | refitted to the lab arena |
| `config/scenarios/{A,B,C}.yaml` | which outfall leaks, flow, background values | fine |
| `config/env.sh` | finds repo and workspace from its own path; sources ROS, `~/turtlebot3_ws`, this workspace | does not set `ROS_DOMAIN_ID` |
| `data/reach/` | water area, outfalls, stations (WGS84 GeoJSON) for the Pegnitz at Nürnberg Lederersteg | fine |
| `web/` | Cesium dashboard | checked through the relay against the real gateway in simulation |
| `tools/lab_setup.sh`, `lab_check.sh`, `lab_save_map.sh`, `lab_stop.sh`, `lab_tape_guide.py`, `lab_tf2_overlay.sh`, `wait_ready.py`, `wait_done.py` | lablaptop scripts | `lab_setup.sh`, `lab_tape_guide.py`, `wait_ready.py`, `wait_done.py` ran in the container; none ran on the lablaptop |
| `tools/relay.py` | dashboard + live data on one port, view-only for remote viewers | tested against the real gateway in simulation |
| `plumetrace_twin/localizer.py`, `scanfit.py`, `tools/localize.py`, node `localization_monitor` | self-localisation: scan-to-map fit compared with the 180 deg mirrored pose (resets AMCL to the mirror when that fits clearly better), global AMCL search while turning on the spot, clears costmaps, `--go-home`. `localize.py` runs before every mission; `localization_monitor` (in `lab_mission`, `loc_monitor:=true`) checks every 3 s during a mission and publishes `/localization/status`; `mission_controller` holds on LOST/RELOCALIZING, resumes on OK, aborts on FAILED | 2026-10-15: scan-fit tests on the arena map pass; localizer, monitor and mission_controller hold/resume checked against a stand-in for ROS; not run on Jazzy or the robot |
| `tools/run_abc.py`, `tools/start_demo.sh` | Loop until Ctrl-C (`--loops N`): `localize.py --go-home` (position check, start mark), `lab_mission nav:=false scenario:=<secret, random per round> strategy:=adaptive|sweep sensor_*:=...` with the monitor; `lab_nav` once; start_demo uses `--strategy sweep`; time-stamped output | 2026-10-15 lablaptop sweep: C PASS 6/6 stops, but `return_home` sent 3x pre-empted itself (status 6). Fixed: home via `localize.py --go-home`, `mission_controller.go_home` single-flight. Loop checked with ROS stand-ins only |
| Mock sensor settings (`sensor_model.SENSOR_DEFAULTS`, `sensor_*` launch args, `run_abc --sensor-*`, dashboard Mock sensor panel) | noise_rel, noise_abs, lag_s, dwell_s to `emulated_sensor`; noise also to the `twin_core` likelihood; `hello.sensor` to the dashboard | offline test with 3x noise, 5 s dwell: sweep still right; not yet on ROS |
| Strategy `sweep` (`estimator.sweep_order`, `twin_core`, `mission_controller`) | 6 fixed stops 0.2 m up- and downstream of each outfall, from the bank end nearest the robot; no early stop at 95 %. `lawnmower` removed | offline 15/15 correct at p = 1.00 (`tests/test_estimator.py`); not yet run in Gazebo or on the robot |
| `tools/reach_build.py`, `reach_from_open_data.py`, `check_reach_data.py`, `update_scenarios.py`, `export_czml.py` | reach and export tools | `reach_build.py` needs shapely 2.1 or newer |
| `docs/LAB_RUNSHEET.md` | the commands for a lab session, from git clone | updated for the refitted arena |
| `docs/SIMULATION.md`, `docs/sim_runs/`, `docs/img/` | what ran on Jazzy, with numbers, workarounds and screenshots | 2026-10-14 |
| `docs/lab_arena_layout.svg` | top-down drawing: walls, boards, river, outfalls, robot stops, start mark | generated by `tools/reach_build.py` |
| `../../docker/` | `Dockerfile`, `run.sh`, `build_ws.sh`, `sim_run.sh` (development laptop only) | in use |

## River placement (decided 2026-10-14)

Map frame = world frame of `lab_arena.world` (origin on the start mark, robot facing +x). The 3 m of river
run along +y from y -3.40 (upstream end) to -0.40, water at x 1.65 to 1.97, in the board-free column between
the L-shaped boards (x <= 1.0) and the board at (2.31, -0.80) (x >= 2.04). The left bank (outfalls, robot
stops) is the -x side, towards the start mark. Outfalls A, B, C at y -2.80, -2.00, -1.20. 22 robot stops at
x 1.52 to 1.61, every 0.12 m from y -3.12 to -0.59. Constants: `FLOW_YAW`, `REACH_ORIGIN` in `tools/reach_build.py`.

How the pieces connect: the twin plans a bank waypoint, `mission_controller` sends it to Nav2
(`navigate_to_pose`), the robot dwells, `emulated_sensor` reads the virtual plume at the robot's
localised pose (`map -> base_footprint`), the estimator updates the outfall probabilities, and the
gateway streams pose, samples, posterior and obstacles to the dashboard. The dashboard can send
`abort`, `return_home`, no-go zones and virtual obstacles back.

## Tasks, in order

1. **Build on Jazzy.** Done in the Docker container (2026-10-14): build clean, 31 tests pass on Python 3.12.
2. **Bring up the simulated arena.** Done: `/scan` 5 Hz, `/odom` 50 Hz, `/clock`, `/tf`, `/cmd_vel` TwistStamped,
   NVIDIA rendering, real-time factor 1.0. Boards are static in the launched copy.
3. **Refit the river to the lab arena.** Done (placement above), maps, frame, drawing, tape guide, tests.
4. **Simulation mission.** Done: `use_sim_time` switch, `sim_mission.launch.py`; A, B and C each ended with a
   `done` event naming the right outfall (`docs/SIMULATION.md`).
5. **Dashboard.** Done in simulation: relay against the real gateway, view-only refusal, key accepted.
6. **Real robot.** Next: follow `docs/LAB_RUNSHEET.md` on the lablaptop: `lab_check.sh`, tape guide, mapping,
   `lab_nav`, `lab_mission`. Keep the run sheet correct as things change.

## Dashboard and relay (tested 2026-10-14 with a stand-in gateway)

- Cesium ion only hosts static assets (terrain, buildings). It cannot receive live data. Live data goes
  gateway -> relay -> browser over WebSocket.
- `tools/relay.py` serves the dashboard and the live data on one port (default 8090, bound to
  127.0.0.1): `/` is `web/`, `/ws` is the data. It connects to the gateway as a client, keeps the last
  message of each type for late joiners, and makes `config.js` say `wsUrl: 'auto'`, so the page uses
  its own origin (`wss://` when the page is `https://`). One tunnel or reverse proxy therefore carries
  everything.
- Viewers are view-only: their commands get a rejected `ack` and never reach the gateway. With
  `PLUMETRACE_RELAY_KEY=<secret>` set, a page opened with `?key=<secret>` may send commands.
- Measured: page, `config.js` and `schema.json` served; path traversal and unknown files return 404;
  a viewer without the key or with a wrong key got `ack ok:false "view only"` and nothing reached the
  gateway; with the key the command arrived. In the browser the page showed "link connected", the
  mission state and the robot on the Pegnitz with ion terrain and buildings.
- Tested 2026-10-14 against the real ROS gateway in simulation (see `docs/SIMULATION.md`). Not tested: any public tunnel. Opening it "from anywhere"
  needs an HTTPS tunnel or reverse proxy that passes WebSockets, pointed at port 8090 on the machine
  that runs the gateway. That is the user's step (their choice of service or server). Anyone with the
  public address can see the page and the ion token inside it, so the token should be a restricted one.
- Needs the Python package `websockets` 13 or newer (`tools/lab_setup.sh --pip` gives the latest; an
  apt-installed 10.4 is too old for the relay, though the gateway itself still runs on it).

## Known risks

- `nav2_burger.yaml` has never been loaded by Nav2 1.3.13. Expect parameter errors on first start.
- AMCL in a near-symmetric rectangle can lock on mirrored; the inner boards and the user's marker
  objects break the symmetry. `tools/localize.py` checks for it (below); without it the robot must start on the start mark.
- Robot and lablaptop clocks: if they differ by more than a few tenths of a second, Nav2 rejects
  transforms. This is why the collision monitor is off by default.
- Goal tolerance is 0.03 m / 0.10 rad (launch arguments) and the top speed 0.15 m/s; tuned in simulation only.
- Simulation only: a lifecycle manager stalled once in five starts (`wait_ready.py` restarts it); the
  browser pane rendering Cesium slowed Gazebo to 0.19x real time.
- `lab_stop.sh` kills every ROS node on the machine that runs from `/opt/ros`.
- The arena is near point-symmetric: on the arena map the 180 deg mirrored pose fits the scan about 0.8 against
  1.0 at the true pose. `localize.py` relies on the inner boards for the difference; its thresholds
  (`--min-fit` 0.65, `--keep-fit` 0.75, `--margin` 0.08) come from simulated scans, not the real lab.
- AMCL `max_particles` raised from 2000 to 5000 (2026-10-15) for global localisation; not re-checked in simulation.

## Working habits

- Check Jazzy facts in the ROBOTIS sources under `src/` and in the installed packages, not from memory.
- One local commit per finished step, with a plain message.
- Record measured results (commands, numbers, dates) in `src/plumetrace/docs/`, and keep this file's
  Status and task list current.
- Never `pkill -f <free text>`; it can kill the calling shell. Use `tools/lab_stop.sh` or a PID.

## Status (2026-10-14, end of the simulation session)

Tasks 1 to 5 are done in a Jazzy Docker container on the development laptop: build, 31 unit tests, the
simulated lab arena (NVIDIA rendering through `--device nvidia.com/gpu=all`), the river refitted to the lab
arena, scenarios A, B and C each ending with a `done` event naming the right outfall, and the dashboard through
the relay with view-only refusal and key access. Details and numbers: `src/plumetrace/docs/SIMULATION.md`.
Nothing has run on the lablaptop or the real robot yet; that is task 6.
