#!/usr/bin/env python3
"""Continuous patrol for the TurtleBot3 in the lab arena, through Nav2 (ROS 2 Jazzy).

One loop:
  1. ABC:   drive to the bank stop at outfall A, then B, then C (dwell at each, facing the water)
  2. home:  back to the start mark (arena 0, 0, yaw 0)
  3. river: trace the near bank of the taped river, upstream end to downstream end
  4. home:  back to the start mark
and again, until Ctrl-C (or --loops N).

Every position comes from config/reach_frame.yaml (the same bank stops the mission uses), so the route is
in the arena / map frame and stays outside the keepout zone over the water.

Run it with lab_nav ONLY (not lab_mission: its mission_controller would send goals as well):
    ros2 launch plumetrace_sim lab_nav.launch.py rviz:=true          # terminal A
    python3 tools/wait_ready.py 90 && python3 tools/patrol_abc.py    # terminal B
Check the route without ROS:
    python3 tools/patrol_abc.py --dry-run

Options (defaults in brackets):
    --loops N            number of loops, 0 = forever [0]
    --legs abc,river     which legs to run, each followed by a trip home [abc,river]
    --order ABC          outfall order [ABC]
    --dwell S            seconds to wait at each outfall [1]
    --pause S            seconds to wait at home between legs [2]
    --trace through|stops
                         through: one NavigateThroughPoses goal along the bank (smooth);
                         stops: one NavigateToPose goal per bank stop, facing the water [through]
    --stride N           use every Nth bank stop for the river trace [2]
    --timeout S          give up on one goal after S seconds [180]
    --max-fails N        go home and stop after N failed goals in a row [3]
    --min-voltage V      go home and stop when /battery_state voltage drops below V, 0 = off [11.0]
    --speed fast|normal  fast: drive at the Burger's top speed 0.22 m/s, turn at 1.5 rad/s and accept a goal
                         within 0.06 m / 0.25 rad; normal: keep lab_nav's tuned values (0.15 m/s, 0.6 rad/s,
                         0.03 m / 0.10 rad) [fast]
    --force              start even if a mission_controller node is running

Fast mode changes the running controller_server's parameters at start and puts the old values back when the
script exits (also on Ctrl-C), so a later lab_mission run in the same launch keeps its tuned values.
If the script is killed hard (kill -9), restart lab_nav to get the tuned values back.

Ctrl-C cancels the active goal, which stops the robot, then exits. A log of every goal goes to
$PLUMETRACE_RUNS/<time>-patrol/patrol.csv (default ~/plumetrace_runs).
"""
import argparse
import csv
import math
import os
import signal
import sys
import threading
import time

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get('PLUMETRACE_REPO', os.path.dirname(HERE))
FLOW_YAW = math.pi / 2  # heading along the river, downstream (+y in the arena frame)

# controller_server parameters for --speed fast (TurtleBot3 Burger limits: 0.22 m/s, 2.84 rad/s).
# xy tolerance stays at 0.06 m: the bank stops are 0.18 m from the keepout edge and the robot radius is 0.105 m,
# so a stop off by 0.06 m still leaves the footprint outside the keepout (it could not plan away otherwise).
FAST_PARAMS = {
    'FollowPath.desired_linear_vel': 0.22,
    'FollowPath.rotate_to_heading_angular_vel': 1.5,
    'FollowPath.max_angular_accel': 2.0,
    'FollowPath.lookahead_dist': 0.35,
    'FollowPath.max_lookahead_dist': 0.5,
    'FollowPath.min_approach_linear_velocity': 0.05,
    'general_goal_checker.xy_goal_tolerance': 0.06,
    'general_goal_checker.yaw_goal_tolerance': 0.25,
    'FollowPath.rotate_to_heading_min_angle': 0.785,
    'FollowPath.min_lookahead_dist': 0.2,
    'FollowPath.approach_velocity_scaling_dist': 0.15,
    'FollowPath.regulated_linear_scaling_min_radius': 0.15,
}


