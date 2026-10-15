#!/usr/bin/env python3
"""Let the TurtleBot find out where it is on the fixed map by itself, then (optionally) drive to the start mark.

    python3 tools/localize.py [--go-home] [--force-global] [--skip-check] [--set-start] [--min-fit 0.65] [--sim-time]

--set-start: the robot stands on the start mark; AMCL is reset there and the fit is checked (most reliable in
the near-symmetric arena). A pose in or at the edge of the taped river cannot be used as it is: Nav2 cannot plan
from inside the keepout. When the scan fits there clearly (not the mirror), the robot really is there (pushed
around an obstacle, for example): it turns away from the water and drives slowly straight out (at most 0.5 m,
stopping at anything the lidar sees ahead), then the fit is checked again. --no-escape: treat such a pose as wrong.

tools/run_abc.py runs it with --go-home before every mission. During a mission the localization_monitor node
(started by lab_mission) does the same checks and pauses the mission when the robot is lost.

Needs lab_nav (map server + AMCL + Nav2) running, as in every lab_mission launch. Steps:
  1. Check the pose AMCL has now (normally the start mark): if the laser scan already fits the map there,
     the robot is localised and nothing moves (skip with --force-global).
  2. Otherwise global localisation: AMCL spreads its particles over the whole map
     (/reinitialize_global_localization) and the robot turns slowly on the spot until AMCL agrees on one pose.
  3. The pose is accepted only if the scan fits the map there AND fits clearly better than at the mirrored
     pose (turned 180 deg about the arena centre). The arena is a near-symmetric rectangle, so AMCL can lock on
     the mirror; when the mirror fits clearly better, AMCL is reset to it (/initialpose). Up to three attempts.
  4. Costmaps are cleared (they filled with obstacles drawn at wrong poses during the search).
  5. --go-home: Nav2 drives the robot to the start mark (start_pose in config/reach_frame.yaml).

The robot only turns on the spot until it is localised; it drives only in step 5, through Nav2.
Exit code 0 when localised (and home, with --go-home), 1 otherwise. Ctrl-C stops the robot.
"""
import argparse
import os
import sys
import threading
import time

import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.parameter import Parameter
from rclpy.signals import SignalHandlerOptions

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get('PLUMETRACE_REPO', os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, 'plumetrace_twin'))
from plumetrace_twin.localizer import Localizer  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--go-home', action='store_true', help='drive to the start mark once localised')
    ap.add_argument('--force-global', action='store_true', help='always run the global search, even if the '
                    'current pose already fits')
    ap.add_argument('--min-fit', type=float, default=0.65, help='scan fit needed after the global search (0..1)')
    ap.add_argument('--keep-fit', type=float, default=0.75, help='scan fit at which the current pose is kept '
                    'without moving (0..1)')
    ap.add_argument('--margin', type=float, default=0.08, help='how much better the pose must fit than its '
                    'mirror (0..1)')
    ap.add_argument('--spin-speed', type=float, default=0.4, help='rad/s while searching')
    ap.add_argument('--turns', type=float, default=2.0, help='turns per attempt at most')
    ap.add_argument('--attempts', type=int, default=3)
    ap.add_argument('--max-std-xy', type=float, default=0.08, help='m')
    ap.add_argument('--max-std-yaw', type=float, default=0.15, help='rad')
    ap.add_argument('--home-timeout', type=float, default=180.0)
    ap.add_argument('--skip-check', action='store_true', help='do not localise, only drive home (with --go-home)')
    ap.add_argument('--set-start', action='store_true', help='the robot stands on the start mark: reset AMCL there, '
                    'then check the scan fits (no global search)')
    ap.add_argument('--sim-time', action='store_true', help='Gazebo: use_sim_time:=true')
    ap.add_argument('--no-escape', dest='escape', action='store_false', help='never drive out of the river: treat a '
                    'pose in or at it as wrong (global search instead)')
    args = ap.parse_args()

    # no rclpy SIGINT handler: Ctrl-C raises KeyboardInterrupt with the context still valid, so stop() reaches the robot
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    node = rclpy.create_node('plumetrace_localize')
    if args.sim_time:
        node.set_parameters([Parameter('use_sim_time', value=True)])
    loc = Localizer(node, args)
    ex = SingleThreadedExecutor()
    ex.add_node(node)
    spin = threading.Thread(target=ex.spin, daemon=True)
    spin.start()
    ok = False
    try:
        if args.set_start:
            if not loc.wait_inputs():
                ok = False
            else:
                loc.set_start()
                ok = loc.accept(args.keep_fit, 'on the start mark')
                if not ok:
                    print('localize: the scan does not fit the map at the start mark. Is the robot on the mark, facing '
                          '+x (away from the back wall)? Does the real arena match the map (boards moved)?', flush=True)
        else:
            ok = True if args.skip_check else loc.run()
        if ok and args.go_home:
            ok = loc.go_home()
    except KeyboardInterrupt:
        print('\nCtrl-C: stopping the robot', flush=True)
        nav = getattr(loc, 'nav', None)
        f = nav.cancel() if nav is not None else None  # else Nav2 keeps driving home on its own
        end = time.time() + 2.0
        while f is not None and not f.done() and time.time() < end:
            time.sleep(0.05)
    finally:
        loc.stop()
        ex.shutdown(timeout_sec=2.0)  # stop spinning before tearing down, else rclpy aborts at exit
        spin.join(timeout=3.0)
        node.destroy_node()
        rclpy.try_shutdown()
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
