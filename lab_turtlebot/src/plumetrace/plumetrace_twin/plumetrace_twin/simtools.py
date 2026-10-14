"""Helpers shared by nodes and tools: run folders, pose helpers, Nav2 client."""
import math
import os
import threading
import time

import rclpy
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import ComputePathToPose, NavigateToPose
from rclpy.action import ActionClient


def make_run_dir(tag=None):
    root = os.environ.get('PLUMETRACE_RUNS', os.path.expanduser('~/plumetrace_runs'))
    name = time.strftime('%Y%m%d-%H%M%S') + (f'-{tag}' if tag else '')
    path = os.path.join(root, name)
    os.makedirs(path, exist_ok=True)
    return path


def yaw_to_quat(yaw):
    return 0.0, 0.0, math.sin(yaw / 2), math.cos(yaw / 2)


def quat_to_yaw(q):
    return math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))


def pose_stamped(node, x, y, yaw, frame='map'):
    ps = PoseStamped()
    ps.header.frame_id = frame
    ps.header.stamp = node.get_clock().now().to_msg()
    ps.pose.position.x, ps.pose.position.y = float(x), float(y)
    q = yaw_to_quat(yaw)
    ps.pose.orientation.x, ps.pose.orientation.y, ps.pose.orientation.z, ps.pose.orientation.w = q
    return ps


class Nav2Client:
    def __init__(self, node):
        self.node = node
        self.nav = ActionClient(node, NavigateToPose, 'navigate_to_pose')
        self.plan = ActionClient(node, ComputePathToPose, 'compute_path_to_pose')
        self._handle = None

    def wait(self, timeout=60.0):
        return self.nav.wait_for_server(timeout_sec=timeout)

    def send(self, x, y, yaw):
        """Send a goal asynchronously; returns a future for the goal handle."""
        goal = NavigateToPose.Goal()
        goal.pose = pose_stamped(self.node, x, y, yaw)
        fut = self.nav.send_goal_async(goal)

        def _store(f):
            self._handle = f.result()
        fut.add_done_callback(_store)
        return fut

    def go(self, x, y, yaw, timeout=120.0):
        """Blocking goal (call from a thread other than the executor's). Returns (status, seconds)."""
        t0 = time.time()
        handle = None
        for _ in range(3):  # the first goal after start-up can lose its response while the BT loads
            fut = self.send(x, y, yaw)
            t1 = time.time()
            while not fut.done() and time.time() - t1 < 10:
                time.sleep(0.02)
            if fut.done():
                handle = fut.result()
                break
        if handle is None:
            return GoalStatus.STATUS_UNKNOWN, time.time() - t0
        if not handle.accepted:
            return GoalStatus.STATUS_ABORTED, time.time() - t0
        rfut = handle.get_result_async()
        while not rfut.done():
            if time.time() - t0 > timeout:
                handle.cancel_goal_async()
                return GoalStatus.STATUS_CANCELED, time.time() - t0
            time.sleep(0.02)
        return rfut.result().status, time.time() - t0

    def cancel(self):
        if self._handle is not None:
            return self._handle.cancel_goal_async()

    def path_length(self, x, y, yaw, timeout=5.0):
        """Plan with the global planner from the current pose; returns the path length or None."""
        if not self.plan.wait_for_server(timeout_sec=1.0):
            return None
        goal = ComputePathToPose.Goal()
        goal.goal = pose_stamped(self.node, x, y, yaw)
        goal.use_start = False
        fut = self.plan.send_goal_async(goal)
        t0 = time.time()
        while not fut.done():
            if time.time() - t0 > timeout:
                return None
            time.sleep(0.01)
        h = fut.result()
        if not h.accepted:
            return None
        r = h.get_result_async()
        while not r.done():
            if time.time() - t0 > timeout:
                return None
            time.sleep(0.01)
        res = r.result()
        if res.status != GoalStatus.STATUS_SUCCEEDED or not res.result.path.poses:
            return None
        pts = [(p.pose.position.x, p.pose.position.y) for p in res.result.path.poses]
        return sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))


def spin_in_thread(node):
    ex = rclpy.executors.MultiThreadedExecutor(num_threads=4)
    ex.add_node(node)
    th = threading.Thread(target=ex.spin, daemon=True)
    th.start()
    return ex, th
