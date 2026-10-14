# Lab run sheet: PlumeTrace on the real TurtleBot3 (ROS 2 Jazzy)

Everything of ours runs on the lablaptop. The robot only runs the stock bringup.
**Status (2026-10-14): the whole chain ran in simulation on Jazzy (scenarios A, B, C each ended with the
right outfall, see `docs/SIMULATION.md`). Nothing below has run on the lablaptop or on the real robot yet.**
Keep one hand near Ctrl-C on the launch terminal: it stops Nav2 and the robot stops.

Every terminal on the lablaptop, after step 0:

```bash
cd ~/euroteq/lab_turtlebot/src/plumetrace && source config/env.sh
```

## 0. Once per lablaptop (5 min)

```bash
cd ~ && git clone -b lab-turtlebot https://github.com/PrinzMajkl/Euroteq_Eindhoven_T3.git euroteq
cd ~/euroteq/lab_turtlebot/src/plumetrace
tools/lab_setup.sh --pip
source config/env.sh
echo $ROS_DOMAIN_ID
```

`lab_setup.sh --pip` installs shapely, pymap3d, websockets and jsonschema for this user (no sudo) and builds
the workspace in `~/euroteq/lab_turtlebot` on top of `~/turtlebot3_ws` (the repo root is not the workspace:
`lab_turtlebot/` is a folder inside it, and the code lives only on the `lab-turtlebot` branch). `ROS_DOMAIN_ID` must print 32 (from `~/.bashrc`).
Check the tests: `python3 -m pytest -q tests` (31 pass in simulation).

Later sessions: `git pull` in `~/euroteq`, then `tools/lab_setup.sh` again.

## 1. Robot up, check the link (5 min)

**Put the robot on the start mark (step 2) before you start the bringup.** Its odometry starts at zero where the
bringup starts, and the SLAM map in step 3 starts at the odometry origin (slam_toolbox ignores `map_start_pose`
in mapping mode; it only uses it when it loads a saved pose graph). If the robot was moved or driven since the
bringup started, stop the bringup, put the robot on the start mark and start the bringup again before step 3.

Robot terminal (ssh): `export TURTLEBOT3_MODEL=burger && ros2 launch turtlebot3_bringup robot.launch.py`

Lablaptop:

```bash
tools/lab_check.sh
```

It prints whether `/cmd_vel` is TwistStamped (expected; else add `stamped:=false` to every launch below) and
the clock offset between robot and laptop (above 0.3 s Nav2 rejects transforms: sync the clocks first).
Commit the report in `lab/reports/`.

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

## 5. Mission (5 to 15 min per run)

Robot on the start mark.

```bash
ros2 launch plumetrace_sim lab_mission.launch.py scenario:=B seed:=1
python3 tools/relay.py
python3 tools/wait_ready.py 90 && ros2 topic pub --once /mission/start std_msgs/msg/Empty "{}"
python3 tools/wait_done.py B 900
```

Terminal A: the launch. Terminal B: the relay; open http://localhost:8090/ on the lablaptop. Terminal C:
start the mission. Terminal D: `wait_done.py` prints every event and ends with `RESULT PASS` when the done
event names outfall B. Logs and the rosbag are in `~/plumetrace_runs/<time>/`; copy the folder into the repo
or a drive before leaving. Repeat with `scenario:=A` and `scenario:=C` (put the robot back on the start mark,
stop terminal A with Ctrl-C and run `tools/lab_stop.sh` between runs).

Commands from the dashboard (abort, return home, no-go zones) need the relay key: start the relay with
`PLUMETRACE_RELAY_KEY=<secret> python3 tools/relay.py` and open `http://localhost:8090/?key=<secret>`.
Without the key the page is view-only. To let others watch from outside the lab, point your HTTPS tunnel or
reverse proxy at port 8090 (your step; anyone with the address sees the page and the ion token in it).

City view with terrain: create `web/config.local.js` on the laptop by hand with
`window.PLUMETRACE_CONFIG_LOCAL = { ionToken: '<your token>' };` (never commit it).

