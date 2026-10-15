# Lab run sheet: PlumeTrace on the real TurtleBot3 (ROS 2 Jazzy)

Everything of ours runs on the lablaptop. The robot only runs the stock bringup.
**Status (2026-10-14):** the whole chain ran in simulation on Jazzy (scenarios A, B, C each ended with the right
outfall, see `docs/SIMULATION.md`), and the repo has brought up and driven the real robot from the lablaptop.
`tools/start_demo.sh` and `tools/run_abc.py` (section 5b) are new and have not run on the lablaptop yet.
`tools/localize.py` (section 5c: the robot finds itself on the map and drives to the start mark) is new as of
2026-10-15 and has only run against a stand-in for ROS, not on Jazzy or the robot.
Keep one hand near Ctrl-C on the launch terminal: it stops Nav2 and the robot stops.

Every terminal on the lablaptop, after step 0:

```bash
cd ~/Euroteq_Eindhoven_T3/lab_turtlebot/src/plumetrace && source config/env.sh
```

## Quick reference

| Task | Command (lablaptop, in the folder above, unless noted) |
| --- | --- |
| Update code | `cd ~/Euroteq_Eindhoven_T3 && git pull && cd lab_turtlebot/src/plumetrace && tools/lab_setup.sh` |
| Robot bringup (robot) | `ssh turtlebot@192.168.8.32`, then `export ROS_DOMAIN_ID=32 TURTLEBOT3_MODEL=burger LDS_MODEL=LDS-02 && ros2 launch turtlebot3_bringup robot.launch.py` |
| Check link and clocks | `tools/lab_check.sh` |
| Tape guide | `python3 tools/lab_tape_guide.py 0.25` |
| Map the arena | `ros2 launch plumetrace_sim lab_map.launch.py` + `ros2 run turtlebot3_teleop teleop_keyboard` + `tools/lab_save_map.sh` |
| Navigation only | `ros2 launch plumetrace_sim lab_nav.launch.py rviz:=true` then `python3 tools/wait_ready.py 90` |
| One mission | `ros2 launch plumetrace_sim lab_mission.launch.py scenario:=B seed:=1` + relay + start (section 5) |
| **Full demo, 5 terminals** | **`tools/start_demo.sh`** (section 5b) |
| Missions A, B, C only | `python3 tools/run_abc.py --confirm` (needs bringup running; section 5b) |
| Robot finds itself, drives to the start mark | `python3 tools/localize.py --go-home` (needs `lab_nav` or `lab_mission` running; section 5c) |
| Dashboard | `PLUMETRACE_RELAY_KEY=<secret> python3 tools/relay.py`, open `http://localhost:8090/?key=<secret>` |
| Public link | `cloudflared tunnel --url http://localhost:8090` |
| RViz alone | `rviz2 -d plumetrace_sim/rviz/plumetrace.rviz` |
| Patrol loop | `python3 tools/wait_ready.py 90 && python3 tools/patrol_abc.py` (with `lab_nav` running) |
| Replay a run | `python3 tools/export_czml.py ~/plumetrace_runs/<time>` then load the `.czml` in the dashboard (Samples · export · replay) |
| Stop everything | `tools/start_demo.sh stop` or `tools/lab_stop.sh` |
| Tests | `python3 -m pytest -q tests` (34 pass) |

## 0. Once per lablaptop (5 min)

```bash
cd ~ && git clone https://github.com/PrinzMajkl/Euroteq_Eindhoven_T3.git
cd ~/Euroteq_Eindhoven_T3/lab_turtlebot/src/plumetrace
tools/lab_setup.sh --pip
source config/env.sh
echo $ROS_DOMAIN_ID
```

The code is on `main` (there is no `lab-turtlebot` branch on GitHub). `lab_setup.sh --pip` installs shapely,
pymap3d, websockets and jsonschema for this user (no sudo) and builds the workspace in `~/Euroteq_Eindhoven_T3/lab_turtlebot`
on top of `~/turtlebot3_ws` (the repo root is not the workspace: `lab_turtlebot/` is a folder inside it).
`ROS_DOMAIN_ID` must print 32 (from `~/.bashrc`). Check the tests: `python3 -m pytest -q tests` (34 pass).

