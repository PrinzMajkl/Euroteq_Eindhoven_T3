#!/usr/bin/env python3
"""Run the PlumeTrace missions for scenarios A, B and C back to back on the real TurtleBot3 (or Gazebo).

    python3 tools/run_abc.py [--scenarios ABC] [--seed 1] [--confirm] [--pause 3] [--no-localize] [--sim-time]
                             [-- launch args]

Once, at the start:
  1. ros2 launch plumetrace_sim lab_nav.launch.py (map server, AMCL, Nav2); tools/wait_ready.py until it is
     active (one restart if not). Nav2 and AMCL then stay up for all runs.
Before every mission (A, B and C):
  2. tools/localize.py --go-home: check the robot's position on the map (no motion when the scan fits); if it is
     lost, find it (turning on the spot); then drive to the start mark. So every mission starts from the start
     mark with a checked position. --no-localize: drive to the start mark only (no check; robot must have
     started on the mark).
During every mission:
  3. ros2 launch plumetrace_sim lab_mission.launch.py scenario:=<S> nav:=false (twin nodes, gateway, logs, and
     localization_monitor), /mission/start, follow /mission/events until `done`. localization_monitor checks
     the position every 3 s; when the robot is lost the mission holds, the robot re-localises on the spot and the
     mission resumes (if that fails, the mission is aborted and the next one localises again first).
  4. stop the mission launch, pause (--pause, default 3 s), next scenario.
After the last mission the robot drives to the start mark.

The dashboard (through tools/relay.py) stays open the whole time: it sees a new gateway `hello` and a new
`mission.scenario` per run, archives the previous run and starts a clean one, so all three runs fill it with
samples, plume, outfall probabilities, alerts and incidents.

Result per run: PASS only when the mission ends DONE naming the right outfall with probability >= 0.95; UNSURE
when it ends DONE without that confidence (for example when no stop on the bank was reached, so every sample was
ignored); FAIL otherwise. The number of stops Nav2 reached is shown too.
--confirm waits for Enter before the first run (--confirm-each: before every run).
Arguments after `--` go to the lab_nav and every lab_mission launch (e.g. `-- xy_goal_tolerance:=0.05`).
Every line printed carries the clock time and the minutes since the start, so slow steps show up.
Ctrl-C: aborts the running mission, stops the launches and exits (the robot stops).
Logs: $PLUMETRACE_RUNS/<time>-abc/ (nav.log, launch_<S>.log per run, summary.json); each mission also writes
its own run folder (CSV + rosbag) as usual.
"""

import argparse
import json
import os
import signal
import subprocess
import sys
import threading
import time

import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.parameter import Parameter
from rclpy.signals import SignalHandlerOptions
from std_msgs.msg import Empty, String

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get('PLUMETRACE_REPO', os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, 'plumetrace_twin'))
from plumetrace_twin.scenario import load_scenario  # noqa: E402

try:
    from plumetrace_msgs.msg import MissionState
except ImportError:  # workspace not sourced: still runs, without state confirmation
    MissionState = None

GOAL_SUCCEEDED = 4  # action_msgs/GoalStatus.STATUS_SUCCEEDED
LOCALISED_P = 0.95  # plumetrace_twin.estimator.LOCALISED_P: the mission's own confidence threshold