## 5b. One-command demo: missions A, B, C with the live dashboard

Robot on the start mark, map done (step 3), river taped (step 2). On the lablaptop:

```bash
tools/start_demo.sh
```

It checks the build, `websockets`, `cloudflared` and that the robot answers ping, then opens five terminals
(gnome-terminal; tmux session `plumetrace` when there is no display or with `--tmux`):

| # | Terminal | What runs |
| --- | --- | --- |
| 1 | relay | `tools/relay.py` on port 8090 with a fresh relay key; prints the operator link `http://localhost:8090/?key=...` |
| 2 | cloudflare | `cloudflared tunnel --url http://localhost:8090` (quick tunnel, public `https://*.trycloudflare.com` link, view-only without the key). Not installed: prints the no-sudo install command |
| 3 | robot | `ssh -t turtlebot@192.168.8.32`, `ROS_DOMAIN_ID=32`, `ros2 launch turtlebot3_bringup robot.launch.py` (type the robot password there) |
| 4 | missions | waits for `/odom` and `/scan`, then `tools/run_abc.py --confirm`: lab_mission A → done → robot drives home → B → C; press Enter before each run after checking the robot sits on the start mark. Ends with a PASS/FAIL table and `~/plumetrace_runs/<time>-abc/summary.json` |
| 5 | rviz | `rviz2` with `plumetrace_sim/rviz/plumetrace.rviz` |

The dashboard keeps one page open over all three runs: each run is archived in the Runs panel (samples,
max NH₃-N, result, incident) and the next starts clean. Gazebo is not started: a simulated robot on domain 32
would publish the same topics as the real one.

Options: `PLUMETRACE_ROBOT=user@host`, `ROS_DOMAIN_ID`, `PLUMETRACE_RELAY_KEY`, and
`RUN_ABC_ARGS="--confirm -- xy_goal_tolerance:=0.05 yaw_goal_tolerance:=0.15"` (arguments after `--` go to every
lab_mission launch). Stop everything: `tools/start_demo.sh stop` (also runs `tools/lab_stop.sh`).

## 6. Patrol loop: outfalls A, B, C, home, river bank, home, repeat

Robot on the start mark. Uses `lab_nav` only, not `lab_mission` (its mission controller would send goals too).

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

## Troubleshooting

| Symptom | Check |
| --- | --- |
| `lab_check.sh` sees no nodes | `echo $ROS_DOMAIN_ID` on robot and laptop must match; same network |
| `wait_ready.py` says "asking the lifecycle managers to start again" | normal once in a while (seen in simulation); it should then print `ready`. If it ends with `not active: [...]`, Ctrl-C terminal A, `tools/lab_stop.sh`, start again |
| Nav2 active, goal accepted, robot does not move | wrong `/cmd_vel` type: relaunch with `stamped:=false` (or `true`) |
| A node fails to configure | read its error in terminal A; `params/nav2_burger.yaml` loads cleanly in Nav2 1.3.13 in simulation |
| "Transform ... extrapolation into the future/past" | clock offset: see step 1 |
| AMCL pose jumps or is mirrored | robot was not on the start mark, or marker objects moved since mapping |
| Robot circles or creeps at a goal and never finishes | add `xy_goal_tolerance:=0.05 yaw_goal_tolerance:=0.15` to the `lab_nav` / `lab_mission` command (defaults 0.03 m, 0.10 rad, tuned in simulation only) |
| Robot cannot leave the bank ("failed to create plan") | it is too close to the water: check the tape positions against the tape guide; the keepout leaves 0.06 m of margin |
| `lab_map` fails: slam_toolbox missing | `sudo apt install ros-jazzy-slam-toolbox` (needs someone with sudo), or skip mapping (step 3) |
| Everything stuck | Ctrl-C, then `tools/lab_stop.sh` (kills all ROS nodes on the lablaptop) |

## Limits on the real robot

There is no ground-truth pose, so the position error of a sample is not measured.
STOP obstacles from the city view need `collision_monitor:=true`, which is off by default because it
depends on robot and lablaptop clocks agreeing.