Optional, for the public dashboard link (no sudo):

```bash
mkdir -p ~/.local/bin && curl -L -o ~/.local/bin/cloudflared https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 && chmod +x ~/.local/bin/cloudflared
```

City view with terrain and buildings: create `web/config.local.js` by hand with
`window.PLUMETRACE_CONFIG_LOCAL = { ionToken: '<your token>' };` (git-ignored, never commit it).

Later sessions: `git pull` in `~/Euroteq_Eindhoven_T3`, then `tools/lab_setup.sh` again (rebuilds the gateway and twin).

## 1. Robot up, check the link (5 min)

**Put the robot on the start mark (step 2) before you start the bringup.** Its odometry starts at zero where the
bringup starts, and the SLAM map in step 3 starts at the odometry origin (slam_toolbox ignores `map_start_pose`
in mapping mode; it only uses it when it loads a saved pose graph). If the robot was moved or driven since the
bringup started, stop the bringup, put the robot on the start mark and start the bringup again before step 3.

Robot terminal:

```bash
ssh turtlebot@192.168.8.32
export ROS_DOMAIN_ID=32 TURTLEBOT3_MODEL=burger LDS_MODEL=LDS-02
ros2 launch turtlebot3_bringup robot.launch.py
```

Lablaptop:

```bash
tools/lab_check.sh
```

It prints whether `/cmd_vel` is TwistStamped (expected; else add `stamped:=false` to every launch below) and
the clock offset between robot and laptop (above 0.3 s Nav2 rejects transforms: sync the clocks first).
Commit the report in `lab/reports/`. Exactly one node may publish `/cmd_vel` at a time:

```bash
ros2 topic info /cmd_vel -v
```

Do not run `code/safe_navigation_pollution_v5.py` (the no-Nav2 script) together with `lab_nav`, `lab_mission`
or the demo: both publish `/cmd_vel` and the robot moves stop-go.

## 2. Tape the river (15 min)

```bash
python3 tools/lab_tape_guide.py 0.25
```

Drawing: `docs/lab_arena_layout.svg` (open it in a browser). All distances are from two walls, standing on
the start mark looking the way the robot faces:

- **Start mark**: 1.00 m from the wall behind the robot ("back wall"), 1.00 m from the wall on its left
  ("left wall"). Mark the robot's centre and its heading (straight away from the back wall).
- **River**: 3.00 m long, parallel to the back wall, about 2.65 to 2.97 m from it (both edges are printed
  every 0.25 m), from 1.40 m to 4.40 m from the left wall. It flows towards the left wall.
- **Outfalls** A, B, C on the near bank, 3.80, 3.00 and 2.20 m from the left wall.
- The robot stops on the near bank, 2.52 to 2.61 m from the back wall. Keep the strip from about 2.2 m from
  the back wall up to the near tape clear over the whole river length.

The river sits in the free column between the L-shaped pair of boards (about 1.7 to 2.0 m from the back wall)
and the board 1.80 m from the left wall that sticks out from the far wall (3.0 to 3.6 m from the back wall,
0.07 m beyond the far tape); it never touches a board in the simulated arena.
If a real board stands in the river or on the near bank strip, move that board, not the river.

## 3. Map the arena (15 min)

Robot on the start mark, facing away from the back wall, **and the bringup started while it stood there** (see
step 1). The SLAM map frame is the robot's odometry frame, so the map is in the arena frame only then. Check in
RViz after the first seconds: the robot should sit at the map origin with the red x axis pointing away from the
back wall. If not, stop, restart the bringup on the start mark, and map again.

```bash
ros2 launch plumetrace_sim lab_map.launch.py
ros2 run turtlebot3_teleop teleop_keyboard
tools/lab_save_map.sh
```

