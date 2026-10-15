#!/usr/bin/env python3
"""Generate a synthetic demo run (JSONL) for the dashboard's Replay mode.

It imitates the message flow of safe_navigation_pollution_v3.py and
digital_twin_pollution_v4.py: the robot drives through a plume, keeps going
until clean water, the twin picks the highest reading as hotspot, Nav2 drives
back to it, arrival is verified and the mission completes.

Every line is one message in the gateway envelope format:
    {"t": <seconds since start>, "topic": "<ros topic>", "data": <payload>}

The plume profile here is longer than MOCK_PLUME_PROFILE so the reroute is
visible on the map. Values are SYNTHETIC, not measurements.

Usage: python3 make_demo_run.py ../data/demo_run.jsonl
"""
import json
import math
import sys

PROFILE = [(0.0, 0.05), (1.0, 0.3), (2.0, 2.0), (3.5, 5.0), (4.5, 9.0),
           (5.5, 3.0), (6.5, 0.05), (9.0, 0.0)]
START = (0.0, 3.5)            # arena metres, odom frame
SPEED = 0.10                  # m/s, like forward_speed_mps
SAMPLE_STEP = 0.08            # m, like sensor_distance_step_m
ALERT, EXIT, LOW_DO = 0.6, 0.1, 7.0
T0 = 1791966000.0             # epoch seconds (Oct 2026)


def profile(along):
    if along <= PROFILE[0][0]:
        return PROFILE[0][1]
    for (x0, y0), (x1, y1) in zip(PROFILE, PROFILE[1:]):
        if along <= x1:
            return y0 + (along - x0) / (x1 - x0) * (y1 - y0)
    return PROFILE[-1][1]


out = []


def emit(t, topic, data):
    out.append({"t": round(t, 2), "topic": topic, "data": data})


class Twin:
    def __init__(self):
        self.mode, self.decision = "BASELINE_ROUTE", "CONTINUE"
        self.samples, self.peak, self.gradient = [], None, None
        self.plume_seen, self.target, self.event = False, None, None
        self.env, self.robot = {}, {}
        self.last_robot_t = self.last_sample_t = None

    def state(self, t):
        ra = None if self.last_robot_t is None else t - self.last_robot_t
        sa = None if self.last_sample_t is None else t - self.last_sample_t
        p = self.peak
        emit(t, "/digital_twin_state", {
            "timestamp": T0 + t,
            "robot": {k: self.robot.get(k) for k in (
                "x", "y", "yaw", "velocity_mps", "status", "battery_percent",
                "battery_voltage_v", "battery_source", "battery_is_simulated",
                "battery_estimated_remaining_min")},
            "environment": {**self.env,
                            "nearest_obstacle_m": self.robot.get("nearest_obstacle_m")},
            "pollution": {
                "alarm": self.mode != "BASELINE_ROUTE" and self.plume_seen,
                "gradient_mg_l_per_m": self.gradient,
                "estimated_source_x": None, "estimated_source_y": None,
                "suspected_hotspot_x": p["x"] if p else None,
                "suspected_hotspot_y": p["y"] if p else None,
                "sample_count": len(self.samples),
                "sensor_origin": "SYNTHETIC_POSITION_BASED",
                "measurement_accuracy": "NOT_VALIDATED"},
            "synchronization": {
                "robot_telemetry_fresh": ra is not None and ra <= 3.0,
                "sensor_data_fresh": sa is not None and sa <= 6.0,
                "robot_telemetry_age_sec": None if ra is None else round(ra, 2),
                "sensor_data_age_sec": None if sa is None else round(sa, 2),
                "last_sample_id": self.samples[-1]["sample_id"] if self.samples else None,
                "battery_available": True},
            "mission": {"current_target": self.target, "mode": self.mode,
                        "decision": self.decision, "last_nav2_event": self.event}})


twin = Twin()
x, y, yaw = START[0], START[1], 0.0
t, dt = 0.0, 0.5
dist = last_sample_dist = 0.0
sid = 0
status = "MOVING"
phase = "patrol"
next_state = 0.0
nav_start = None
arrived_t = None


def battery(t):
    b = max(0.0, 95.0 - (t / 60.0) * (95.0 / 90.0))
    return round(b, 2), round(b / (95.0 / 90.0), 1)


