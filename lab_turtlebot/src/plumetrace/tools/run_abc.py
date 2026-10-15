#!/usr/bin/env python3
"""Run the PlumeTrace missions for scenarios A, B and C back to back on the real TurtleBot3 (or Gazebo).

    python3 tools/run_abc.py [--scenarios ABC] [--seed 1] [--confirm] [--pause 10] [--sim-time] [-- launch args]

Per scenario:
  1. ros2 launch plumetrace_sim lab_mission.launch.py scenario:=<S> (Nav2 + twin + gateway; RViz runs separately)
  2. tools/wait_ready.py until Nav2 is active (one restart of the launch if it is not)
  2b. before the first run (and after a failed return home): tools/localize.py finds the robot on the map by
     itself (turning on the spot if needed), then the robot drives to the start mark (return_home)
  3. /mission/start, then follow /mission/events until the `done` event
  4. /twin/command return_home, wait until the robot is back on the start mark
  5. stop the launch (SIGINT to its process group), pause, next scenario

The dashboard (through tools/relay.py) stays open the whole time: it sees a new gateway `hello` and a new
`mission.scenario` per run, archives the previous run and starts a clean one, so all three runs fill it with
samples, plume, outfall probabilities, alerts and incidents.

The robot may start anywhere in the arena: it localises itself on the fixed map and drives to the start mark
before the first mission; between runs it drives home by itself. --no-localize skips this (the robot must then
start on the start mark). With --confirm the script waits for Enter before each run.
Arguments after `--` go to every lab_mission launch (e.g. `-- xy_goal_tolerance:=0.05 yaw_goal_tolerance:=0.15`).
Ctrl-C: aborts the running mission, stops the launch and exits (the robot stops).
Logs: $PLUMETRACE_RUNS/<time>-abc/ (launch_<S>.log per run, summary.json); each mission also writes its own
run folder (CSV + rosbag) as usual.
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
from rclpy.parameter import Parameter
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


class Launch:
    def __init__(self, scenario, seed, extra, log_path, sim_time):
        cmd = ['ros2', 'launch', 'plumetrace_sim', 'lab_mission.launch.py', f'scenario:={scenario}',
               f'seed:={seed}', 'rviz:=false'] + (['use_sim_time:=true'] if sim_time else []) + extra
        print('  $', ' '.join(cmd), flush=True)
        self.log = open(log_path, 'w')
        self.proc = subprocess.Popen(cmd, stdout=self.log, stderr=subprocess.STDOUT, start_new_session=True)

    def stop(self):
        if self.proc.poll() is None:
            for sig, wait in ((signal.SIGINT, 20), (signal.SIGTERM, 8), (signal.SIGKILL, 3)):
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


def wait_ready(timeout):
    return subprocess.call([sys.executable, os.path.join(HERE, 'wait_ready.py'), str(timeout)]) == 0


def localize(args):
    cmd = [sys.executable, os.path.join(HERE, 'localize.py')] + (['--sim-time'] if args.sim_time else [])
    return subprocess.call(cmd) == 0


def run_one(watcher, s, args, out_dir, need_localize=False):
    truth = load_scenario(s)['active_outfall']
    res = dict(scenario=s, truth=truth, started=time.strftime('%H:%M:%S'))
    for attempt in (1, 2):
        watcher.reset()
        launch = Launch(s, args.seed, args.launch_args, os.path.join(out_dir, f'launch_{s}.log'), args.sim_time)
        if wait_ready(args.ready_timeout):
            break
        print(f'  Nav2 not ready (attempt {attempt}); restarting the launch', flush=True)
        launch.stop()
        time.sleep(5)
    else:
        res.update(result='NOT_READY')
        return res, None
    try:
        time.sleep(3)  # let the twin and the gateway connect
        if need_localize:
            print('  localising the robot on the map ...', flush=True)
            if localize(args):
                watcher.command('return_home')
                home = watcher.wait_event('return_home', args.home_timeout)
                if not (home and home.get('status') == GOAL_SUCCEEDED):
                    print('  !! could not drive to the start mark; the mission starts from where the robot is',
                          flush=True)
                watcher.reset()
            elif sys.stdin.isatty():
                input('  Localisation failed. Put the robot on the start mark facing +x (or set "2D Pose Estimate" '
                      'in RViz), then press Enter. ')
            else:
                print('  !! localisation failed; continuing with the start-mark pose', flush=True)
        if not watcher.start_mission():
            res.update(result='NO_START')
            return res, launch
        print(f'  mission {s} started', flush=True)
        done = watcher.wait_event('done', args.timeout)
        if done is None:
            watcher.command('abort')
            res.update(result='TIMEOUT')
            watcher.wait_event('done', 20)
        else:
            ok = done.get('final') == 'DONE' and done.get('map_label') == truth
            res.update(result='PASS' if ok else 'FAIL', final=done.get('final'), map_label=done.get('map_label'),
                       probabilities=done.get('probabilities'), samples=done.get('samples'))
        print(f'  {s}: {res["result"]} (named {res.get("map_label")}, truth {truth}); returning home', flush=True)
        watcher.command('return_home')
        home = watcher.wait_event('return_home', args.home_timeout)
        res['home'] = 'OK' if home and home.get('status') == GOAL_SUCCEEDED else 'FAILED'
        if res['home'] != 'OK':
            print('  !! robot did not confirm it is home: put it on the start mark by hand before the next run',
                  flush=True)
    finally:
        res['ended'] = time.strftime('%H:%M:%S')
    return res, launch


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
    ap.add_argument('--pause', type=float, default=10.0, help='seconds between runs')
    ap.add_argument('--confirm', action='store_true', help='wait for Enter before each run')
    ap.add_argument('--sim-time', action='store_true', help='Gazebo: use_sim_time:=true')
    ap.add_argument('--no-localize', action='store_true', help='skip self-localisation; robot starts on the mark')
    args = ap.parse_args(argv)
    args.launch_args = extra

    out_dir = os.path.join(os.environ.get('PLUMETRACE_RUNS', os.path.expanduser('~/plumetrace_runs')),
                           time.strftime('%Y%m%d-%H%M%S') + '-abc')
    os.makedirs(out_dir, exist_ok=True)
    rclpy.init()
    node = rclpy.create_node('plumetrace_run_abc')
    if args.sim_time:
        node.set_parameters([Parameter('use_sim_time', value=True)])
    watcher = Watcher(node)
    threading.Thread(target=rclpy.spin, args=(node,), daemon=True).start()

    results, launch = [], None
    try:
        for i, s in enumerate(args.scenarios.upper()):
            print(f'\n=== run {i + 1}/{len(args.scenarios)}: scenario {s} ===', flush=True)
            if args.confirm:
                input('Robot on the start mark, facing away from the back wall? Press Enter to start. '
                      if args.no_localize or i > 0 else 'Robot anywhere in the arena (it finds itself)? Press Enter. ')
            need = not args.no_localize and (i == 0 or results[-1].get('home') != 'OK')
            res, launch = run_one(watcher, s, args, out_dir, need)
            results.append(res)
            if launch is not None:
                launch.stop()
                launch = None
            with open(os.path.join(out_dir, 'summary.json'), 'w') as f:
                json.dump(results, f, indent=1)
            if i + 1 < len(args.scenarios):
                time.sleep(args.pause)
    except KeyboardInterrupt:
        print('\nCtrl-C: aborting the mission and stopping the launch', flush=True)
        watcher.command('abort')
    finally:
        if launch is not None:
            launch.stop()
        node.destroy_node()
        rclpy.try_shutdown()

    print('\nscenario  result   named  truth  home    samples')
    for r in results:
        print(f"{r['scenario']:<9} {r.get('result', '?'):<8} {str(r.get('map_label')):<6} {r['truth']:<6} "
              f"{r.get('home', '-'):<7} {r.get('samples', '-')}")
    print(f'logs: {out_dir}')
    sys.exit(0 if results and all(r.get('result') == 'PASS' for r in results) else 1)


if __name__ == '__main__':
    main()