class Watcher:
    """Collects /mission/events and /mission/state from whichever mission is running."""

    def __init__(self, node):
        self.node = node
        self.cv = threading.Condition()
        self.events = []
        self.state = None
        node.create_subscription(String, '/mission/events', self.on_event, 50)
        if MissionState is not None:
            node.create_subscription(MissionState, '/mission/state', self.on_state, 10)
        self.start_pub = node.create_publisher(Empty, '/mission/start', 10)
        self.cmd_pub = node.create_publisher(String, '/twin/command', 10)

    def on_event(self, msg):
        try:
            e = json.loads(msg.data)
        except ValueError:
            return
        print('  event', json.dumps(e), flush=True)
        with self.cv:
            self.events.append(e)
            self.cv.notify_all()

    def on_state(self, msg):
        with self.cv:
            self.state = msg.state
            self.cv.notify_all()

    def reset(self):
        with self.cv:
            self.events = []
            self.state = None

    def wait_event(self, kind, timeout):
        end = time.time() + timeout
        with self.cv:
            while time.time() < end:
                for e in self.events:
                    if e.get('type') == kind:
                        return e
                self.cv.wait(timeout=min(1.0, max(0.0, end - time.time())))
        return None

    def start_mission(self, timeout=30.0):
        """Publish /mission/start until the mission reports RUNNING (or any event arrives)."""
        end = time.time() + timeout
        while time.time() < end:
            self.start_pub.publish(Empty())
            with self.cv:
                self.cv.wait(timeout=1.0)
                if self.state in ('RUNNING', 'HOLD', 'DONE') or self.events:
                    return True
        return MissionState is None  # no state topic available: assume it started

    def command(self, kind):
        for _ in range(3):  # cheap insurance against a lost first message right after discovery
            self.cmd_pub.publish(String(data=json.dumps(dict(type=kind, source='run_abc'))))
            time.sleep(0.3)


T0 = time.time()


def log(msg):
    print(f'[{time.strftime("%H:%M:%S")} +{(time.time() - T0) / 60:4.1f} min] {msg}', flush=True)


class Launch:
    def __init__(self, launch_file, args, log_path):
        cmd = ['ros2', 'launch', 'plumetrace_sim', launch_file] + args
        log('$ ' + ' '.join(cmd))
        self.log = open(log_path, 'w')
        self.proc = subprocess.Popen(cmd, stdout=self.log, stderr=subprocess.STDOUT, start_new_session=True)

    def stop(self):
        if self.proc.poll() is None:
            for sig, wait in ((signal.SIGINT, 15), (signal.SIGTERM, 5), (signal.SIGKILL, 3)):
                try:
                    os.killpg(self.proc.pid, sig)
                except ProcessLookupError:
                    break
                try:
                    self.proc.wait(timeout=wait)
                    break
                except subprocess.TimeoutExpired:
                    continue
        self.log.close()


def common_args(args):
    return (['use_sim_time:=true'] if args.sim_time else []) + args.launch_args


def wait_ready(timeout):
    return subprocess.call([sys.executable, os.path.join(HERE, 'wait_ready.py'), str(timeout)]) == 0


def start_nav(args, out_dir):
    """lab_nav once for all runs; one restart when Nav2 does not come up."""
    for attempt in (1, 2):
        nav = Launch('lab_nav.launch.py', ['rviz:=false'] + common_args(args), os.path.join(out_dir, 'nav.log'))
        if wait_ready(args.ready_timeout):
            log('Nav2 is active')
            return nav
        log(f'Nav2 not ready (attempt {attempt}); restarting it')
        nav.stop()
        time.sleep(5)
    return None


def localize(args):
    log("checking the robot's position on the map, then driving to the start mark ..." if not args.no_localize
        else 'driving to the start mark ...')
    cmd = [sys.executable, os.path.join(HERE, 'localize.py'), '--go-home'] + (['--sim-time'] if args.sim_time else []) \
        + (['--skip-check'] if args.no_localize else [])
    ok = subprocess.call(cmd) == 0
    base = [sys.executable, os.path.join(HERE, 'localize.py')] + (['--sim-time'] if args.sim_time else [])
    while not ok:  # never start a mission from a wrong pose: every goal would fail (status 6) and nothing moves
        if not sys.stdin.isatty():
            log('!! localisation failed; continuing with the pose AMCL has')
            return False
        a = input('  Localisation or the drive home failed.\n'
                  '    Enter = I put the robot on the start mark facing +x (AMCL is reset there)\n'
                  '    p     = I set "2D Pose Estimate" in RViz (check it, then drive to the start mark)\n'
                  '    s     = start the mission anyway\n  > ').strip().lower()
        if a == 's':
            log('!! starting with an unchecked pose')
            return False
        ok = subprocess.call(base + (['--go-home'] if a == 'p' else ['--set-start'])) == 0
    log('robot localised and on the start mark')
    return True


