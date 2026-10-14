#!/usr/bin/env python3
"""Follow /mission/events until the mission's `done` event and check it against the scenario file.

    python3 tools/wait_done.py <scenario> [timeout_s] [--sim-time]

Prints every event as one JSON line. Exit 0 when the done event has final DONE and its map_label is the
scenario's active_outfall; 1 when it names another outfall or ends ABORTED; 2 on timeout (wall-clock).
"""
import json
import os
import sys
import time

import rclpy
from rclpy.parameter import Parameter
from std_msgs.msg import String

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'plumetrace_twin'))
from plumetrace_twin.scenario import load_scenario  # noqa: E402


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    truth = load_scenario(args[0])['active_outfall']
    timeout = float(args[1]) if len(args) > 1 else 900.0
    rclpy.init()
    node = rclpy.create_node('plumetrace_wait_done')
    if '--sim-time' in sys.argv:
        node.set_parameters([Parameter('use_sim_time', value=True)])
    done = []

    def on_event(msg):
        print(msg.data, flush=True)
        try:
            ev = json.loads(msg.data)
        except ValueError:
            return
        if ev.get('type') == 'done':
            done.append(ev)

    node.create_subscription(String, '/mission/events', on_event, 50)
    t0 = time.time()
    while not done and time.time() - t0 < timeout:
        rclpy.spin_once(node, timeout_sec=0.5)
    if not done:
        print(f'RESULT timeout after {timeout:.0f} s: no done event', flush=True)
        return 2
    ev = done[0]
    ok = ev.get('final') == 'DONE' and ev.get('map_label') == truth
    print(f"RESULT {'PASS' if ok else 'FAIL'}: scenario {args[0]} active outfall {truth}, done event final "
          f"{ev.get('final')} map_label {ev.get('map_label')} probabilities {ev.get('probabilities')} "
          f"samples {ev.get('samples')} after {time.time() - t0:.0f} s", flush=True)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
