# Jerky motion: diagnosis (2026-10-14)

Read-only review of the Nav2 setup after commit "fix: smooth jerky motion — disable rotate-to-heading,
increase lookahead, raise AMCL thresholds". Nothing below has been run on the robot yet; it is a ranked
list of causes with the parameter changes to try. P = `plumetrace_sim/params/nav2_burger.yaml`.

## Ranked causes

| # | Cause | Evidence | Confidence | Fix |
| --- | --- | --- | --- | --- |
| 1 | **Regression from the last commit:** goal heading can no longer be reached. RPP only turns to the goal yaw when `use_rotate_to_heading` is true, but the goal checker still demands 0.10 rad. Every bank stop faces the water (about 90° off the driving direction), so the robot circles/creeps at each stop until the progress checker fails and recoveries (spin, back-up) run. | P: `use_rotate_to_heading: false`, `yaw_goal_tolerance: 0.10`, `stateful: False`, `min_approach_linear_velocity: 0.03`; `reach.py` stop headings; `LAB_RUNSHEET.md` already lists "robot circles at a goal" | high | `use_rotate_to_heading: true` with the new `rotate_to_heading_min_angle: 0.785` (the old stutter came from 0.3, not from the feature); `rotate_to_heading_angular_vel: 0.6`; optionally `stateful: True` |
| 2 | **Stop-go is in the mission design.** One `NavigateToPose` per stop, wait, 3 s dwell (sample rejected if the robot moves > 0.01 m), next goal. Stops are 0.12 m apart, shorter than `approach_velocity_scaling_dist: 0.3`, so every hop is a crawl at 0.03-0.05 m/s. | `mission_controller.py` goal loop; `emulated_sensor.py` dwell 3 s; `sensor_model.py` move limit | high (expected behaviour) | `approach_velocity_scaling_dist: 0.10`, `min_approach_linear_velocity: 0.05`; let the planner skip stops so hops are >= 0.3 m; `NavigateThroughPoses` for transit legs |
| 3 | **No acceleration limit anywhere.** No `velocity_smoother` in `lab_nav.launch.py`; controller output goes straight to `cmd_vel`; Burger `profile_acceleration: 0.0`. RPP steps between 0.15, 0.05 and 0.03 m/s. | `lab_nav.launch.py` node list and remap; ROBOTIS `burger.yaml` | high | Add `nav2_velocity_smoother` (controller → `cmd_vel_nav` → smoother → `cmd_vel`/`cmd_vel_raw`): `smoothing_frequency: 20.0`, `feedback: OPEN_LOOP`, `max_velocity: [0.15, 0.0, 1.0]`, `max_accel: [0.5, 0.0, 1.0]`, `max_decel: [-0.5, 0.0, -1.0]`, `enable_stamped_cmd_vel: true`; add to lifecycle list |
| 4 | **Collision check fires at the bank.** Water is lethal via the keepout filter; stops are ~0.13 m from the water edge with `robot_radius: 0.105` at 0.02 m resolution. Small localisation error → "collision ahead" → stop/recovery. | P: `use_collision_detection: true`, `max_allowed_time_to_collision_up_to_carrot: 1.0` | medium | `max_allowed_time_to_collision_up_to_carrot: 0.5` (keepout still blocks planning) |
| 5 | **Real robot only: 20 Hz control over Wi-Fi.** TF/odom/scan arrive over UDP Wi-Fi; unmeasured clock offset; tf2 0.36.22 deadlock bug. Missed cycles → zero commands → stutter. | P: `controller_frequency: 20.0` (ROBOTIS uses 10), `transform_tolerance: 0.5` | medium | `controller_frequency: 10.0`; measure clock offset with `tools/lab_check.sh`; run `tools/lab_tf2_overlay.sh` |
| 6 | **AMCL corrections in bigger jumps.** Last commit raised `update_min_d: 0.1`, `update_min_a: 0.2`: fewer, larger map→odom jumps shift the path and spike steering. | P: AMCL section | low-medium | `update_min_d: 0.05`, `update_min_a: 0.1`, together with fix 3 |
| 7 | **Teammate's no-Nav2 script (`code/safe_navigation_pollution_v5.py`, removed from the repo on 2026-10-18) fights over `/cmd_vel`** if run next to Nav2 (10 Hz TwistStamped incl. zeros). On its own it is bang-bang: turns in place above 0.3 rad error, `safe_distance` 0.6 m > board size so avoid mode keeps triggering, raw odometry only. | that file, publisher + timer + control branch | high if co-run, low as current cause | Never run alongside `lab_nav`/`lab_mission`; check `ros2 topic info /cmd_vel -v` shows one publisher |

## Smaller points

- With `use_velocity_scaled_lookahead_dist: true`, lookahead = 0.15 m/s × 1.5 s = 0.225 m, clamped to
  `min_lookahead_dist: 0.25`. The new `lookahead_dist: 0.4` is never used.
- Default BT replans at 1 Hz with no path smoothing; small path switches between plans.
- Velocity limits are inside the Burger's (0.15 vs 0.22 m/s); speed is not the cause.
- Goals are not resent at high rate (only cancelled after a 3 s link loss). `tools/patrol_abc.py` does not publish `/cmd_vel`.

## What the last commit did

- Fixed: frequent stop-and-turn (old `rotate_to_heading_min_angle: 0.3` with a 0.2 m lookahead).
- Made worse: unreachable goal heading (cause 1), AMCL jumps (cause 6).
- Still open: causes 2, 3, 4, 5, 7.

## Suggested first change

Re-enable `use_rotate_to_heading` (keep 0.785 rad), add the velocity smoother, set
`approach_velocity_scaling_dist: 0.10`. Then test in simulation (`sim_mission.launch.py`, scenarios A-C)
before the lab.