MISSION_NODES = ('mission_controller', 'plumetrace_gateway', 'twin_core', 'emulated_sensor', 'localization_monitor')


def mission_nodes_alive(node):
    return sorted(set(node.get_node_names()) & set(MISSION_NODES))


def wait_mission_nodes_gone(node, timeout=20.0):
    end = time.time() + timeout
    while time.time() < end:
        left = mission_nodes_alive(node)
        if not left:
            return []
        time.sleep(1.0)
    return mission_nodes_alive(node)


def start_mission_launch(node, s, args, out_dir):
    """Never start a mission next to a leftover one (two controllers/gateways = doubled samples, port clash)."""
    left = wait_mission_nodes_gone(node, timeout=5.0)
    if left:
        log(f'!! mission nodes from an earlier launch are still running: {left}. Stop them first '
            '(tools/lab_stop.sh stops every ROS node on this laptop, then start run_abc again).')
        return None
    return Launch('lab_mission.launch.py', [f'scenario:={s}', f'seed:={args.seed}', 'nav:=false', 'rviz:=false']
                  + (['loc_monitor:=false'] if args.no_localize else []) + common_args(args),
                  os.path.join(out_dir, f'launch_{s}.log'))


def run_one(watcher, s, args, last):
    truth = load_scenario(s)['active_outfall']
    res = dict(scenario=s, truth=truth, started=time.strftime('%H:%M:%S'))
    watcher.reset()
    try:
        if not watcher.start_mission(timeout=60.0):  # retries until the mission controller is up and RUNNING
            res.update(result='NO_START')
            return res
        log(f'mission {s} started')
        done = watcher.wait_event('done', args.timeout)
        if done is None:
            watcher.command('abort')
            res.update(result='TIMEOUT')
            watcher.wait_event('done', 20)
        else:
            probs = done.get('probabilities') or []
            confident = bool(probs) and max(probs) >= LOCALISED_P
            ok = done.get('final') == 'DONE' and done.get('map_label') == truth and confident
            # a uniform posterior also has a map_label (the first outfall), so the label alone is not a result
            result = 'PASS' if ok else ('UNSURE' if done.get('final') == 'DONE' and not confident else 'FAIL')
            res.update(result=result, final=done.get('final'), map_label=done.get('map_label'),
                       probabilities=probs, samples=done.get('samples'))
        goals = [e for e in watcher.events if e.get('type') == 'goal_result']
        failed = [e for e in goals if e.get('status') != GOAL_SUCCEEDED]
        res['stops_reached'] = f'{len(goals) - len(failed)}/{len(goals)}'
        if goals and len(failed) > len(goals) / 2:
            log(f'!! Nav2 failed {len(failed)} of {len(goals)} stops: samples were taken where the robot stopped, not at the '
                'planned bank stops. '
                'Check the robot position in RViz (scan on the walls?) and for duplicate nodes (run sheet 5b).')
        holds = [e for e in watcher.events if e.get('type') == 'localization_lost']
        res['relocalized'] = len(holds)
        top = max(res.get('probabilities') or [0])
        log(f'{s}: {res["result"]} (named {res.get("map_label")} with p={top:.2f}, truth {truth}; '
            f'stops reached {res["stops_reached"]})'
            + (f'; robot was lost {len(holds)}x during the mission and re-localised' if holds else ''))
        if last:
            log('returning to the start mark ...')
            watcher.command('return_home')
            home = watcher.wait_event('return_home', args.home_timeout)
            res['home'] = 'OK' if home and home.get('status') == GOAL_SUCCEEDED else 'FAILED'
            log('on the start mark' if res['home'] == 'OK' else '!! robot did not confirm it is home')
    finally:
        res['ended'] = time.strftime('%H:%M:%S')
    return res