(first command in terminal A, teleop in terminal B: drive one slow lap round the arena and the boards; save in
terminal C while A still runs). Stop A. Check `lab/maps/lab_arena.pgm` shows the walls and boards, then commit
`lab/maps/`. Without a saved map `lab_nav` uses the map generated from the simulated world, which is right
only if the real boards stand exactly where the simulated ones do.

## 4. Navigation only (10 min)

Robot back on the start mark.

```bash
ros2 launch plumetrace_sim lab_nav.launch.py rviz:=true
python3 tools/wait_ready.py 90
ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose "{pose: {header: {frame_id: map}, pose: {position: {x: 0.7, y: 0.0}, orientation: {w: 1.0}}}}"
```

(launch in terminal A, the other two in terminal B). `wait_ready.py` prints `ready`; the goal should drive the
robot 0.7 m straight ahead. Then send it to the first bank stop and check it stops beside the near tape, facing
the water:

```bash
ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose "{pose: {header: {frame_id: map}, pose: {position: {x: 1.565, y: -1.53}, orientation: {z: -0.039, w: 0.999}}}}"
```

## 5. One mission by hand (5 to 15 min per run)

Robot on the start mark, bringup running.

```bash
ros2 launch plumetrace_sim lab_mission.launch.py scenario:=B seed:=1
PLUMETRACE_RELAY_KEY=<secret> python3 tools/relay.py
python3 tools/wait_ready.py 90 && ros2 topic pub --once /mission/start std_msgs/msg/Empty "{}"
python3 tools/wait_done.py B 900
```

Terminal A: the launch. Terminal B: the relay; open `http://localhost:8090/?key=<secret>` on the lablaptop
(without `?key=` the page is view-only). Terminal C: start the mission. Terminal D: `wait_done.py` prints every
event and ends with `RESULT PASS` when the done event names outfall B. Logs and the rosbag are in
`~/plumetrace_runs/<time>/`; copy the folder into the repo or a drive before leaving. Repeat with `scenario:=A`
and `scenario:=C` (put the robot back on the start mark, stop terminal A with Ctrl-C and run `tools/lab_stop.sh`
between runs), or use `tools/run_abc.py` (5b), which does this for you.

Useful extras:

```bash
ros2 topic pub --once /twin/command std_msgs/msg/String "{data: '{\"type\": \"return_home\"}'}"
ros2 topic pub --once /twin/command std_msgs/msg/String "{data: '{\"type\": \"abort\"}'}"
ros2 topic echo /mission/events
ros2 launch plumetrace_sim lab_mission.launch.py scenario:=B show_true_plume:=true
```

`show_true_plume:=true` shows the simulated true plume on the dashboard from the start. Default `false`: it
appears only after the mission's `done` event, because it gives away the leaking outfall.

To let others watch from outside the lab: `cloudflared tunnel --url http://localhost:8090` (or
`~/.local/bin/cloudflared ...`) prints a `https://*.trycloudflare.com` link. Viewers are view-only; anyone with
the link sees the page and the Cesium ion token in it, so use a restricted token.

## 5b. Full demo in one command: missions A, B, C with the live dashboard

Map done (step 3), river taped (step 2). The robot may stand anywhere in the arena: before mission A it finds
itself on the map and drives to the start mark (section 5c). Terminal 3 starts the bringup over ssh, or leaves it
alone when `/odom` is already visible (bringup started by hand). On the lablaptop:

```bash
cd ~/Euroteq_Eindhoven_T3/lab_turtlebot/src/plumetrace
tools/start_demo.sh
```

It checks the build, `websockets`, `cloudflared` and that the robot answers ping, then opens five terminals
(gnome-terminal; tmux session `plumetrace` when there is no display or with `--tmux`):

