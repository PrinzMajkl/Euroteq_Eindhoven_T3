#!/usr/bin/env python3
"""Exit 0 once every listed lifecycle node reports ACTIVE (default: the lab_nav set), else 1 after a timeout.

    python3 tools/wait_ready.py [timeout_s] [extra node names...]
A lifecycle manager sometimes stops after "Starting managed nodes bringup..." (seen once in five starts in
simulation, 2026-10-14). When nodes are still inactive after half the timeout, the three managers of
lab_nav are asked once to start their nodes again.
"""
import sys
import time

import rclpy
from lifecycle_msgs.msg import State
from lifecycle_msgs.srv import GetState
from nav2_msgs.srv import ManageLifecycleNodes

NODES = ['map_server', 'amcl', 'filter_mask_server', 'soft_mask_server', 'costmap_filter_info_server',
         'controller_server', 'smoother_server', 'planner_server', 'behavior_server', 'bt_navigator']
MANAGERS = ['lifecycle_manager_localization', 'lifecycle_manager_filters', 'lifecycle_manager_navigation']


def main():
    timeout = float(sys.argv[1]) if len(sys.argv) > 1 else 60.0
    extra = sys.argv[2:]
    rclpy.init()
    node = rclpy.create_node('plumetrace_wait_ready')
    clients = {n: node.create_client(GetState, f'/{n}/get_state') for n in NODES + extra}
    t0 = time.time()
    pending = set(clients)
    kicked = False
    while pending and time.time() - t0 < timeout:
        if not kicked and time.time() - t0 > timeout / 2:
            kicked = True
            print(f'still not active: {sorted(pending)}; asking the lifecycle managers to start again', flush=True)
            for m in MANAGERS:
                c = node.create_client(ManageLifecycleNodes, f'/{m}/manage_nodes')
                if c.wait_for_service(timeout_sec=1.0):
                    fut = c.call_async(ManageLifecycleNodes.Request(command=ManageLifecycleNodes.Request.STARTUP))
                    rclpy.spin_until_future_complete(node, fut, timeout_sec=20.0)
        for n in list(pending):
            c = clients[n]
            if not c.service_is_ready():
                continue
            fut = c.call_async(GetState.Request())
            rclpy.spin_until_future_complete(node, fut, timeout_sec=2.0)
            if fut.done() and fut.result() and fut.result().current_state.id == State.PRIMARY_STATE_ACTIVE:
                pending.discard(n)
        rclpy.spin_once(node, timeout_sec=0.5)
    print('ready' if not pending else f'not active: {sorted(pending)}', flush=True)
    return 0 if not pending else 1


if __name__ == '__main__':
    sys.exit(main())