def main():
    argv = sys.argv[1:]
    extra = argv[argv.index('--') + 1:] if '--' in argv else []
    argv = argv[:argv.index('--')] if '--' in argv else argv
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--scenarios', default='ABC')
    ap.add_argument('--seed', type=int, default=1)
    ap.add_argument('--timeout', type=float, default=900.0, help='seconds per mission until done')
    ap.add_argument('--home-timeout', type=float, default=200.0)
    ap.add_argument('--ready-timeout', type=float, default=90.0)
    ap.add_argument('--pause', type=float, default=3.0, help='seconds between runs')
    ap.add_argument('--confirm', action='store_true', help='wait for Enter before the first run')
    ap.add_argument('--confirm-each', action='store_true', help='wait for Enter before every run')
    ap.add_argument('--sim-time', action='store_true', help='Gazebo: use_sim_time:=true')
    ap.add_argument('--no-localize', action='store_true', help='no position check before missions, only the drive '
                    'to the start mark (robot must have started on the mark); also turns off the in-mission monitor')
    args = ap.parse_args(argv)
    args.launch_args = extra

    out_dir = os.path.join(os.environ.get('PLUMETRACE_RUNS', os.path.expanduser('~/plumetrace_runs')),
                           time.strftime('%Y%m%d-%H%M%S') + '-abc')
    os.makedirs(out_dir, exist_ok=True)
    # no rclpy SIGINT handler: Ctrl-C raises KeyboardInterrupt with ROS still up, so the abort still goes out
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    node = rclpy.create_node('plumetrace_run_abc')
    if args.sim_time:
        node.set_parameters([Parameter('use_sim_time', value=True)])
    watcher = Watcher(node)
    ex = SingleThreadedExecutor()
    ex.add_node(node)
    spin = threading.Thread(target=ex.spin, daemon=True)
    spin.start()

    results, launch, nav = [], None, None
    scenarios = args.scenarios.upper()
    try:
        nav = start_nav(args, out_dir)
        if nav is None:
            log('Nav2 did not come up twice: see nav.log in ' + out_dir)
            sys.exit(1)
        for i, s in enumerate(scenarios):
            log(f'=== run {i + 1}/{len(scenarios)}: scenario {s} ===')
            if not (args.no_localize and i == 0):  # localise + start mark before every mission
                localize(args)
            if args.confirm_each or (args.confirm and i == 0):
                input('Press Enter to start the mission. ')
            launch = start_mission_launch(node, s, args, out_dir)  # main owns it, so Ctrl-C always stops it
            if launch is None:
                results.append(dict(scenario=s, truth=load_scenario(s)['active_outfall'], result='LEFTOVER_NODES'))
                break
            results.append(run_one(watcher, s, args, last=i + 1 == len(scenarios)))
            launch.stop()
            launch = None
            left = wait_mission_nodes_gone(node)
            if left:
                log(f'!! still running after the launch stopped: {left}; not starting another mission')
                break
            with open(os.path.join(out_dir, 'summary.json'), 'w') as f:
                json.dump(results, f, indent=1)
            if i + 1 < len(scenarios):
                time.sleep(args.pause)
    except KeyboardInterrupt:
        print('\nCtrl-C: aborting the mission and stopping the launches', flush=True)
        watcher.command('abort')
    finally:
        if launch is not None:
            launch.stop()
        if nav is not None:
            nav.stop()
        ex.shutdown(timeout_sec=2.0)  # stop spinning before tearing down, else rclpy aborts at exit
        spin.join(timeout=3.0)
        node.destroy_node()
        rclpy.try_shutdown()

    print('\nscenario  result   named  p     truth  stops   samples  started   ended')
    for r in results:
        p = max(r.get('probabilities') or [0])
        print(f"{r['scenario']:<9} {r.get('result', '?'):<8} {str(r.get('map_label')):<6} {p:<5.2f} {r['truth']:<6} "
              f"{r.get('stops_reached', '-'):<7} {str(r.get('samples', '-')):<8} {r.get('started', '')}  "
              f"{r.get('ended', '')}")
    print(f'logs: {out_dir}')
    sys.exit(0 if results and all(r.get('result') == 'PASS' for r in results) else 1)


if __name__ == '__main__':
    main()