| # | Terminal | What runs |
| --- | --- | --- |
| 1 | relay | `tools/relay.py` on port 8090 with a fresh relay key; prints the operator link `http://localhost:8090/?key=...` |
| 2 | cloudflare | `cloudflared tunnel --url http://localhost:8090` (public `https://*.trycloudflare.com` link, view-only without the key). Not installed: prints the install command from step 0 |
| 3 | robot | `ssh -t turtlebot@192.168.8.32` with `ROS_DOMAIN_ID=32`, `ros2 launch turtlebot3_bringup robot.launch.py` (type the robot password there) |
| 4 | missions | waits for `/odom` and `/scan`, then `tools/run_abc.py --confirm`: lab_mission A → robot localises itself and drives to the start mark → mission A → done → robot drives home → B → C. Press Enter before each run. Ends with a PASS/FAIL table |
| 5 | rviz | `rviz2 -d plumetrace_sim/rviz/plumetrace.rviz` |

Open the operator link from terminal 1 in a browser. Gazebo is not started: a simulated robot on domain 32 would
publish the same topics as the real one (for the simulation see `docs/SIMULATION.md`).

Variants:

```bash
tools/start_demo.sh --tmux
tmux attach -t plumetrace
PLUMETRACE_ROBOT=ubuntu@192.168.8.40 tools/start_demo.sh
PLUMETRACE_RELAY_KEY=mysecret tools/start_demo.sh
RUN_ABC_ARGS="--confirm -- xy_goal_tolerance:=0.05 yaw_goal_tolerance:=0.15" tools/start_demo.sh
tools/start_demo.sh stop
```

(`--tmux`: no gnome-terminal windows, switch windows with Ctrl-b 1..5. `PLUMETRACE_ROBOT`: other robot login.
`RUN_ABC_ARGS`: options for `run_abc.py`; arguments after `--` go to every lab_mission launch. `stop`: stops relay,
tunnel and all ROS nodes on the lablaptop via `tools/lab_stop.sh`; the bringup on the robot stops when its ssh
terminal closes or with Ctrl-C there.)

`run_abc.py` on its own (bringup already running, relay in another terminal):

```bash
python3 tools/run_abc.py --confirm
python3 tools/run_abc.py --scenarios B --confirm
python3 tools/run_abc.py --scenarios CAB --seed 2 --pause 20
python3 tools/run_abc.py --confirm -- xy_goal_tolerance:=0.05 yaw_goal_tolerance:=0.15
python3 tools/run_abc.py --no-localize      # robot already on the start mark: skip self-localisation
```

Per run it starts `lab_mission` (RViz off; terminal 5 has it), waits for Nav2 (restarts the launch once if it is
not ready), before the first run (and after any failed return home) runs `tools/localize.py` and sends the robot
to the start mark (5c), starts the mission, waits for `done` (`--timeout`, default 900 s), sends the robot home
(`--home-timeout`, default 200 s), stops the launch and pauses (`--pause`, default 10 s). If the robot does not
confirm it is home, the next run localises it again first. Ctrl-C aborts the mission and stops
the launch. Logs: `~/plumetrace_runs/<time>-abc/launch_<S>.log` and `summary.json`; each mission also writes its
own run folder (CSV + rosbag).

What the dashboard shows during the demo:

- Always visible: map with the robot (large icon, ring; Find / Follow buttons), mission card (run, scenario,
  elapsed time, what the robot is doing, battery), pollution status (NH₃-N, DO, Normal / Elevated / ALERT /
  SEVERE) and the "Which outfall?" bars.
- Map legend: plume layer Estimated / True (simulation) / Off and 3D columns.
- Closed sections: mission events, commands (abort, return home, no-go zones, virtual obstacles; need the key),
  sync per stream, runs table (one row per scenario with result), alerts, river and gauge (Pegnitz gauge
  24225000, flow, downstream ETA to the Regnitz), samples / CSV export / CZML replay.
- On the first alert: incident window with actions checklist, escalation ladder (Police/Fire → Umweltamt + SUN
  → WWA Nürnberg → Regierung von Mittelfranken / LfU → IWAP Rhein; logged only, no message is sent), public
  warning request draft with radius on the map (only authorities can issue warnings), and a pre-filled report
  and log (export JSON / CSV). "Export all runs (JSON)" in the runs section saves everything.