while True:
    # ---- motion
    if phase == "patrol":
        x += SPEED * dt
        dist += SPEED * dt
        vel = SPEED
    elif phase == "nav":
        tx, ty = twin.target["x"], twin.target["y"]
        d = math.hypot(tx - x, ty - y)
        yaw = math.atan2(ty - y, tx - x)
        step = min(SPEED, d / dt) * dt
        x += math.cos(yaw) * step
        y += math.sin(yaw) * step
        dist += step
        vel = step / dt
        if d < 0.05 and arrived_t is None:
            arrived_t = t
    else:
        vel = 0.0

    # ---- robot status (2 Hz)
    b, rem = battery(t)
    robot = {"timestamp": T0 + t, "x": round(x, 4), "y": round(y, 4),
             "yaw": round(yaw, 4), "velocity_mps": round(vel, 3),
             "distance_m": round(dist, 3), "nearest_obstacle_m": round(2.4 - 0.1 * x, 3),
             "status": status, "finished": phase == "done",
             "battery_percent": b, "battery_voltage_v": None,
             "battery_source": "SIMULATED_RUNTIME_MODEL",
             "battery_is_simulated": True, "battery_estimated_remaining_min": rem}
    emit(t, "/robot_status", robot)
    twin.robot, twin.last_robot_t = robot, t

    # ---- sensor sample while patrolling
    if phase == "patrol" and dist - last_sample_dist >= SAMPLE_STEP - 1e-9:
        last_sample_dist = dist
        sid += 1
        a = round(max(0.0, profile(x - START[0])), 4)
        do = round(max(0.0, 8.5 - 0.45 * a), 3)
        s = {"sample_id": sid, "timestamp": T0 + t, "x": round(x, 4), "y": round(y, 4),
             "distance_m": round(dist, 4), "nh3_n_mg_l": a, "do_mg_l": do,
             "sensor_type": "SYNTHETIC_POSITION_BASED"}
        emit(t, "/pollution", s)
        if twin.samples:
            p = twin.samples[-1]
            delta = math.hypot(s["x"] - p["x"], s["y"] - p["y"])
            if delta > 0.005:
                twin.gradient = (a - p["nh3_n_mg_l"]) / delta
        twin.samples.append(s)
        twin.last_sample_t = t
        twin.env = {"nh3_n_mg_l": a, "do_mg_l": do}
        if twin.peak is None or a > twin.peak["nh3_n_mg_l"]:
            twin.peak = dict(s)
        if a >= ALERT:
            twin.plume_seen = True
        if twin.mode == "BASELINE_ROUTE" and twin.plume_seen and a < EXIT:
            twin.mode, twin.decision = "PAUSED_FOR_ANALYSIS", "PAUSE"
            emit(t, "/navigation_decision", "PAUSE")
            status, phase = "PAUSED_FOR_TWIN", "pause"
            twin.state(t)
            twin.target = {"x": twin.peak["x"], "y": twin.peak["y"], "frame_id": "odom",
                           "tolerance_m": 0.25, "basis": "PEAK_MEASUREMENT_PROXY"}
            twin.mode, twin.decision = "ROUTING_TO_HOTSPOT", "NAVIGATE"
            emit(t, "/twin_waypoint", twin.target)
            status = "NAV2_PREPARING"
            nav_start = t + 3.0
        twin.state(t)

    if phase == "pause" and t >= nav_start:
        phase, status = "nav", "NAVIGATING_TO_HOTSPOT"
        twin.event = {"status": "ACCEPTED", "timestamp": T0 + t}
        emit(t, "/twin_mission_event", twin.event)
        twin.state(t)

    if phase == "nav" and arrived_t is not None:
        phase, status = "done", "GOAL_REACHED"
        twin.event = {"status": "ARRIVED", "timestamp": T0 + t}
        emit(t, "/twin_mission_event", twin.event)
        twin.mode, twin.decision = "COMPLETED", "STOP"
        emit(t, "/navigation_decision", "STOP")
        twin.state(t)
        end_t = t + 6.0

    if t >= next_state:
        twin.state(t)
        next_state = t + 5.0

    if phase == "done" and t >= end_t:
        break
    t += dt

with open(sys.argv[1] if len(sys.argv) > 1 else "demo_run.jsonl", "w") as f:
    for m in out:
        f.write(json.dumps(m, allow_nan=False) + "\n")
print(f"{len(out)} messages, {t:.0f} s, {sid} samples, peak "
      f"{twin.peak['nh3_n_mg_l']} mg/L at ({twin.peak['x']}, {twin.peak['y']})")
