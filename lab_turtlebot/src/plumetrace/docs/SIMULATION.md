# Simulation on ROS 2 Jazzy: what ran, with numbers (2026-10-14)

Everything here ran on the development laptop in a Jazzy Docker container (Ubuntu 24.04, Python 3.12.3,
Nav2 1.3.13, slam_toolbox 2.8.5, gz sim 8.15.0, ros_gz_sim 1.0.24, tf2 0.36.21, TurtleBot3 packages built
from this repo's `src/`). Nothing here has run on the lablaptop or the real robot.
Times in the run folder names are UTC (container clock).

## How to repeat it (development laptop only)

```bash
docker/run.sh image          # once: build plumetrace-jazzy (osrf/ros:jazzy-desktop + Nav2, slam_toolbox, ros_gz, pip libraries)
docker/run.sh up             # container with GPU (--device nvidia.com/gpu=all), X11 windows, ports 8090/8765 on 127.0.0.1
docker/run.sh ws             # build ~/turtlebot3_ws (ROBOTIS underlay) and plumetrace (tools/lab_setup.sh --pip) in Docker volumes
docker/run.sh x 'python3 -m pytest -q tests'
docker/sim_run.sh B 1        # one mission: Gazebo + Nav2 + twin + gateway + relay, exit 0 = done event names the right outfall
```

`docker/sim_run.sh` restarts the container, starts `sim_mission.launch.py` (Gazebo and RViz windows on the
desktop), starts `tools/relay.py` (dashboard on http://localhost:8090/, commands with `?key=` + the value in
`docker/runs/relay_key`), waits for Nav2 with `tools/wait_ready.py`, publishes `/mission/start` and follows
`/mission/events` with `tools/wait_done.py`. Logs, CSV files and the rosbag go to `docker/runs/<time>-sim-<scenario>/`
(git-ignored). The host's `build/`, `install/`, `log/` are never written.

## Results

| Step | Result |
| --- | --- |
| Image build | `plumetrace-jazzy:latest`, 7.0 GB |
| Workspaces | ROBOTIS underlay: 15 packages in 1 min 8 s; plumetrace: 4 packages in 17 s, no errors |
| Unit tests (Python 3.12) | 31 passed. Only change needed: `jsonschema` was missing (added to the pip list of `lab_setup.sh` and the image) |
| Graphics | NVIDIA path works: `--device nvidia.com/gpu=all` + `NVIDIA_DRIVER_CAPABILITIES=all`; glxinfo: "NVIDIA GeForce GTX 1060/PCIe/SSE2, OpenGL 4.6.0 NVIDIA 580.178.04"; Ogre2 `GL_VENDOR = NVIDIA Corporation`. The Intel `/dev/dri` and software fallbacks were not needed and not tried. Ogre first logs an EGL error for `/dev/dri/card0` (not passed into the container) and then uses the NVIDIA device |
| Windows | Gazebo GUI and RViz open on the host desktop (XWayland, `DISPLAY=:0`, cookie copied by `docker/run.sh up`) |
| `lab_world.launch.py` | `/scan` 4.99 Hz, 360 beams, frame `base_scan`, range 0.12 to 3.5 m, ranges match the walls (front 2.66 m, left 0.97 m, back 0.94 m from the start); `/odom` 49.9 Hz; `/clock` ~1000 Hz; `/tf`, `/tf_static` present; `/cmd_vel` is `geometry_msgs/msg/TwistStamped` (1 subscriber, the bridge); real-time factor 1.00 |
| Scenario B | `20261014-022408-sim-B`: done event `final DONE`, `map_label B`, probabilities [0, 1, 0], 2 samples, 57 s wall |
| Scenario A | `20261014-022551-sim-A`: done event `final DONE`, `map_label A`, probabilities [1, 0, 0], 2 samples, 59 s wall |
| Scenario C | `20261014-092513-sim-C`: done event `final DONE`, `map_label C`, probabilities [0, 0, 1], 1 sample, 60 s wall (real-time factor 0.19 during this run, see below) |
| Dashboard | Relay against the real gateway during the C run: page "link connected", mission state RUNNING then DONE, sync per stream SYNCED, robot on the Pegnitz between B and C, sample count and last NH3-N, outfall bars C 100 %. Plume data checked through the relay: 992 plume points, 129 above 0.1 mg/L (max 1.09 mg/L) downstream of C. Plain viewer clicking "Return home": `✗ rejected: view only`, nothing in the gateway log. With `?key=`: `✓ return_home`, gateway log "command return_home accepted", the robot drove back to (0.01, -0.00) |

Screenshots: `docs/img/sim_gazebo_lab_arena.png`, `docs/img/sim_rviz_after_C.png`, `docs/img/dashboard_sim_C_done.jpg`.
Events and samples of the three passing runs: `docs/sim_runs/`.

The `done` check was not weakened: `tools/wait_done.py` passes only when the done event has `final == DONE`
and its `map_label` equals `active_outfall` of the scenario file.

Every passing sample carried qc flag 1 (MOVED): the AMCL pose shifts by more than 1 cm during the 3 s dwell
after the robot stops. Only OFF_BANK (4) samples are left out by the estimator, so these samples count.

## Navigation accuracy against Gazebo ground truth

Six bank goals in a row, sent by hand with `ros2 action send_goal` (navigation only, final parameters): all SUCCEEDED; AMCL
position error at the stop 0.4 to 2.3 cm, AMCL yaw error up to 0.15 rad; true stop 1 to 5 cm from the goal,
mostly along the bank.

## Problems found and what was changed

| Problem (simulation) | Change | Applies to the real robot too |
| --- | --- | --- |
| Nav2 1.3.13 refused `nav2_navfn_planner/NavfnPlanner` (planner_server FATAL) | plugin names in `nav2_burger.yaml` use `::` (`nav2_navfn_planner::NavfnPlanner`, `nav2_behaviors::Spin`, `BackUp`, `DriveOnHeading`, `Wait`); `progress_checker_plugins` is a list | yes |
| The robot stops 0.13 m from the water and is 0.105 m in radius: 2 cm of localisation error put it "in collision" with the keepout and Nav2 could not plan away from the bank (first B run never finished) | lethal keepout mask = water pulled back 0.06 m from its edge (`KEEPOUT_MARGIN` in `tools/reach_build.py`); the soft cost still covers the whole water | yes |
| With goal tolerance 0.05 m / 0.20 rad the first stop was off the bank (probe more than 5 cm from the edge) | `xy_goal_tolerance` 0.03, `yaw_goal_tolerance` 0.10, both also launch arguments of `lab_nav` / `lab_mission` / `sim_mission` | yes; raise them with the launch arguments if the real robot circles at a goal |
| Turning in place at 1 rad/s with 3.2 rad/s² the simulated Burger slides 6 cm (1.8 cm at 1 rad/s²); AMCL then lost up to 16 cm and goals aborted | `rotate_to_heading_angular_vel` 0.6, `max_angular_accel` 1.0, behavior server `max_rotational_vel` 0.6, `rotational_acc_lim` 1.0 | yes (gentler turns) |
| Once in five starts `lifecycle_manager_filters` stopped after "Starting managed nodes bringup..." and the keepout servers stayed inactive | `tools/wait_ready.py` asks the three lifecycle managers to start their nodes again after half its timeout | yes |
| The browser pane rendering Cesium took ~3 CPU cores; Gazebo fell to real-time factor 0.19 during the C run and Nav2 timed out once acknowledging a goal (the return-home drive still arrived) | none in code; close the dashboard tab or use a lighter browser window while a simulation runs | no (the lablaptop has no Gazebo) |
| Boards in `lab_arena.world` are non-static | `lab_world.launch.py` loads a copy with `<static>true</static>` (default `static_boards:=true`); the world file itself is unchanged | no |

## Not done here

- Mapping with `lab_map` in simulation (the simulation uses the map generated from the world file).
- The collision monitor (`collision_monitor:=true`) was not started.
- `lab_map`, `lab_nav`, `lab_mission` on the real robot: tomorrow, `docs/LAB_RUNSHEET.md`.
- No public tunnel; the relay was opened on localhost only.