## 5c. The robot finds itself on the map and drives to the start mark

The map is fixed, so the robot does not have to start on the start mark. `tools/localize.py` works out where it
is and `--go-home` sends it to the mark. `run_abc.py` does this by itself before mission A.

```bash
python3 tools/localize.py --go-home          # lab_nav or lab_mission must be running
python3 tools/localize.py --force-global     # always search, even if the current pose already fits
```

1. **Check the current pose.** It compares the laser scan with the map at the pose AMCL has now (normally the
   start mark). If the scan fits there, nothing moves.
2. **Search.** Otherwise AMCL spreads its particles over the whole map and the robot turns slowly on the spot
   (0.4 rad/s, at most two turns per attempt, three attempts) until AMCL settles on one pose.
3. **Mirror check.** The arena is a near-symmetric rectangle: the pose turned 180° about the arena centre fits the
   walls almost as well (about 0.8 against 1.0 in tests on the arena map). Only the inner boards tell the two
   apart. A pose is accepted only if it fits the map and fits at least 0.08 better than its mirror. If the
   mirror fits clearly better, AMCL is reset to it (`/initialpose`).
4. **Clear costmaps.** They filled with obstacles drawn at wrong poses during the search.
5. **Drive.** With `--go-home`, Nav2 drives the robot to the start mark.

It prints both fits each time, for example `scan fit 0.93, at the mirrored pose 0.71 -> ok`. If the real lab
differs from the map (boards moved, bags, people), fits drop. Lower the thresholds if needed:
`--min-fit 0.55 --keep-fit 0.65` (defaults 0.65 / 0.75), `--margin 0.05` (default 0.08).

While it turns, keep the area around the robot clear and Ctrl-C at hand (Ctrl-C stops the robot). If it fails, set
the pose in RViz with **2D Pose Estimate**, or put the robot on the start mark, and press Enter in terminal 4.
Leave the marker objects where they were when the map was made: the inner boards and those objects are what
break the arena's symmetry.

## 6. Patrol loop: outfalls A, B, C, home, river bank, home, repeat

Robot on the start mark. Uses `lab_nav` only, not `lab_mission` (its mission controller would send goals too).
No pollution data reaches the dashboard in this mode.

```bash
ros2 launch plumetrace_sim lab_nav.launch.py rviz:=true
python3 tools/wait_ready.py 90 && python3 tools/patrol_abc.py
```

(launch in terminal A, the patrol in terminal B). One loop: the bank stops at outfalls A, B and C (1 s at
each, facing the water), home to the start mark, one smooth drive along the near bank from the upstream end to
the downstream end, home again; then the next loop, until Ctrl-C. Ctrl-C cancels the active goal (the robot
stops) and puts the controller parameters back. Check the route first with `python3 tools/patrol_abc.py --dry-run`.

