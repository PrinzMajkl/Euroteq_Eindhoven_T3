"""mission_controller: planner -> Nav2 goal -> dwell -> sample -> estimator, until localised.

States IDLE | RUNNING | HOLD | DONE | ABORTED on /mission/state (MissionState, 1 Hz and on change).
HOLD: while the link stream of /twin/sync is LOST (no heartbeat for >= 3 s) the current Nav2 goal is
cancelled and the robot holds; the goal is re-sent once every stream is SYNCED again. The same happens while
localization_monitor reports the robot lost on the map (/localization/status LOST or RELOCALIZING, std_msgs/String
JSON); OK resumes, FAILED aborts the mission.
Started at launch (autostart) or by /mission/start (std_msgs/Empty).
Commands on /twin/command (std_msgs/String JSON {"type": ...}): abort, return_home.
Events (JSON) on /mission/events: goal_sent, goal_result, sample, hold, resume, done, abort.
"""
import json
import threading
import time

import rclpy
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import PoseStamped
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from std_msgs.msg import Empty, String, UInt32

from plumetrace_msgs.msg import MissionState, PlumeSample, Posterior, SyncStatus

from ..estimator import LOCALISED_P
from ..reach import ReachFrame
from ..simtools import Nav2Client, quat_to_yaw

LOST = 2