# ---------------------------------------------------------------- route (no ROS needed)
def load_route(frame_path, order='ABC', stride=2):
    with open(frame_path) as f:
        cfg = yaml.safe_load(f)
    hx, hy, hyaw = (float(v) for v in cfg['arena']['start_pose'])
    home = ('home', hx, hy, hyaw)
    stops = sorted(cfg['sampling_points'], key=lambda p: float(p['along']))
    outfalls = {o['id']: o for o in cfg['outfalls']}

    abc = []
    for oid in order:
        if oid not in outfalls:
            raise SystemExit(f'unknown outfall {oid!r}; known: {sorted(outfalls)}')
        ox, oy = outfalls[oid]['arena_xy']
        p = min(stops, key=lambda s: math.hypot(s['edge'][0] - ox, s['edge'][1] - oy))
        abc.append((f'outfall {oid}', float(p['waypoint'][0]), float(p['waypoint'][1]), float(p['yaw'])))

    picked = stops[::max(1, stride)]
    if picked[-1] is not stops[-1]:
        picked.append(stops[-1])  # always reach the downstream end
    river = [(f'bank {int(p["index"])}', float(p['waypoint'][0]), float(p['waypoint'][1]), float(p['yaw']))
             for p in picked]
    return home, abc, river


def print_route(home, abc, river):
    def row(w):
        return f'  {w[0]:<11} x {w[1]:+.3f}  y {w[2]:+.3f}  yaw {w[3]:+.3f}'
    print('home:\n' + row(home))
    print('ABC leg:\n' + '\n'.join(row(w) for w in abc))
    print(f'river leg ({len(river)} points, upstream to downstream):\n' + '\n'.join(row(w) for w in river))