It runs fast by default: 0.22 m/s (the Burger's top speed), 1.5 rad/s turns, goals accepted within 0.06 m and
0.25 rad, set on the running controller and restored when the script exits. `--speed normal` keeps the tuned
0.15 m/s. Other options: `--loops N`, `--legs abc` or `--legs river`, `--order CBA`, `--dwell S`, `--pause S`,
`--trace stops` (stop at every bank point instead of one smooth drive), `--min-voltage V` (goes home and stops
on low battery, default 11.0 V). Log: `~/plumetrace_runs/<time>-patrol/patrol.csv`.
Run it first with `--loops 1` and a hand near Ctrl-C; drop to `--speed normal` if the robot overshoots stops
or slides on the turns.

## 7. Before leaving

```bash
tools/start_demo.sh stop
ls ~/plumetrace_runs/
mkdir -p ~/Euroteq_Eindhoven_T3/lab_turtlebot/lab/runs && cp -r ~/plumetrace_runs/<time>* ~/Euroteq_Eindhoven_T3/lab_turtlebot/lab/runs/
```

Export the dashboard runs ("Export all runs (JSON)") if you want the incident records. Commit reports, maps and
run summaries you want to keep; never commit `web/config.local.js`.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| `lab_check.sh` sees no nodes | `echo $ROS_DOMAIN_ID` on robot and laptop must match (32); same network |
| `start_demo.sh`: "plumetrace_sim is not built" | `tools/lab_setup.sh` |
| `start_demo.sh`: "relay needs websockets >= 13" | `tools/lab_setup.sh --pip` |
| `start_demo.sh`: robot does not answer ping | robot on, same Wi-Fi, address 192.168.8.32 (else `PLUMETRACE_ROBOT=user@address`) |
| Terminal 3: ssh asks for password every time | normal; or once: `ssh-copy-id turtlebot@192.168.8.32` |
| Terminal 3: `ros2: command not found` on the robot | the robot's `~/.bashrc` must source `/opt/ros/jazzy/setup.bash` and its TurtleBot3 workspace |
| Terminal 4 waits forever for `/odom` | bringup not running or wrong domain: look at terminal 3, run `ros2 topic list` |
| No windows open (only a list of `bash ...` lines) | no gnome-terminal or display: use `tools/start_demo.sh --tmux` |
| Dashboard says "reconnecting" | relay not running (terminal 1); between runs it reconnects by itself when the next gateway starts |
| Dashboard shows the robot but no samples | mission not started yet, or mission ended; see Mission events section |
| Cloudflare link does not load | `cloudflared` output in terminal 2; quick tunnels change address on every start |
| `wait_ready.py` says "asking the lifecycle managers to start again" | normal once in a while (seen in simulation); it should then print `ready`. If it ends with `not active: [...]`, Ctrl-C terminal A, `tools/lab_stop.sh`, start again |
| Nav2 active, goal accepted, robot does not move | wrong `/cmd_vel` type: relaunch with `stamped:=false` (or `true`) |
| Robot moves stop-go, two publishers on `/cmd_vel` | `ros2 topic info /cmd_vel -v`; stop the extra one (e.g. the no-Nav2 script) |
| Jerky motion in general | see `docs/jerky_motion_diagnosis.md` (ranked causes and parameter fixes) |
| A node fails to configure | read its error in terminal A (or `launch_<S>.log` with `run_abc.py`) |
| "Transform ... extrapolation into the future/past" | clock offset: see step 1 |
| AMCL pose jumps or is mirrored | run `python3 tools/localize.py --force-global` (5c); if it keeps failing, marker objects moved since mapping |
| `localize.py`: "AMCL has not settled on one pose yet" three times | too little structure in view: move the robot nearer the inner boards, or set the pose with 2D Pose Estimate |
| `localize.py`: fits below the threshold although RViz shows the scan on the walls | the real lab differs from the map: lower `--min-fit` / `--keep-fit` (5c) |
| Robot circles or creeps at a goal and never finishes | add `xy_goal_tolerance:=0.05 yaw_goal_tolerance:=0.15` to the `lab_nav` / `lab_mission` command (or `RUN_ABC_ARGS`) |
| Robot cannot leave the bank ("failed to create plan") | it is too close to the water: check the tape positions against the tape guide; the keepout leaves 0.06 m of margin |
| Battery shown in orange or red on the dashboard | below 11.3 V / 11.0 V: charge or swap before the next run |
| `lab_map` fails: slam_toolbox missing | `sudo apt install ros-jazzy-slam-toolbox` (needs someone with sudo), or skip mapping (step 3) |
| Everything stuck | Ctrl-C, then `tools/start_demo.sh stop` or `tools/lab_stop.sh` (kills all ROS nodes on the lablaptop) |

## Limits on the real robot

There is no ground-truth pose, so the position error of a sample is not measured.
The pollution readings are emulated from the synthetic plume at the robot's localised position (no real probe).
STOP obstacles from the city view need `collision_monitor:=true`, which is off by default because it
depends on robot and lablaptop clocks agreeing.