class MissionController(Node):
    def __init__(self):
        super().__init__('mission_controller')
        self.declare_parameter('scenario', 'A')
        self.declare_parameter('mode', 'SIM')
        self.declare_parameter('autostart', True)
        self.declare_parameter('sample_timeout_s', 20.0)
        self.declare_parameter('mission_timeout_s', 900.0)
        self.scenario = self.get_parameter('scenario').value
        self.mode = self.get_parameter('mode').value
        self.frame = ReachFrame.load()
        self.state = 'IDLE'
        self.samples = 0
        self.goal = None
        self.post = None
        self.sync_lost = False
        self.sync_ok = True
        self.loc_lost = False
        self.abort_req = False
        self.home_req = False
        self.cv = threading.Condition()
        cb = ReentrantCallbackGroup()
        self.nav = Nav2Client(self)
        self.state_pub = self.create_publisher(MissionState, '/mission/state', 10)
        self.event_pub = self.create_publisher(String, '/mission/events', 50)
        self.trig = self.create_publisher(UInt32, '/sensor/trigger', 10)
        self.req = self.create_publisher(Empty, '/twin/plan_request', 10)
        self.create_subscription(PoseStamped, '/twin/next_goal', self.on_goal, 10, callback_group=cb)
        self.create_subscription(Posterior, '/twin/posterior', self.on_post, 10, callback_group=cb)
        self.create_subscription(PlumeSample, '/twin/samples', self.on_sample, 50, callback_group=cb)
        self.create_subscription(SyncStatus, '/twin/sync', self.on_sync, 10, callback_group=cb)
        self.create_subscription(String, '/twin/command', self.on_cmd, 10, callback_group=cb)
        self.create_subscription(String, '/localization/status', self.on_loc, 10, callback_group=cb)
        self.create_timer(1.0, self.publish_state, callback_group=cb)
        self.started = False
        self.create_subscription(Empty, '/mission/start', lambda _: self.start(), 10, callback_group=cb)
        if self.get_parameter('autostart').value:
            self.start()

    def start(self):
        if not self.started:
            self.started = True
            threading.Thread(target=self.run, daemon=True).start()

    # --- inputs -------------------------------------------------------------
    def on_goal(self, msg):
        with self.cv:
            self.goal = msg
            self.cv.notify_all()

    def on_post(self, msg):
        self.post = msg

    def on_sample(self, msg):
        with self.cv:
            self.samples += 1
            self.cv.notify_all()
        self.event('sample', seq=msg.seq, nh3=round(msg.nh3_n_mg_l, 4))

    def on_sync(self, msg):
        st = dict(zip(msg.streams, msg.states))
        with self.cv:
            self.sync_lost = st.get('link', 0) == LOST
            self.sync_ok = all(s == 0 for s in msg.states)
            self.cv.notify_all()

    def on_loc(self, msg):
        try:
            st = json.loads(msg.data).get('state')
        except ValueError:
            return
        running = self.state in ('RUNNING', 'HOLD')
        if st in ('LOST', 'RELOCALIZING'):
            if running and not self.loc_lost:
                self.event('localization_lost')
                self.nav.cancel()
            with self.cv:
                self.loc_lost = True
                self.cv.notify_all()
        elif st == 'OK' and self.loc_lost:
            if running:
                self.event('relocalized')
            with self.cv:
                self.loc_lost = False
                self.cv.notify_all()
        elif st == 'FAILED':
            with self.cv:
                self.loc_lost = False
                self.cv.notify_all()
            if running:
                self.event('abort', reason='localization failed')
                self.abort_req = True
                self.nav.cancel()

    def on_cmd(self, msg):
        try:
            cmd = json.loads(msg.data)
        except ValueError:
            return
        t = cmd.get('type')
        self.event('command', command=t)
        running = self.state in ('RUNNING', 'HOLD')
        if t == 'abort':
            self.abort_req = True
            self.nav.cancel()
            if not running:
                self.set_state('ABORTED')
        elif t == 'return_home':
            if running:
                self.home_req = True
                self.nav.cancel()
            else:
                threading.Thread(target=self.go_home, daemon=True).start()

    def go_home(self):
        x, y, yaw = self.frame.arena['start_pose']
        self.event('return_home_start')
        st, _ = self.nav.go(x, y, yaw, timeout=180)
        self.event('return_home', status=int(st))

    # --- outputs ------------------------------------------------------------
    def event(self, kind, **kw):
        kw.update(type=kind, t=round(self.get_clock().now().nanoseconds * 1e-9, 3), state=self.state)
        self.event_pub.publish(String(data=json.dumps(kw)))

    def set_state(self, s):
        if s != self.state:
            self.state = s
            self.event('state', new=s)
            self.publish_state()

    def publish_state(self):
        m = MissionState()
        m.header.stamp = self.get_clock().now().to_msg()
        m.mode = self.mode
        m.state = self.state
        m.samples_taken = self.samples
        m.scenario = self.scenario
        self.state_pub.publish(m)

    # --- mission ------------------------------------------------------------
    def wait_for(self, pred, timeout):
        t0 = time.time()
        with self.cv:
            while not pred():
                if self.abort_req or time.time() - t0 > timeout:
                    return False
                self.cv.wait(0.1)
        return True

    def localised(self):
        return self.post is not None and len(self.post.probabilities) and max(self.post.probabilities) >= LOCALISED_P

    def drive(self, x, y, yaw):
        """Navigate with HOLD on link loss. Returns a GoalStatus code."""
        while True:
            if self.abort_req or self.home_req:
                return GoalStatus.STATUS_CANCELED
            if self.sync_lost or self.loc_lost:
                self.hold()
                continue
            result = {}
            th = threading.Thread(target=lambda: result.update(r=self.nav.go(x, y, yaw, timeout=180)))
            th.start()
            held = False
            last_cancel = 0.0
            while th.is_alive():
                if self.sync_lost or self.loc_lost:
                    held = True
                    if time.time() - last_cancel > 0.5:  # repeat: a cancel before the goal handle exists is lost
                        last_cancel = time.time()
                        self.nav.cancel()
                time.sleep(0.05)
            if self.sync_lost or self.loc_lost:  # the goal may have been cancelled (on_loc) before the loop saw it
                held = True
            if held:
                self.hold()
                continue
            return result['r'][0]

    def hold(self):
        self.set_state('HOLD')
        self.event('hold', reason='localization' if self.loc_lost else 'link')
        self.wait_for(lambda: self.sync_ok and not self.loc_lost, 1e9)
        if not self.abort_req:
            self.set_state('RUNNING')
            self.event('resume')

    def run(self):
        while not self.nav.wait(5.0):
            pass
        time.sleep(2.0)
        t_start = time.time()
        self.set_state('RUNNING')
        self.goal = None
        self.req.publish(Empty())
        while True:
            if self.abort_req:
                return self.finish('ABORTED')
            if self.home_req:
                x, y, yaw = self.frame.arena['start_pose']
                self.home_req = False
                self.event('return_home_start')
                st = self.drive(x, y, yaw)
                self.event('return_home', status=int(st))
                return self.finish('ABORTED' if self.abort_req else 'DONE')
            if time.time() - t_start > self.get_parameter('mission_timeout_s').value:
                return self.finish('ABORTED')
            if not self.wait_for(lambda: self.goal is not None, 30.0):
                if self.abort_req:
                    continue
                self.req.publish(Empty())
                continue
            g = self.goal
            self.goal = None
            if g.header.frame_id == 'none':
                return self.finish('DONE')
            x, y, yaw = g.pose.position.x, g.pose.position.y, quat_to_yaw(g.pose.orientation)
            self.event('goal_sent', x=round(x, 3), y=round(y, 3), yaw=round(yaw, 3))
            st = self.drive(x, y, yaw)
            self.event('goal_result', status=int(st))
            if self.abort_req or self.home_req:
                continue
            n0 = self.samples
            self.trig.publish(UInt32(data=n0 + 1))
            self.event('dwell')
            if not self.wait_for(lambda: self.samples > n0, self.get_parameter('sample_timeout_s').value):
                self.event('sample_timeout')
                self.req.publish(Empty())
                continue
            if self.loc_lost:  # lost while sampling: wait until the position is fixed before the next stop
                self.hold()
                if self.abort_req:  # re-localisation failed: do not finish DONE on this sample
                    continue
            if self.localised():
                self.wait_for(lambda: self.goal is not None, 3.0)
                return self.finish('DONE')

    def finish(self, state):
        p = self.post
        self.event('done', final=state, samples=self.samples,
                   map_label=p.map_label if p else None,
                   probabilities=[round(v, 4) for v in p.probabilities] if p else None)
        self.set_state(state)


def main():
    rclpy.init()
    node = MissionController()
    ex = MultiThreadedExecutor(num_threads=4)
    ex.add_node(node)
    try:
        ex.spin()
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass


if __name__ == '__main__':
    main()