# ---------------------------------------------------------------- ROS part
def run(args, home, abc, river):
    import rclpy
    from action_msgs.msg import GoalStatus
    from geometry_msgs.msg import PoseStamped
    from nav2_msgs.action import NavigateThroughPoses, NavigateToPose
    from rclpy.action import ActionClient
    from rclpy.executors import MultiThreadedExecutor
    from rclpy.qos import qos_profile_sensor_data
    from sensor_msgs.msg import BatteryState

    ok_status = GoalStatus.STATUS_SUCCEEDED
    names = {GoalStatus.STATUS_SUCCEEDED: 'succeeded', GoalStatus.STATUS_ABORTED: 'aborted',
             GoalStatus.STATUS_CANCELED: 'canceled', GoalStatus.STATUS_UNKNOWN: 'no response'}

    rclpy.init()
    node = rclpy.create_node('plumetrace_patrol')
    to_pose = ActionClient(node, NavigateToPose, 'navigate_to_pose')
    through = ActionClient(node, NavigateThroughPoses, 'navigate_through_poses')
    stop = threading.Event()
    active = {'handle': None}
    battery = {'v': None}
    node.create_subscription(BatteryState, '/battery_state',
                             lambda m: battery.update(v=float(m.voltage)), qos_profile_sensor_data)

    executor = MultiThreadedExecutor()
    executor.add_node(node)
    threading.Thread(target=executor.spin, daemon=True).start()

    run_dir = os.path.join(os.environ.get('PLUMETRACE_RUNS', os.path.expanduser('~/plumetrace_runs')),
                           time.strftime('%Y%m%d-%H%M%S') + '-patrol')
    os.makedirs(run_dir, exist_ok=True)
    log_f = open(os.path.join(run_dir, 'patrol.csv'), 'w', newline='')
    log = csv.writer(log_f)
    log.writerow(['wall_time', 'loop', 'leg', 'target', 'x', 'y', 'yaw', 'status', 'seconds', 'battery_v'])

    def say(msg):
        print(time.strftime('%H:%M:%S ') + msg, flush=True)

    def pose(x, y, yaw):
        ps = PoseStamped()
        ps.header.frame_id = 'map'  # stamp 0 = latest transform (robot and lablaptop clocks may differ)
        ps.pose.position.x, ps.pose.position.y = x, y
        ps.pose.orientation.z, ps.pose.orientation.w = math.sin(yaw / 2), math.cos(yaw / 2)
        return ps

    def execute(client, goal, timeout):
        """Send a goal and wait for it. Returns (status, seconds)."""
        t0 = time.time()
        handle = None
        for _ in range(3):  # the first goal after start-up can lose its response while the BT loads
            fut = client.send_goal_async(goal)
            t1 = time.time()
            while not fut.done() and time.time() - t1 < 10 and not stop.is_set():
                time.sleep(0.05)
            if fut.done():
                handle = fut.result()
                break
            if stop.is_set():
                break
        if handle is None:
            return GoalStatus.STATUS_UNKNOWN, time.time() - t0
        if not handle.accepted:
            return GoalStatus.STATUS_ABORTED, time.time() - t0
        active['handle'] = handle
        rfut = handle.get_result_async()
        while not rfut.done():
            if stop.is_set() or time.time() - t0 > timeout:
                cfut = handle.cancel_goal_async()
                t2 = time.time()
                while not cfut.done() and time.time() - t2 < 3:
                    time.sleep(0.05)
                active['handle'] = None
                return GoalStatus.STATUS_CANCELED, time.time() - t0
            time.sleep(0.05)
        active['handle'] = None
        return rfut.result().status, time.time() - t0

    def record(loop, leg, target, x, y, yaw, status, secs):
        log.writerow([time.strftime('%Y-%m-%d %H:%M:%S'), loop, leg, target, f'{x:.3f}', f'{y:.3f}', f'{yaw:.3f}',
                      names.get(status, str(status)), f'{secs:.1f}', battery['v'] if battery['v'] else ''])
        log_f.flush()

    def go(loop, leg, wp, retries=1):
        label, x, y, yaw = wp
        for attempt in range(retries + 1):
            if stop.is_set():
                return False
            say(f'loop {loop} {leg}: -> {label} ({x:+.2f}, {y:+.2f})' + (' retry' if attempt else ''))
            g = NavigateToPose.Goal()
            g.pose = pose(x, y, yaw)
            st, secs = execute(to_pose, g, args.timeout)
            record(loop, leg, label, x, y, yaw, st, secs)
            say(f'  {label}: {names.get(st, st)} in {secs:.0f} s')
            if st == ok_status:
                return True
        return False

    def go_through(loop, leg, wps):
        if not through.wait_for_server(timeout_sec=3.0):
            say('navigate_through_poses not available: tracing stop by stop')
            return None
        g = NavigateThroughPoses.Goal()
        # drive along the bank: every pose heads downstream, so the robot does not turn to the water at each one
        poses = [pose(x, y, FLOW_YAW) for _, x, y, _ in wps]
        if isinstance(g.poses, list):   # Jazzy: geometry_msgs/PoseStamped[]
            g.poses = poses
        else:                           # later Nav2: nav_msgs/Goals
            g.poses.header.frame_id = 'map'
            g.poses.goals = poses
        say(f'loop {loop} {leg}: tracing the bank through {len(wps)} points '
            f'({wps[0][0]} -> {wps[-1][0]})')
        st, secs = execute(through, g, args.timeout * 2)
        record(loop, leg, f'{wps[0][0]}..{wps[-1][0]}', wps[-1][1], wps[-1][2], FLOW_YAW, st, secs)
        say(f'  river trace: {names.get(st, st)} in {secs:.0f} s')
        return st == ok_status

    from rcl_interfaces.msg import Parameter, ParameterType, ParameterValue
    from rcl_interfaces.srv import GetParameters, SetParameters

    def call(client, req, timeout=5.0):
        if not client.wait_for_service(timeout_sec=timeout):
            return None
        fut = client.call_async(req)
        t0 = time.time()
        while not fut.done() and time.time() - t0 < timeout:
            time.sleep(0.05)
        return fut.result() if fut.done() else None

    get_p = node.create_client(GetParameters, '/controller_server/get_parameters')
    set_p = node.create_client(SetParameters, '/controller_server/set_parameters')
    saved = {}

    def set_params(values):
        req = SetParameters.Request()
        for k, v in values.items():
            req.parameters.append(Parameter(name=k, value=ParameterValue(
                type=ParameterType.PARAMETER_DOUBLE, double_value=float(v))))
        res = call(set_p, req)
        if res is None:
            return ['no answer from /controller_server/set_parameters']
        return [f'{p.name}: {r.reason}' for p, r in zip(req.parameters, res.results) if not r.successful]

    def go_fast():
        res = call(get_p, GetParameters.Request(names=list(FAST_PARAMS)))
        if res is None:
            say('fast mode: controller_server did not answer; driving at the tuned speed')
            return
        for k, v in zip(FAST_PARAMS, res.values):
            if v.type == ParameterType.PARAMETER_DOUBLE:
                saved[k] = v.double_value
        errors = set_params({k: v for k, v in FAST_PARAMS.items() if k in saved})
        if errors:
            say('fast mode: some parameters were refused: ' + '; '.join(errors))
        say(f'fast mode: {FAST_PARAMS["FollowPath.desired_linear_vel"]} m/s, '
            f'{FAST_PARAMS["FollowPath.rotate_to_heading_angular_vel"]} rad/s turns '
            f'(was {saved.get("FollowPath.desired_linear_vel", "?")} m/s)')

    def battery_low():
        return args.min_voltage > 0 and battery['v'] is not None and 1.0 < battery['v'] < args.min_voltage

    def on_sigint(*_):
        if stop.is_set():
            os._exit(130)
        say('Ctrl-C: cancelling the active goal (robot stops)')
        stop.set()
    signal.signal(signal.SIGINT, on_sigint)

    rc = 0
    try:
        say('waiting for Nav2 (navigate_to_pose)')
        if not to_pose.wait_for_server(timeout_sec=60.0):
            say('navigate_to_pose not available: is lab_nav running and did tools/wait_ready.py print ready?')
            return 1
        time.sleep(2.0)  # discovery
        if not args.force and 'mission_controller' in node.get_node_names():
            say('a mission_controller node is running (lab_mission): it would send goals too. '
                'Use lab_nav instead, or pass --force.')
            return 1
        say(f'log: {run_dir}/patrol.csv')
        if args.speed == 'fast':
            go_fast()
        legs = [s.strip() for s in args.legs.split(',') if s.strip()]
        fails = 0
        loop = 0
        while not stop.is_set() and (args.loops == 0 or loop < args.loops):
            loop += 1
            for leg in legs:
                if stop.is_set():
                    break
                if battery_low():
                    say(f'battery {battery["v"]:.2f} V < {args.min_voltage} V: going home and stopping')
                    go(loop, 'home', home)
                    stop.set()
                    rc = 2
                    break
                if leg == 'abc':
                    for wp in abc:
                        if go(loop, 'abc', wp):
                            fails = 0
                            t_end = time.time() + args.dwell
                            while time.time() < t_end and not stop.is_set():
                                time.sleep(0.1)
                        else:
                            fails += 1
                        if fails >= args.max_fails:
                            break
                elif leg == 'river':
                    res = go_through(loop, 'river', river) if args.trace == 'through' else None
                    if res is None:
                        for wp in river:
                            fails = 0 if go(loop, 'river', wp, retries=0) else fails + 1
                            if fails >= args.max_fails or stop.is_set():
                                break
                    elif res:
                        fails = 0
                    else:
                        fails += 1
                else:
                    say(f'unknown leg {leg!r} (use abc, river)')
                    return 1
                if stop.is_set():
                    break
                if fails >= args.max_fails:
                    say(f'{fails} goals failed in a row: going home and stopping')
                    go(loop, 'home', home)
                    stop.set()
                    rc = 1
                    break
                if not go(loop, 'home', home, retries=2):
                    if not stop.is_set():
                        say('could not reach home: stopping')
                        rc = 1
                    stop.set()
                    break
                t_end = time.time() + args.pause
                while time.time() < t_end and not stop.is_set():
                    time.sleep(0.1)
            if not stop.is_set():
                say(f'loop {loop} done')
        return rc
    finally:
        h = active.get('handle')
        if h is not None:
            h.cancel_goal_async()
            time.sleep(1.0)
        if saved:
            errors = set_params(saved)
            say('restored the tuned controller parameters' if not errors else
                'could not restore all controller parameters (restart lab_nav): ' + '; '.join(errors))
        log_f.close()
        executor.shutdown(timeout_sec=1.0)
        node.destroy_node()
        rclpy.try_shutdown()
        say('stopped')


def main():
    ap = argparse.ArgumentParser(description='ABC outfalls -> home -> river bank -> home, in a loop (Nav2).')
    ap.add_argument('--loops', type=int, default=0)
    ap.add_argument('--legs', default='abc,river')
    ap.add_argument('--order', default='ABC')
    ap.add_argument('--dwell', type=float, default=1.0)
    ap.add_argument('--pause', type=float, default=2.0)
    ap.add_argument('--speed', choices=['fast', 'normal'], default='fast')
    ap.add_argument('--trace', choices=['through', 'stops'], default='through')
    ap.add_argument('--stride', type=int, default=2)
    ap.add_argument('--timeout', type=float, default=180.0)
    ap.add_argument('--max-fails', type=int, default=3)
    ap.add_argument('--min-voltage', type=float, default=11.0)
    ap.add_argument('--frame', default=os.path.join(REPO, 'config', 'reach_frame.yaml'))
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--dry-run', action='store_true', help='print the route and exit (no ROS)')
    args = ap.parse_args()
    home, abc, river = load_route(args.frame, args.order.upper(), args.stride)
    if args.dry_run:
        print_route(home, abc, river)
        return 0
    return run(args, home, abc, river)


if __name__ == '__main__':
    sys.exit(main())
